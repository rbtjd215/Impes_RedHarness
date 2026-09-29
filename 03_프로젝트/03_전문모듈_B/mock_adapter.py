"""Offline XSS candidate analysis for the RedHarness B contract.

This module reads only an in-memory, synthetic v1 envelope. It does not fetch a
page, open a browser, execute JavaScript, or decide the final result.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any


_FIELDS = {
    "contract_version", "run_id", "target_id", "selected_module", "producer",
    "observation", "actions", "status", "evidence", "error", "next_action",
}
_MARKER = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_MAX_MOCK_SIZE = 100_000
_SOURCES = {
    "location.hash": re.compile(r"\blocation\s*\.\s*hash\b"),
    "location.search": re.compile(r"\blocation\s*\.\s*search\b"),
    "document.URL": re.compile(r"\bdocument\s*\.\s*URL\b"),
}
_SINKS = {
    "innerHTML": re.compile(r"\.\s*innerHTML\s*=\s*(.+)\Z"),
    "outerHTML": re.compile(r"\.\s*outerHTML\s*=\s*(.+)\Z"),
    "document.write": re.compile(r"\bdocument\s*\.\s*write\s*\(\s*(.+)\Z"),
}
_ASSIGNMENT = re.compile(
    r"^(?:(?:const|let|var)\s+)?([A-Za-z_$][\w$]*)\s*=\s*(.+)\Z"
)


class _MarkerContexts(HTMLParser):
    """Record where an inert marker appears, without retaining the HTML."""

    def __init__(self, marker: str) -> None:
        super().__init__(convert_charrefs=False)
        self.marker = marker
        self.contexts: set[str] = set()
        self.raw_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if any(value is not None and self.marker in value for _, value in attrs):
            self.contexts.add("attribute")
        if tag in {"script", "style", "textarea", "title"}:
            self.raw_tag = tag

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if any(value is not None and self.marker in value for _, value in attrs):
            self.contexts.add("attribute")

    def handle_endtag(self, tag: str) -> None:
        if tag == self.raw_tag:
            self.raw_tag = None

    def handle_data(self, data: str) -> None:
        if self.marker in data:
            self.contexts.add(self.raw_tag or "text")

    def handle_comment(self, data: str) -> None:
        if self.marker in data:
            self.contexts.add("comment")


def _reflection_contexts(response_html: str, marker: str) -> list[str]:
    if marker not in response_html:
        return []
    parser = _MarkerContexts(marker)
    parser.feed(response_html)
    parser.close()
    return sorted(parser.contexts or {"unclassified"})


def _source_in(expression: str) -> str | None:
    return next((name for name, pattern in _SOURCES.items() if pattern.search(expression)), None)


def _tainted_reference(expression: str, variables: dict[str, str]) -> str | None:
    direct = _source_in(expression)
    if direct is not None:
        return direct
    for variable, source in variables.items():
        if re.search(r"(?<![\w$])" + re.escape(variable) + r"(?![\w$])", expression):
            return source
    return None


def _dom_candidates(script_source: str) -> list[dict[str, str]]:
    """Find direct or ordered one-variable source-to-sink candidates.

    This is deliberately a small textual approximation, not JavaScript parsing
    or browser execution. It makes no safety or exploitability claim.
    """
    variables: dict[str, str] = {}
    candidates: list[dict[str, str]] = []
    for statement in (part.strip() for part in re.split(r"[;\n]", script_source)):
        if not statement:
            continue
        for sink_name, pattern in _SINKS.items():
            sink_match = pattern.search(statement)
            if sink_match is None:
                continue
            source = _tainted_reference(sink_match.group(1), variables)
            if source is not None:
                candidate = {"kind": "dom_source_sink_candidate", "source": source, "sink": sink_name}
                if candidate not in candidates:
                    candidates.append(candidate)
        assignment = _ASSIGNMENT.match(statement)
        if assignment is not None:
            variable, expression = assignment.groups()
            source = _tainted_reference(expression, variables)
            if source is None:
                variables.pop(variable, None)
            else:
                variables[variable] = source
    return candidates


def _validate_input(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ValueError("input must be a v1 envelope object")
    missing = sorted(_FIELDS - envelope.keys())
    if missing:
        raise ValueError("missing v1 fields: " + ", ".join(missing))
    if envelope["contract_version"] != "1.0":
        raise ValueError("contract_version must be 1.0")
    for key in ("run_id", "target_id"):
        if not isinstance(envelope[key], str) or not envelope[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if envelope["selected_module"] != "B" or envelope["producer"] != "DISPATCHER":
        raise ValueError("B mock adapter requires a Dispatcher envelope selected for B")
    if not isinstance(envelope["status"], str) or envelope["status"] not in {"NOT_RUN", "UNKNOWN"}:
        raise ValueError("Dispatcher input cannot contain a final status")
    if not isinstance(envelope["observation"], dict):
        raise ValueError("observation must be an object")
    if not isinstance(envelope["actions"], list) or not isinstance(envelope["evidence"], list):
        raise ValueError("actions and evidence must be arrays")
    if envelope["error"] is not None and not isinstance(envelope["error"], (str, dict)):
        raise ValueError("error must be null, a string, or an object")
    if not isinstance(envelope["next_action"], str):
        raise ValueError("next_action must be a string")

    observation = envelope["observation"]
    for key in ("response_html", "script_source"):
        if key in observation and (
            not isinstance(observation[key], str)
            or not observation[key]
            or len(observation[key]) > _MAX_MOCK_SIZE
        ):
            raise ValueError(f"{key} must be a non-empty mock string of at most {_MAX_MOCK_SIZE} characters")
    if "response_html" in observation:
        marker = observation.get("marker")
        if not isinstance(marker, str) or _MARKER.fullmatch(marker) is None:
            raise ValueError("response_html requires a short inert marker")
    elif "marker" in observation:
        raise ValueError("marker requires response_html")
    return envelope


def analyze_mock(envelope: Any) -> dict[str, Any]:
    """Return a B v1 envelope with candidate evidence, never a final verdict.

    The input observation may contain ``response_html`` plus an inert ``marker``
    and/or ``script_source``. Raw input content is not included in the output.
    Invalid envelopes raise ``ValueError`` and produce no output envelope.
    """
    source = _validate_input(envelope)
    observation = source["observation"]
    checked: list[str] = []
    evidence: list[dict[str, Any]] = []
    actions: list[dict[str, str]] = []

    if source["error"] is None and "response_html" in observation:
        checked.append("reflection")
        actions.append({"kind": "offline_mock_reflection_check"})
        contexts = _reflection_contexts(observation["response_html"], observation["marker"])
        if contexts:
            evidence.append({"kind": "reflected_marker_candidate", "contexts": contexts})
    if source["error"] is None and "script_source" in observation:
        checked.append("dom")
        actions.append({"kind": "offline_mock_dom_check"})
        evidence.extend(_dom_candidates(observation["script_source"]))

    ran = bool(checked)
    return {
        "contract_version": "1.0",
        "run_id": source["run_id"],
        "target_id": source["target_id"],
        "selected_module": "B",
        "producer": "B",
        "observation": {
            "mode": "offline_mock",
            "checked": checked,
            "candidate_count": len(evidence),
        },
        "actions": actions,
        "status": "UNKNOWN" if ran else "NOT_RUN",
        "evidence": evidence,
        "error": {"kind": "upstream_error"} if source["error"] is not None else None,
        "next_action": (
            "Send candidates to Oracle for external verification" if evidence
            else "Review mock input; final classification remains with Oracle" if ran
            else "Provide mock observation or resolve upstream error before B analysis"
        ),
    }

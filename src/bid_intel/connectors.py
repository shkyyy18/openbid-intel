from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol

from .models import Notice


@dataclass(slots=True)
class ConnectorContext:
    fetch_text: Callable[[str], str]
    interval_seconds: float = 1.0
    max_pages: int = 1
    cutoff: datetime | None = None
    fetch_details: bool = True
    detail_budget: int = 0
    priority_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConnectorOutput:
    notices: list[Notice]
    warnings: list[str] = field(default_factory=list)


class SourceConnector(Protocol):
    type_name: str
    uses_detail_budget: bool

    def collect(self, source: dict[str, Any], context: ConnectorContext) -> ConnectorOutput:
        ...


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector) -> None:
        type_name = connector.type_name.strip()
        if not type_name:
            raise ValueError("connector type_name must not be empty")
        if type_name in self._connectors:
            raise ValueError(f"connector already registered: {type_name}")
        self._connectors[type_name] = connector

    def get(self, type_name: str) -> SourceConnector:
        try:
            return self._connectors[type_name]
        except KeyError as exc:
            supported = ", ".join(sorted(self._connectors)) or "none"
            raise ValueError(f"unsupported source type: {type_name}; supported: {supported}") from exc

    def types(self) -> tuple[str, ...]:
        return tuple(sorted(self._connectors))

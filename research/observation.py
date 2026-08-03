from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Observation:
    """Immutable accepted observation record."""

    observation_id: str

    symbol_id: str

    statement: str

    evidence_refs: list[str]

    importance: int

    effective_time: str

    created_at: str

    research_cycle_id: str

    ai_call_id: str

    schema_version: str = "1.0"

    duplicate_of: Optional[str] = None
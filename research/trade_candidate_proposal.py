"""Deterministic read-only trade candidate proposal readiness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from research.promotion_candidate import PromotionCandidateDecision, PromotionCandidateEvaluation


class TradeCandidateProposalDecision(str, Enum):
    """Trade-candidate proposal readiness outcome."""

    PROPOSAL_READY = "proposal_ready"
    NOT_READY = "not_ready"


_REQUIRED_COMPONENTS = (
    "entry_logic",
    "exit_logic",
    "invalidation_logic",
    "position_sizing",
    "risk_limits",
    "demo_parameters",
)


@dataclass(frozen=True, slots=True)
class TradeCandidateProposalReadiness:
    """Read-only trade-candidate proposal readiness for one hypothesis."""

    hypothesis_id: str
    hypothesis_title: str
    decision: TradeCandidateProposalDecision
    source_decision: PromotionCandidateDecision
    required_components: tuple[str, ...] = field(default_factory=tuple)
    missing_components: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""


def evaluate_trade_candidate_proposals(
    promotion_candidate_evaluations: Iterable[PromotionCandidateEvaluation],
) -> list[TradeCandidateProposalReadiness]:
    """Evaluate which research candidates are ready for trade-candidate proposal design."""

    readiness_items: list[TradeCandidateProposalReadiness] = []
    for evaluation in promotion_candidate_evaluations:
        if evaluation.decision == PromotionCandidateDecision.CANDIDATE:
            readiness_items.append(
                TradeCandidateProposalReadiness(
                    hypothesis_id=evaluation.hypothesis_id,
                    hypothesis_title=evaluation.hypothesis_title,
                    decision=TradeCandidateProposalDecision.PROPOSAL_READY,
                    source_decision=evaluation.decision,
                    required_components=_REQUIRED_COMPONENTS,
                    missing_components=_REQUIRED_COMPONENTS,
                    rationale=(
                        "Research candidate has enough evidence for trade-candidate design, "
                        "but no executable trade proposal exists yet."
                    ),
                )
            )
            continue

        readiness_items.append(
            TradeCandidateProposalReadiness(
                hypothesis_id=evaluation.hypothesis_id,
                hypothesis_title=evaluation.hypothesis_title,
                decision=TradeCandidateProposalDecision.NOT_READY,
                source_decision=evaluation.decision,
                required_components=(),
                missing_components=(),
                rationale="Hypothesis is not a qualified research candidate.",
            )
        )

    return readiness_items
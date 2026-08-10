"""Deterministic read-only gate evaluation for proposed demo trade candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_candidate import validate_demo_trade_candidate
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.promotion_candidate import PromotionCandidateDecision
from research.promotion_candidate import PromotionCandidateEvaluation


class DemoTradeGateDecision(str, Enum):
    """Read-only demo trade gate outcomes."""

    GATE_PASS = "gate_pass"
    GATE_FAIL = "gate_fail"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True, slots=True)
class DemoTradeGateEvaluation:
    """Deterministic gate evaluation for one demo trade candidate."""

    trade_candidate_id: str
    source_hypothesis_id: str
    status: DemoTradeCandidateStatus
    decision: DemoTradeGateDecision
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    risk_flags: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""


_VALIDATION_ERROR_TO_CHECK = {
    "source_hypothesis_id is required": "source_hypothesis_id_missing",
    "symbol is required": "symbol_missing",
    "entry_logic is required": "entry_logic_missing",
    "exit_logic is required": "exit_logic_missing",
    "invalidation_logic is required": "invalidation_logic_missing",
    "maximum_holding_period is required": "maximum_holding_period_missing",
    "position_sizing_rule is required": "position_sizing_rule_missing",
    "monitoring_frequency is required": "monitoring_frequency_missing",
    "demo_only must be true": "demo_only_false",
    "max_loss_per_trade must be positive": "max_loss_per_trade_non_positive",
    "max_loss_per_trade must not exceed 0.02": "max_loss_per_trade_above_limit",
    "max_portfolio_exposure must be positive": "max_portfolio_exposure_non_positive",
    "max_portfolio_exposure must not exceed 0.10": "max_portfolio_exposure_above_limit",
    "status must be allowed": "invalid_status",
}


def _normalized_logic(value: str) -> str:
    return " ".join(value.split()).casefold()


def _append_failed_check(failed_checks: list[str], check_name: str) -> None:
    if check_name not in failed_checks:
        failed_checks.append(check_name)


def evaluate_demo_trade_gate(
    candidates: Iterable[DemoTradeCandidate],
    promotion_evaluations: Iterable[PromotionCandidateEvaluation],
) -> list[DemoTradeGateEvaluation]:
    """Evaluate deterministic read-only gate checks for demo trade candidates."""

    promotion_by_hypothesis_id = {
        evaluation.hypothesis_id: evaluation
        for evaluation in promotion_evaluations
    }

    evaluations: list[DemoTradeGateEvaluation] = []
    for candidate in candidates:
        if candidate.status != DemoTradeCandidateStatus.PROPOSED:
            evaluations.append(
                DemoTradeGateEvaluation(
                    trade_candidate_id=candidate.trade_candidate_id,
                    source_hypothesis_id=candidate.source_hypothesis_id,
                    status=candidate.status,
                    decision=DemoTradeGateDecision.NOT_EVALUATED,
                    risk_flags=tuple(candidate.risk_flags),
                    rationale="Only proposed demo trade candidates are evaluated by the demo gate.",
                )
            )
            continue

        failed_checks: list[str] = []

        try:
            validate_demo_trade_candidate(candidate)
        except ValueError as exc:
            _append_failed_check(
                failed_checks,
                _VALIDATION_ERROR_TO_CHECK.get(str(exc), "candidate_validation_failed"),
            )

        if not candidate.demo_only:
            _append_failed_check(failed_checks, "demo_only_false")

        promotion_evaluation = promotion_by_hypothesis_id.get(candidate.source_hypothesis_id)
        if promotion_evaluation is None:
            _append_failed_check(failed_checks, "source_research_candidate_missing")
        else:
            if promotion_evaluation.decision != PromotionCandidateDecision.CANDIDATE:
                _append_failed_check(failed_checks, "source_research_candidate_not_qualified")

            if not promotion_evaluation.review_current:
                _append_failed_check(failed_checks, "latest_review_not_current")

            if promotion_evaluation.evidence_status != HypothesisEvidenceStatus.PROMISING:
                _append_failed_check(failed_checks, "source_evidence_not_promising")

        if candidate.max_loss_per_trade > 0.02:
            _append_failed_check(failed_checks, "max_loss_per_trade_above_limit")

        if candidate.max_portfolio_exposure > 0.10:
            _append_failed_check(failed_checks, "max_portfolio_exposure_above_limit")

        if not candidate.pause_conditions:
            _append_failed_check(failed_checks, "pause_conditions_empty")

        entry_logic = _normalized_logic(candidate.entry_logic)
        exit_logic = _normalized_logic(candidate.exit_logic)
        invalidation_logic = _normalized_logic(candidate.invalidation_logic)

        if entry_logic and entry_logic == exit_logic:
            _append_failed_check(failed_checks, "entry_logic_matches_exit_logic")

        if entry_logic and entry_logic == invalidation_logic:
            _append_failed_check(failed_checks, "entry_logic_matches_invalidation_logic")

        if exit_logic and exit_logic == invalidation_logic:
            _append_failed_check(failed_checks, "exit_logic_matches_invalidation_logic")

        decision = (
            DemoTradeGateDecision.GATE_PASS
            if not failed_checks
            else DemoTradeGateDecision.GATE_FAIL
        )
        rationale = (
            "Candidate passes deterministic demo gate checks."
            if decision == DemoTradeGateDecision.GATE_PASS
            else "Candidate fails deterministic demo gate checks."
        )

        evaluations.append(
            DemoTradeGateEvaluation(
                trade_candidate_id=candidate.trade_candidate_id,
                source_hypothesis_id=candidate.source_hypothesis_id,
                status=candidate.status,
                decision=decision,
                failed_checks=tuple(failed_checks),
                risk_flags=tuple(candidate.risk_flags),
                rationale=rationale,
            )
        )

    return evaluations
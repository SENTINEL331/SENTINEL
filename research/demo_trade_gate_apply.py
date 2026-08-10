"""Append-only apply flow for deterministic demo trade gate outcomes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256

from ai.storage import Storage
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_gate import DemoTradeGateDecision
from research.demo_trade_gate import evaluate_demo_trade_gate
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.promotion_candidate import evaluate_promotion_candidates
from research.research_freshness import build_research_freshness


_SKIP_LATEST_STATUSES = {
    DemoTradeCandidateStatus.GATE_PASSED,
    DemoTradeCandidateStatus.GATE_FAILED,
    DemoTradeCandidateStatus.IN_DEMO,
    DemoTradeCandidateStatus.DEMO_COMPLETED,
    DemoTradeCandidateStatus.PROMOTED,
    DemoTradeCandidateStatus.REJECTED,
}


@dataclass(frozen=True, slots=True)
class DemoTradeGateApplyItem:
    trade_candidate_id: str
    source_hypothesis_id: str
    previous_status: DemoTradeCandidateStatus
    new_status: DemoTradeCandidateStatus
    decision: DemoTradeGateDecision


@dataclass(frozen=True, slots=True)
class DemoTradeGateApplyResult:
    apply_mode: bool
    candidates_loaded: int
    gate_evaluated: int
    would_pass: int
    would_fail: int
    applied_passed: int
    applied_failed: int
    skipped_existing: int
    applied_results: tuple[DemoTradeGateApplyItem, ...]


class DemoTradeGateApplyService:
    """Apply deterministic demo trade gate outcomes in dry-run or append-only mode."""

    def __init__(self, storage=None):
        self.storage = storage or Storage()

    def _now(self):
        return datetime.now(timezone.utc)

    def _lineage_key(self, candidate: DemoTradeCandidate) -> str:
        return candidate.source_trade_candidate_id or candidate.trade_candidate_id

    def _latest_timestamp(self, candidate: DemoTradeCandidate) -> datetime:
        return candidate.gate_checked_at or candidate.created_at

    def _select_latest_candidates(self, candidates: list[DemoTradeCandidate]) -> list[DemoTradeCandidate]:
        ordered_keys: list[str] = []
        latest_by_key: dict[str, DemoTradeCandidate] = {}

        for candidate in candidates:
            key = self._lineage_key(candidate)
            existing = latest_by_key.get(key)
            if existing is None:
                ordered_keys.append(key)
                latest_by_key[key] = candidate
                continue

            if self._latest_timestamp(candidate) >= self._latest_timestamp(existing):
                latest_by_key[key] = candidate

        return [latest_by_key[key] for key in ordered_keys]

    def _new_transition_candidate_id(
        self,
        symbol: str,
        root_trade_candidate_id: str,
        new_status: DemoTradeCandidateStatus,
        checked_at: datetime,
    ) -> str:
        digest = sha256(
            f"{symbol}|{root_trade_candidate_id}|{new_status.value}|{checked_at.isoformat()}".encode("utf-8")
        ).hexdigest()[:12]
        return f"dtc-{symbol}-{digest}"

    def _build_transition_candidate(
        self,
        candidate: DemoTradeCandidate,
        *,
        new_status: DemoTradeCandidateStatus,
        decision: DemoTradeGateDecision,
        failed_checks: tuple[str, ...],
        rationale: str,
        checked_at: datetime,
    ) -> DemoTradeCandidate:
        root_trade_candidate_id = self._lineage_key(candidate)

        return replace(
            candidate,
            trade_candidate_id=self._new_transition_candidate_id(
                candidate.symbol,
                root_trade_candidate_id,
                new_status,
                checked_at,
            ),
            source_trade_candidate_id=root_trade_candidate_id,
            created_at=checked_at,
            status=new_status,
            gate_checked_at=checked_at,
            gate_decision=decision.value,
            failed_checks=failed_checks,
            gate_rationale=rationale,
            created_by="sentinel",
        )

    def apply_for_symbol(self, symbol: str, apply_mode: bool = False) -> DemoTradeGateApplyResult:
        if not symbol:
            raise ValueError("symbol is required")

        hypotheses = self.storage.load_hypotheses(symbol)
        observations = self.storage.load_observations(symbol)
        experiment_requests = self.storage.load_experiment_requests(symbol)
        experiment_results = self.storage.load_experiment_results(symbol)
        hypothesis_reviews = self.storage.load_hypothesis_reviews(symbol)
        revision_proposals = self.storage.load_hypothesis_revision_proposals(symbol)
        candidates = self.storage.load_demo_trade_candidates(symbol=symbol)

        evidence_summaries = evaluate_hypothesis_evidence(
            hypotheses=hypotheses,
            experiment_results=experiment_results,
            experiment_requests=experiment_requests,
        )
        latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
        lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
            hypotheses=hypotheses,
            evidence_summaries=evidence_summaries,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
        )
        freshness_items = build_research_freshness(
            hypotheses=hypotheses,
            observations=observations,
            experiment_requests=experiment_requests,
            experiment_results=experiment_results,
            hypothesis_reviews=hypothesis_reviews,
            revision_proposals=revision_proposals,
            lifecycle_recommendations=lifecycle_recommendations,
        )
        promotion_evaluations = evaluate_promotion_candidates(
            hypotheses=hypotheses,
            evidence_summaries=evidence_summaries,
            freshness_items=freshness_items,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
        )

        latest_candidates = self._select_latest_candidates(candidates)
        skipped_existing = sum(
            1 for candidate in latest_candidates if candidate.status in _SKIP_LATEST_STATUSES
        )
        proposed_latest_candidates = [
            candidate
            for candidate in latest_candidates
            if candidate.status == DemoTradeCandidateStatus.PROPOSED
        ]
        gate_evaluations = evaluate_demo_trade_gate(proposed_latest_candidates, promotion_evaluations)

        applied_results: list[DemoTradeGateApplyItem] = []
        applied_passed = 0
        applied_failed = 0
        checked_at = self._now()

        candidate_by_id = {
            candidate.trade_candidate_id: candidate
            for candidate in proposed_latest_candidates
        }

        for evaluation in gate_evaluations:
            candidate = candidate_by_id[evaluation.trade_candidate_id]
            new_status = (
                DemoTradeCandidateStatus.GATE_PASSED
                if evaluation.decision == DemoTradeGateDecision.GATE_PASS
                else DemoTradeCandidateStatus.GATE_FAILED
            )

            if apply_mode:
                transitioned_candidate = self._build_transition_candidate(
                    candidate,
                    new_status=new_status,
                    decision=evaluation.decision,
                    failed_checks=evaluation.failed_checks,
                    rationale=evaluation.rationale,
                    checked_at=checked_at,
                )
                self.storage.save_demo_trade_candidate(transitioned_candidate)
                if new_status == DemoTradeCandidateStatus.GATE_PASSED:
                    applied_passed += 1
                else:
                    applied_failed += 1

            applied_results.append(
                DemoTradeGateApplyItem(
                    trade_candidate_id=candidate.trade_candidate_id,
                    source_hypothesis_id=candidate.source_hypothesis_id,
                    previous_status=candidate.status,
                    new_status=new_status,
                    decision=evaluation.decision,
                )
            )

        would_pass = sum(
            1 for evaluation in gate_evaluations if evaluation.decision == DemoTradeGateDecision.GATE_PASS
        )
        would_fail = sum(
            1 for evaluation in gate_evaluations if evaluation.decision == DemoTradeGateDecision.GATE_FAIL
        )

        return DemoTradeGateApplyResult(
            apply_mode=apply_mode,
            candidates_loaded=len(candidates),
            gate_evaluated=len(gate_evaluations),
            would_pass=would_pass,
            would_fail=would_fail,
            applied_passed=applied_passed,
            applied_failed=applied_failed,
            skipped_existing=skipped_existing,
            applied_results=tuple(applied_results),
        )
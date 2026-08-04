"""Deterministic evidence summarization for hypotheses."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from research.experiment import ExperimentRequest
from research.experiment_result import ExperimentResult, ExperimentResultStatus
from research.hypothesis import Hypothesis


class HypothesisEvidenceStatus(str, Enum):
    """Conservative deterministic evidence labels for hypothesis summaries."""

    UNTESTED = "untested"
    INSUFFICIENT_DATA = "insufficient_data"
    MIXED = "mixed"
    PROMISING = "promising"
    WEAK = "weak"


@dataclass(frozen=True, slots=True)
class HypothesisEvidenceSummary:
    """Aggregated completed experiment evidence for one hypothesis."""

    hypothesis_id: str
    hypothesis_title: str
    completed_experiment_count: int
    total_trade_count: int
    average_return: float | None
    win_rate: float | None
    best_return: float | None
    worst_return: float | None
    evidence_status: HypothesisEvidenceStatus


_MIN_COMPLETED_EXPERIMENTS = 2
_MIN_TOTAL_TRADES = 20
_PROMISING_MIN_WIN_RATE = 0.55
_WEAK_MAX_WIN_RATE = 0.45


def _mean(values: list[float]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def _classify_evidence_status(
    completed_experiment_count: int,
    total_trade_count: int,
    average_return: float | None,
    win_rate: float | None,
) -> HypothesisEvidenceStatus:
    if completed_experiment_count == 0:
        return HypothesisEvidenceStatus.UNTESTED

    if (
        completed_experiment_count < _MIN_COMPLETED_EXPERIMENTS
        or total_trade_count < _MIN_TOTAL_TRADES
        or average_return is None
        or win_rate is None
    ):
        return HypothesisEvidenceStatus.INSUFFICIENT_DATA

    if average_return > 0 and win_rate >= _PROMISING_MIN_WIN_RATE:
        return HypothesisEvidenceStatus.PROMISING

    if average_return < 0 and win_rate <= _WEAK_MAX_WIN_RATE:
        return HypothesisEvidenceStatus.WEAK

    return HypothesisEvidenceStatus.MIXED


def evaluate_hypothesis_evidence(
    hypotheses: Iterable[Hypothesis],
    experiment_results: Iterable[ExperimentResult],
    experiment_requests: Iterable[ExperimentRequest] = (),
) -> list[HypothesisEvidenceSummary]:
    """Summarize completed experiment evidence for each hypothesis."""

    request_hypothesis_ids = {
        request.experiment_request_id: request.hypothesis_id
        for request in experiment_requests
        if request.experiment_request_id and request.hypothesis_id
    }

    grouped_results: dict[str, list[ExperimentResult]] = defaultdict(list)
    for result in experiment_results:
        if result.status != ExperimentResultStatus.COMPLETED:
            continue

        resolved_hypothesis_id = result.hypothesis_id
        if not resolved_hypothesis_id:
            resolved_hypothesis_id = request_hypothesis_ids.get(result.experiment_request_id, "")

        if not resolved_hypothesis_id:
            continue

        grouped_results[resolved_hypothesis_id].append(result)

    summaries: list[HypothesisEvidenceSummary] = []
    for hypothesis in hypotheses:
        completed_results = grouped_results.get(hypothesis.hypothesis_id, [])

        trade_counts = [
            result.metrics.trade_count
            for result in completed_results
            if result.metrics.trade_count is not None
        ]
        average_returns = [
            result.metrics.average_return
            for result in completed_results
            if result.metrics.average_return is not None
        ]
        win_rates = [
            result.metrics.win_rate
            for result in completed_results
            if result.metrics.win_rate is not None
        ]
        best_returns = [
            result.metrics.extra_metrics["best_return"]
            for result in completed_results
            if "best_return" in result.metrics.extra_metrics
        ]
        worst_returns = [
            result.metrics.extra_metrics["worst_return"]
            for result in completed_results
            if "worst_return" in result.metrics.extra_metrics
        ]

        total_trade_count = sum(trade_counts) if trade_counts else 0
        average_return = _mean(average_returns)
        win_rate = _mean(win_rates)
        best_return = max(best_returns) if best_returns else None
        worst_return = min(worst_returns) if worst_returns else None

        evidence_status = _classify_evidence_status(
            completed_experiment_count=len(completed_results),
            total_trade_count=total_trade_count,
            average_return=average_return,
            win_rate=win_rate,
        )

        summaries.append(
            HypothesisEvidenceSummary(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_title=hypothesis.title,
                completed_experiment_count=len(completed_results),
                total_trade_count=total_trade_count,
                average_return=average_return,
                win_rate=win_rate,
                best_return=best_return,
                worst_return=worst_return,
                evidence_status=evidence_status,
            )
        )

    return summaries
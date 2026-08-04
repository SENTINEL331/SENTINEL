import json

from ai.journal import ResearchJournal
from ai.storage import Storage
from research.experiment import ExperimentRequestExecutionState
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.parser import parse_hypothesis_reviews


class HypothesisReviewService:
    """Coordinate hypothesis review generation for a single symbol."""

    def __init__(self, ai_client=None, storage=None, journal_builder=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()
        self.journal_builder = journal_builder or ResearchJournal()
        self.journal_builder.storage = self.storage

    def _format_percent(self, value):
        if value is None:
            return "n/a"

        return f"{value * 100:.2f}%"

    def _build_deterministic_review_context(
        self,
        symbol,
        hypotheses,
        experiment_requests,
        experiment_results,
    ):
        request_by_id = {
            request.experiment_request_id: request
            for request in experiment_requests
            if request.experiment_request_id
        }

        completed_executable_results = []
        excluded_non_completed_count = 0
        excluded_non_executable_count = 0

        for result in experiment_results:
            if result.status != ExperimentResultStatus.COMPLETED:
                excluded_non_completed_count += 1
                continue

            request = request_by_id.get(result.experiment_request_id)
            if request is None:
                excluded_non_executable_count += 1
                continue

            if request.execution_state != ExperimentRequestExecutionState.EXECUTABLE:
                excluded_non_executable_count += 1
                continue

            completed_executable_results.append(result)

        evidence_summaries = evaluate_hypothesis_evidence(
            hypotheses=hypotheses,
            experiment_results=completed_executable_results,
            experiment_requests=experiment_requests,
        )

        lines = [
            f"Hypothesis Review Context: {symbol}",
            "",
            "Evidence Policy",
            "---------------",
            "Use only completed experiment results linked to executable requests.",
            "Exclude failed, not_implemented, and legacy non-executable or obsolete request evidence.",
            f"Included Completed Executable Results: {len(completed_executable_results)}",
            f"Excluded Non-Completed Results: {excluded_non_completed_count}",
            f"Excluded Non-Executable/Legacy Results: {excluded_non_executable_count}",
            "",
            "Hypothesis Evidence",
            "-------------------",
        ]

        if evidence_summaries:
            for summary in evidence_summaries:
                lines.append(
                    f"- {summary.hypothesis_title} "
                    f"[{summary.evidence_status.value}] "
                    f"id={summary.hypothesis_id}"
                )
                lines.append(
                    "  completed_experiments="
                    f"{summary.completed_experiment_count}, "
                    f"trade_count={summary.total_trade_count}, "
                    f"average_return={self._format_percent(summary.average_return)}, "
                    f"win_rate={self._format_percent(summary.win_rate)}, "
                    f"best_return={self._format_percent(summary.best_return)}, "
                    f"worst_return={self._format_percent(summary.worst_return)}"
                )
                if summary.evidence_status.value == "insufficient_data":
                    lines.append(
                        "  note: Evidence is currently insufficient; prioritize additional executable completed tests."
                    )
        else:
            lines.append("No hypothesis evidence available.")

        return "\n".join(lines)

    def _render_hypotheses(self, hypotheses):
        if isinstance(hypotheses, str):
            return hypotheses

        serialized = []

        for hypothesis in hypotheses:
            if isinstance(hypothesis, Hypothesis):
                serialized.append(
                    {
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "symbol": hypothesis.symbol,
                        "title": hypothesis.title,
                        "description": hypothesis.description,
                        "status": hypothesis.status.value,
                        "confidence": hypothesis.confidence,
                        "experiment_refs": list(hypothesis.experiment_refs),
                    }
                )
                continue

            if isinstance(hypothesis, dict):
                serialized.append(hypothesis)
                continue

            raise ValueError("hypotheses must be a JSON string, dicts, or Hypothesis objects")

        return json.dumps(serialized, indent=4)

    def generate_for_symbol(
        self,
        symbol,
        journal=None,
        hypotheses=None,
    ):
        """Generate, parse, store, and return hypothesis reviews for one symbol."""

        if not symbol:
            raise ValueError("symbol is required")

        resolved_hypotheses = hypotheses if hypotheses is not None else self.storage.load_hypotheses(symbol)
        hypothesis_payload = self._render_hypotheses(resolved_hypotheses)

        experiment_requests = self.storage.load_experiment_requests(symbol)
        experiment_results = self.storage.load_experiment_results(symbol)

        if journal is not None:
            resolved_journal = journal
        else:
            resolved_journal = self._build_deterministic_review_context(
                symbol=symbol,
                hypotheses=resolved_hypotheses,
                experiment_requests=experiment_requests,
                experiment_results=experiment_results,
            )

        response = self.ai.hypothesis_review(
            symbol=symbol,
            journal=resolved_journal,
            hypotheses=hypothesis_payload,
        )

        reviews = parse_hypothesis_reviews(symbol, response)

        self.storage.save_hypothesis_reviews(symbol, reviews)

        return reviews

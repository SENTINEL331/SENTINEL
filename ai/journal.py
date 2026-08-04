from ai.storage import Storage
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence


class ResearchJournal:
    """
    Builds the AI's research journal from
    Sentinel's persistent stores.
    """

    def __init__(self):

        self.storage = Storage()

    def _is_active_hypothesis(self, status):
        return status in {
            HypothesisStatus.PROPOSED,
            HypothesisStatus.ACTIVE,
        }

    def _format_hypothesis(self, hypothesis):
        confidence = f"{hypothesis.confidence:.2f}"
        return (
            f"- {hypothesis.title} "
            f"[{hypothesis.status.value}] "
            f"confidence={confidence} "
            f"id={hypothesis.hypothesis_id}"
        )

    def _format_experiment_request(self, experiment_request):
        return (
            f"- {experiment_request.title} "
            f"[{experiment_request.status.value}] "
            f"test_type={experiment_request.test_type.value} "
            f"id={experiment_request.experiment_request_id}"
            "\n"
            f"  objective: {experiment_request.objective}"
        )

    def _format_experiment_result(self, experiment_result):
        metric_parts = []

        if experiment_result.metrics.total_return is not None:
            metric_parts.append(f"total_return={experiment_result.metrics.total_return:.4f}")

        if experiment_result.metrics.win_rate is not None:
            metric_parts.append(f"win_rate={experiment_result.metrics.win_rate:.4f}")

        if experiment_result.metrics.max_drawdown is not None:
            metric_parts.append(
                f"max_drawdown={experiment_result.metrics.max_drawdown:.4f}"
            )

        if experiment_result.metrics.trade_count is not None:
            metric_parts.append(f"trade_count={experiment_result.metrics.trade_count}")

        if experiment_result.metrics.profit_factor is not None:
            metric_parts.append(
                f"profit_factor={experiment_result.metrics.profit_factor:.4f}"
            )

        metrics_text = ", ".join(metric_parts) if metric_parts else "no key metrics"

        detail = experiment_result.summary or experiment_result.failure_reason or "No summary."

        return (
            f"- {experiment_result.test_type.value} "
            f"[{experiment_result.status.value}] "
            f"id={experiment_result.experiment_result_id}"
            "\n"
            f"  metrics: {metrics_text}"
            "\n"
            f"  detail: {detail}"
        )

    def _format_percent(self, value):
        if value is None:
            return "n/a"

        return f"{value * 100:.2f}%"

    def _format_hypothesis_evidence(self, evidence_summary):
        return (
            f"- {evidence_summary.hypothesis_title} "
            f"[{evidence_summary.evidence_status.value}] "
            f"id={evidence_summary.hypothesis_id}"
            "\n"
            f"  completed_experiments={evidence_summary.completed_experiment_count}, "
            f"trade_count={evidence_summary.total_trade_count}, "
            f"average_return={self._format_percent(evidence_summary.average_return)}, "
            f"win_rate={self._format_percent(evidence_summary.win_rate)}, "
            f"best_return={self._format_percent(evidence_summary.best_return)}, "
            f"worst_return={self._format_percent(evidence_summary.worst_return)}"
        )

    def _select_latest_hypothesis_reviews(self, hypothesis_reviews):
        latest_reviews = {}

        for review in hypothesis_reviews:
            previous = latest_reviews.get(review.hypothesis_id)

            if previous is None:
                latest_reviews[review.hypothesis_id] = review
                continue

            if review.created_at > previous.created_at:
                latest_reviews[review.hypothesis_id] = review
                continue

            # Preserve deterministic selection when timestamps are equal.
            if review.created_at == previous.created_at and review.review_id > previous.review_id:
                latest_reviews[review.hypothesis_id] = review

        return latest_reviews

    def _format_latest_hypothesis_review(self, review, hypothesis_title):
        confidence = f"{review.confidence:.2f}"
        created_at = f", created_at={review.created_at.isoformat()}" if review.created_at else ""

        return (
            f"- {hypothesis_title} id={review.hypothesis_id}"
            "\n"
            f"  recommendation={review.recommendation.value}, confidence={confidence}{created_at}"
            "\n"
            f"  rationale: {review.rationale}"
        )

    def build(
        self,
        symbol,
    ):
        """
        Build a journal for one symbol.
        """

        observations = self.storage.load_observations(symbol)
        hypotheses = self.storage.load_hypotheses(symbol)
        experiment_requests = self.storage.load_experiment_requests(symbol)
        experiment_results = self.storage.load_experiment_results(symbol)
        load_hypothesis_reviews = getattr(self.storage, "load_hypothesis_reviews", None)
        hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []
        hypothesis_evidence = evaluate_hypothesis_evidence(
            hypotheses=hypotheses,
            experiment_results=experiment_results,
            experiment_requests=experiment_requests,
        )
        latest_reviews_by_hypothesis_id = self._select_latest_hypothesis_reviews(
            hypothesis_reviews
        )
        active_hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if self._is_active_hypothesis(hypothesis.status)
        ]

        lines = []

        lines.append(f"Research Journal: {symbol}")
        lines.append("")
        lines.append("Observations")
        lines.append("------------")

        if observations:

            for observation in observations:

                lines.append(
                    f"- {observation.statement}"
                )

        else:

            lines.append(
                "No previous observations."
            )

        lines.append("")
        lines.append("Hypotheses")
        lines.append("----------")

        if active_hypotheses:

            for hypothesis in active_hypotheses:

                lines.append(
                    self._format_hypothesis(hypothesis)
                )

        else:

            lines.append(
                "No active hypotheses."
            )

        lines.append("")
        lines.append("Experiment Requests")
        lines.append("-------------------")

        if experiment_requests:

            for experiment_request in experiment_requests:

                lines.append(
                    self._format_experiment_request(experiment_request)
                )

        else:

            lines.append(
                "No experiment requests."
            )

        lines.append("")
        lines.append("Experiment Results")
        lines.append("------------------")

        if experiment_results:

            for experiment_result in experiment_results:

                lines.append(
                    self._format_experiment_result(experiment_result)
                )

        else:

            lines.append(
                "No experiment results."
            )

        lines.append("")
        lines.append("Hypothesis Evidence")
        lines.append("-------------------")

        if hypothesis_evidence:

            for evidence_summary in hypothesis_evidence:

                lines.append(
                    self._format_hypothesis_evidence(evidence_summary)
                )

        else:

            lines.append(
                "No hypothesis evidence."
            )

        lines.append("")
        lines.append("Latest Hypothesis Reviews")
        lines.append("-------------------------")

        hypothesis_review_lines = []
        for hypothesis in hypotheses:
            review = latest_reviews_by_hypothesis_id.get(hypothesis.hypothesis_id)

            if review is None:
                continue

            hypothesis_review_lines.append(
                self._format_latest_hypothesis_review(
                    review,
                    hypothesis.title,
                )
            )

        if hypothesis_review_lines:
            lines.extend(hypothesis_review_lines)
        else:
            lines.append("No hypothesis reviews.")

        return "\n".join(lines)
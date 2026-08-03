from ai.storage import Storage
from research.hypothesis import HypothesisStatus


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

        return "\n".join(lines)
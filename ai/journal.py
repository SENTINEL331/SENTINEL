from ai.storage import Storage
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus


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

    def _format_lifecycle_recommendation(self, recommendation):
        lines = [
            (
                f"- {recommendation.hypothesis_title} "
                f"[{recommendation.current_status.value}] "
                f"id={recommendation.hypothesis_id} "
                f"action={recommendation.action.value}"
            ),
            (
                "  evidence="
                f"{recommendation.evidence_status.value}, "
                f"completed_experiments={recommendation.completed_experiment_count}, "
                f"trade_count={recommendation.total_trade_count}"
            ),
        ]

        if recommendation.review_recommendation is not None:
            lines.append(
                "  latest_review="
                f"{recommendation.review_recommendation.value}"
            )

        lines.append(f"  rationale: {recommendation.rationale}")

        return "\n".join(lines)

    def _format_revision_proposal(
        self,
        proposal,
        applied_status,
        child_hypothesis_id,
    ):
        lines = [
            (
                f"- parent_id={proposal.parent_hypothesis_id} "
                f"proposal_type={proposal.proposal_type.value} "
                f"lifecycle_action={proposal.lifecycle_action.value} "
                f"confidence={proposal.confidence:.2f} "
                f"id={proposal.proposal_id}"
            )
        ]

        if proposal.proposed_title:
            lines.append(f"  proposed_title: {proposal.proposed_title}")

        if proposal.proposed_description:
            lines.append(f"  proposed_description: {proposal.proposed_description}")

        lines.append(f"  applied_status={applied_status}")
        lines.append(f"  child_hypothesis_id={child_hypothesis_id or 'none'}")
        lines.append(f"  rationale: {proposal.rationale}")

        return "\n".join(lines)

    def _format_hypothesis_lineage(self, hypothesis):
        lineage_text = (
            ",".join(hypothesis.lineage_hypothesis_ids)
            if hypothesis.lineage_hypothesis_ids
            else "none"
        )
        source_proposal_id = hypothesis.source_revision_proposal_id or "none"
        parent_id = hypothesis.parent_hypothesis_id or "none"

        return (
            f"- {hypothesis.title} id={hypothesis.hypothesis_id} "
            f"parent_id={parent_id} "
            f"source_revision_proposal_id={source_proposal_id} "
            f"lineage={lineage_text}"
        )

    def _select_latest_application_by_proposal_id(self, applications):
        latest_by_proposal_id = {}

        for application in applications:
            existing = latest_by_proposal_id.get(application.proposal_id)

            if existing is None or application.created_at >= existing.created_at:
                latest_by_proposal_id[application.proposal_id] = application

        return latest_by_proposal_id
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
        load_hypothesis_revision_proposals = getattr(
            self.storage,
            "load_hypothesis_revision_proposals",
            None,
        )
        revision_proposals = (
            load_hypothesis_revision_proposals(symbol)
            if callable(load_hypothesis_revision_proposals)
            else []
        )
        load_hypothesis_revision_applications = getattr(
            self.storage,
            "load_hypothesis_revision_applications",
            None,
        )
        revision_applications = (
            load_hypothesis_revision_applications(symbol)
            if callable(load_hypothesis_revision_applications)
            else []
        )
        hypothesis_evidence = evaluate_hypothesis_evidence(
            hypotheses=hypotheses,
            experiment_results=experiment_results,
            experiment_requests=experiment_requests,
        )
        latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(
            hypothesis_reviews
        )
        lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
            hypotheses=hypotheses,
            evidence_summaries=hypothesis_evidence,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
        )
        latest_applications_by_proposal_id = self._select_latest_application_by_proposal_id(
            revision_applications
        )
        child_by_proposal_id = {
            hypothesis.source_revision_proposal_id: hypothesis
            for hypothesis in hypotheses
            if hypothesis.source_revision_proposal_id is not None
        }
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

        lines.append("")
        lines.append("Hypothesis Lifecycle Recommendations")
        lines.append("------------------------------------")
        lines.append("Recommendations only; no hypothesis state is changed.")

        if lifecycle_recommendations:
            for recommendation in lifecycle_recommendations:
                lines.append(
                    self._format_lifecycle_recommendation(recommendation)
                )
        else:
            lines.append("No lifecycle recommendations.")

        lines.append("")
        lines.append("Hypothesis Revision Proposals")
        lines.append("-----------------------------")
        lines.append("Proposals are records only and are never auto-applied.")

        if revision_proposals:
            for proposal in revision_proposals:
                latest_application = latest_applications_by_proposal_id.get(
                    proposal.proposal_id
                )
                child_hypothesis = child_by_proposal_id.get(proposal.proposal_id)

                if child_hypothesis is not None:
                    applied_status = HypothesisRevisionApplicationStatus.APPLIED.value
                    child_hypothesis_id = child_hypothesis.hypothesis_id
                elif latest_application is not None:
                    applied_status = latest_application.status.value
                    child_hypothesis_id = latest_application.child_hypothesis_id
                else:
                    applied_status = "not_applied"
                    child_hypothesis_id = None

                lines.append(
                    self._format_revision_proposal(
                        proposal,
                        applied_status,
                        child_hypothesis_id,
                    )
                )
        else:
            lines.append("No hypothesis revision proposals.")

        lines.append("")
        lines.append("Hypothesis Lineage")
        lines.append("------------------")

        lineage_hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if (
                hypothesis.parent_hypothesis_id is not None
                or hypothesis.source_revision_proposal_id is not None
                or bool(hypothesis.lineage_hypothesis_ids)
            )
        ]

        if lineage_hypotheses:
            for hypothesis in lineage_hypotheses:
                lines.append(self._format_hypothesis_lineage(hypothesis))
        else:
            lines.append("No hypothesis lineage records.")

        return "\n".join(lines)
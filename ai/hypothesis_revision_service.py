import json

from ai.journal import ResearchJournal
from ai.storage import Storage
from research.hypothesis import Hypothesis
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.parser import parse_hypothesis_revision_proposals


class HypothesisRevisionService:
    """Coordinate append-only hypothesis revision proposal generation."""

    def __init__(self, ai_client=None, storage=None, journal_builder=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()
        self.journal_builder = journal_builder or ResearchJournal()
        self.journal_builder.storage = self.storage

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

    def _render_lifecycle_recommendations(self, lifecycle_recommendations):
        serialized = []

        for recommendation in lifecycle_recommendations:
            serialized.append(
                {
                    "hypothesis_id": recommendation.hypothesis_id,
                    "hypothesis_title": recommendation.hypothesis_title,
                    "current_status": recommendation.current_status.value,
                    "evidence_status": recommendation.evidence_status.value,
                    "completed_experiment_count": recommendation.completed_experiment_count,
                    "total_trade_count": recommendation.total_trade_count,
                    "action": recommendation.action.value,
                    "rationale": recommendation.rationale,
                    "review_id": recommendation.review_id,
                    "review_recommendation": (
                        recommendation.review_recommendation.value
                        if recommendation.review_recommendation is not None
                        else None
                    ),
                    "review_confidence": recommendation.review_confidence,
                }
            )

        return json.dumps(serialized, indent=4)

    def _eligible_lifecycle_recommendations(self, lifecycle_recommendations):
        return [
            recommendation
            for recommendation in lifecycle_recommendations
            if recommendation.action == HypothesisLifecycleAction.REFINE_CANDIDATE
        ]

    def generate_for_symbol(
        self,
        symbol,
        journal=None,
        hypotheses=None,
    ):
        """Generate, parse, store, and return revision proposals for one symbol."""

        if not symbol:
            raise ValueError("symbol is required")

        resolved_hypotheses = hypotheses if hypotheses is not None else self.storage.load_hypotheses(symbol)
        hypothesis_payload = self._render_hypotheses(resolved_hypotheses)

        experiment_requests = self.storage.load_experiment_requests(symbol)
        experiment_results = self.storage.load_experiment_results(symbol)
        load_hypothesis_reviews = getattr(self.storage, "load_hypothesis_reviews", None)
        hypothesis_reviews = load_hypothesis_reviews(symbol) if callable(load_hypothesis_reviews) else []

        evidence_summaries = evaluate_hypothesis_evidence(
            hypotheses=resolved_hypotheses,
            experiment_results=experiment_results,
            experiment_requests=experiment_requests,
        )
        latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(hypothesis_reviews)
        lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
            hypotheses=resolved_hypotheses,
            evidence_summaries=evidence_summaries,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
        )
        eligible_recommendations = self._eligible_lifecycle_recommendations(
            lifecycle_recommendations
        )

        if not eligible_recommendations:
            return []

        if journal is None:
            resolved_journal = self.journal_builder.build(symbol)
        else:
            resolved_journal = journal

        response = self.ai.hypothesis_revision_proposals(
            symbol=symbol,
            journal=resolved_journal,
            hypotheses=hypothesis_payload,
            lifecycle_recommendations=self._render_lifecycle_recommendations(
                eligible_recommendations
            ),
        )

        proposals = parse_hypothesis_revision_proposals(symbol, response)

        self.storage.save_hypothesis_revision_proposals(symbol, proposals)

        return proposals

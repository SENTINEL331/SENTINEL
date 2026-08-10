import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from ai.journal import ResearchJournal
from ai.storage import Storage
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_candidate import validate_demo_trade_candidate
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.parser import parse_demo_trade_candidate_proposals
from research.promotion_candidate import PromotionCandidateDecision
from research.promotion_candidate import evaluate_promotion_candidates
from research.research_freshness import build_research_freshness


_ACTIVE_DUPLICATE_STATUSES = {
    DemoTradeCandidateStatus.PROPOSED,
    DemoTradeCandidateStatus.GATE_PASSED,
    DemoTradeCandidateStatus.IN_DEMO,
}


@dataclass(frozen=True, slots=True)
class DemoTradeCandidateGenerationResult:
    research_candidates_loaded: int
    generation_candidates: int
    generated_candidates: tuple[DemoTradeCandidate, ...]
    skipped_existing: int
    failed_validation: int


class DemoTradeCandidateService:
    """Coordinate AI demo trade candidate generation for one symbol."""

    def __init__(self, ai_client=None, storage=None, journal_builder=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()
        self.journal_builder = journal_builder or ResearchJournal()
        self.journal_builder.storage = self.storage

    def _render_candidate_context(self, hypotheses_by_id, candidate_evaluations):
        serialized = []

        for evaluation in candidate_evaluations:
            hypothesis = hypotheses_by_id[evaluation.hypothesis_id]
            serialized.append(
                {
                    "symbol": hypothesis.symbol,
                    "source_hypothesis_id": evaluation.hypothesis_id,
                    "hypothesis_title": evaluation.hypothesis_title,
                    "hypothesis_description": hypothesis.description,
                    "source_research_candidate_decision": evaluation.decision.value,
                    "source_evidence_summary": {
                        "completed_experiments": evaluation.completed_experiments,
                        "trade_count": evaluation.trade_count,
                        "average_return": evaluation.average_return,
                        "win_rate": evaluation.win_rate,
                        "best_return": evaluation.best_return,
                        "worst_return": evaluation.worst_return,
                        "evidence_status": evaluation.evidence_status.value,
                    },
                    "source_review_action": (
                        evaluation.latest_review_action.value
                        if evaluation.latest_review_action is not None
                        else None
                    ),
                    "source_review_confidence": evaluation.latest_review_confidence,
                    "risk_flags": list(evaluation.risk_flags),
                    "rationale": evaluation.rationale,
                }
            )

        return json.dumps(serialized, indent=4)

    def _build_candidate_id(self, payload):
        digest = sha256(
            "|".join(
                [
                    payload["symbol"],
                    payload["source_hypothesis_id"],
                    payload["entry_logic"],
                    payload["exit_logic"],
                    payload["invalidation_logic"],
                    payload["maximum_holding_period"],
                    payload["position_sizing_rule"],
                    str(payload["max_loss_per_trade"]),
                    str(payload["max_portfolio_exposure"]),
                    payload["monitoring_frequency"],
                    json.dumps(payload["pause_conditions"]),
                ]
            ).encode("utf-8")
        ).hexdigest()[:12]

        return f"dtc-{payload['symbol']}-{digest}"

    def _build_domain_candidate(self, payload, source_context, ingested_at):
        return DemoTradeCandidate(
            trade_candidate_id=self._build_candidate_id(payload),
            symbol=source_context["symbol"],
            source_hypothesis_id=source_context["source_hypothesis_id"],
            source_research_candidate_decision=source_context["source_research_candidate_decision"],
            created_at=ingested_at,
            status=DemoTradeCandidateStatus.PROPOSED,
            entry_logic=payload["entry_logic"],
            exit_logic=payload["exit_logic"],
            invalidation_logic=payload["invalidation_logic"],
            maximum_holding_period=payload["maximum_holding_period"],
            position_sizing_rule=payload["position_sizing_rule"],
            max_loss_per_trade=payload["max_loss_per_trade"],
            max_portfolio_exposure=payload["max_portfolio_exposure"],
            demo_only=True,
            monitoring_frequency=payload["monitoring_frequency"],
            pause_conditions=payload["pause_conditions"],
            source_evidence_summary=source_context["source_evidence_summary"],
            source_review_action=source_context["source_review_action"],
            source_review_confidence=source_context["source_review_confidence"],
            risk_flags=source_context["risk_flags"],
            created_by="ai",
        )

    def generate_for_symbol(self, symbol, journal=None):
        """Generate, validate, persist, and summarize demo trade candidates."""

        if not symbol:
            raise ValueError("symbol is required")

        hypotheses = self.storage.load_hypotheses(symbol)
        hypotheses_by_id = {
            hypothesis.hypothesis_id: hypothesis
            for hypothesis in hypotheses
        }
        observations = self.storage.load_observations(symbol)
        experiment_requests = self.storage.load_experiment_requests(symbol)
        experiment_results = self.storage.load_experiment_results(symbol)
        hypothesis_reviews = self.storage.load_hypothesis_reviews(symbol)
        revision_proposals = self.storage.load_hypothesis_revision_proposals(symbol)

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

        research_candidates = [
            evaluation
            for evaluation in promotion_evaluations
            if evaluation.decision == PromotionCandidateDecision.CANDIDATE
        ]

        existing_candidates = self.storage.load_demo_trade_candidates(symbol=symbol)
        existing_candidate_keys = {
            (candidate.symbol, candidate.source_hypothesis_id)
            for candidate in existing_candidates
            if candidate.status in _ACTIVE_DUPLICATE_STATUSES
        }

        generation_candidate_evaluations = []
        skipped_existing = 0
        for evaluation in research_candidates:
            candidate_key = (
                hypotheses_by_id[evaluation.hypothesis_id].symbol,
                evaluation.hypothesis_id,
            )
            if candidate_key in existing_candidate_keys:
                skipped_existing += 1
                continue

            generation_candidate_evaluations.append(evaluation)

        if not generation_candidate_evaluations:
            return DemoTradeCandidateGenerationResult(
                research_candidates_loaded=len(research_candidates),
                generation_candidates=0,
                generated_candidates=(),
                skipped_existing=skipped_existing,
                failed_validation=0,
            )

        if journal is None:
            resolved_journal = self.journal_builder.build(symbol)
        else:
            resolved_journal = journal

        source_context_by_hypothesis_id = {
            evaluation.hypothesis_id: {
                "symbol": hypotheses_by_id[evaluation.hypothesis_id].symbol,
                "source_hypothesis_id": evaluation.hypothesis_id,
                "source_research_candidate_decision": evaluation.decision.value,
                "source_evidence_summary": {
                    "completed_experiments": evaluation.completed_experiments,
                    "trade_count": evaluation.trade_count,
                    "average_return": evaluation.average_return,
                    "win_rate": evaluation.win_rate,
                    "best_return": evaluation.best_return,
                    "worst_return": evaluation.worst_return,
                    "evidence_status": evaluation.evidence_status.value,
                },
                "source_review_action": (
                    evaluation.latest_review_action.value
                    if evaluation.latest_review_action is not None
                    else None
                ),
                "source_review_confidence": evaluation.latest_review_confidence,
                "risk_flags": tuple(evaluation.risk_flags),
            }
            for evaluation in generation_candidate_evaluations
        }

        response = self.ai.demo_trade_candidate_generation(
            symbol=symbol,
            journal=resolved_journal,
            qualified_candidates=self._render_candidate_context(
                hypotheses_by_id,
                generation_candidate_evaluations,
            ),
        )
        proposals = parse_demo_trade_candidate_proposals(symbol, response)

        generated_candidates = []
        failed_validation = 0
        seen_hypothesis_ids = set()
        ingested_at = datetime.now(timezone.utc)

        for payload in proposals:
            hypothesis_id = payload["source_hypothesis_id"]
            if hypothesis_id in seen_hypothesis_ids:
                failed_validation += 1
                continue

            source_context = source_context_by_hypothesis_id.get(hypothesis_id)
            if source_context is None:
                failed_validation += 1
                continue

            seen_hypothesis_ids.add(hypothesis_id)

            try:
                candidate = self._build_domain_candidate(payload, source_context, ingested_at)
                validate_demo_trade_candidate(candidate)
            except ValueError:
                failed_validation += 1
                continue

            self.storage.save_demo_trade_candidate(candidate)
            generated_candidates.append(candidate)

        return DemoTradeCandidateGenerationResult(
            research_candidates_loaded=len(research_candidates),
            generation_candidates=len(generation_candidate_evaluations),
            generated_candidates=tuple(generated_candidates),
            skipped_existing=skipped_existing,
            failed_validation=failed_validation,
        )
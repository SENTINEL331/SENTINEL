import json
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path

from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.experiment_result import (
    ExperimentMetrics,
    ExperimentResult,
    ExperimentResultStatus,
)
from research.demo_order_intent import DemoOrderIntent
from research.demo_order_intent import DemoOrderIntentStatus
from research.demo_broker_order_status import DemoBrokerOrderStatus
from research.demo_position_snapshot import DemoPositionSnapshot
from research.demo_trade_performance_snapshot import DemoTradePerformanceSnapshot
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus
from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.observation import Observation


class Storage:
    """
    Handles persistent storage for Sentinel AI.
    """

    def __init__(self):

        self.base = Path(__file__).parent / "memory"

    def _parse_timestamp(self, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                return value.replace(tzinfo=timezone.utc)

            return value

        if value:
            parsed = datetime.fromisoformat(value)

            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return parsed.replace(tzinfo=timezone.utc)

            return parsed

        return datetime.now(timezone.utc)

    def save_observations(
        self,
        symbol,
        observations,
    ):
        """
        Save observations for one symbol.
        """

        path = (
            self.base
            / "observations"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["observation_id"]
            for item in data
            if "observation_id" in item
        }

        for observation in observations:

            if observation.observation_id in existing_ids:
                continue

            existing_ids.add(observation.observation_id)

            data.append(
                {
                    "observation_id": observation.observation_id,
                    "symbol_id": observation.symbol_id,
                    "statement": observation.statement,
                    "evidence_refs": observation.evidence_refs,
                    "importance": observation.importance,
                    "effective_time": observation.effective_time,
                    "created_at": observation.created_at,
                    "research_cycle_id": observation.research_cycle_id,
                    "ai_call_id": observation.ai_call_id,
                    "schema_version": observation.schema_version,
                    "duplicate_of": observation.duplicate_of,
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_hypotheses(
        self,
        symbol,
        hypotheses,
    ):
        """
        Save hypotheses for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["hypothesis_id"]
            for item in data
            if "hypothesis_id" in item
        }

        for hypothesis in hypotheses:

            if hypothesis.hypothesis_id in existing_ids:
                continue

            existing_ids.add(hypothesis.hypothesis_id)

            data.append(
                {
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "symbol": hypothesis.symbol,
                    "title": hypothesis.title,
                    "description": hypothesis.description,
                    "status": hypothesis.status.value,
                    "confidence": hypothesis.confidence,
                    "source_observation_ids": list(
                        hypothesis.source_observation_ids
                    ),
                    "parent_hypothesis_id": hypothesis.parent_hypothesis_id,
                    "lineage_hypothesis_ids": list(
                        hypothesis.lineage_hypothesis_ids
                    ),
                    "source_revision_proposal_id": hypothesis.source_revision_proposal_id,
                    "experiment_refs": list(hypothesis.experiment_refs),
                    "created_at": hypothesis.created_at.isoformat(),
                    "updated_at": hypothesis.updated_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_experiment_requests(
        self,
        symbol,
        experiment_requests,
    ):
        """
        Save experiment requests for one symbol.
        """

        path = (
            self.base
            / "experiments"
            / "requests"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["experiment_request_id"]
            for item in data
            if "experiment_request_id" in item
        }

        for request in experiment_requests:

            if request.experiment_request_id in existing_ids:
                continue

            existing_ids.add(request.experiment_request_id)

            data.append(
                {
                    "experiment_request_id": request.experiment_request_id,
                    "hypothesis_id": request.hypothesis_id,
                    "hypothesis_version_id": request.hypothesis_version_id,
                    "symbol": request.symbol,
                    "title": request.title,
                    "objective": request.objective,
                    "test_type": request.test_type.value,
                    "entry_conditions": request.entry_conditions,
                    "machine_readable_entry_conditions": list(
                        request.machine_readable_entry_conditions
                    ),
                    "exit_conditions": request.exit_conditions,
                    "time_horizon": request.time_horizon,
                    "forward_horizon": request.forward_horizon,
                    "status": request.status.value,
                    "source_observation_ids": list(request.source_observation_ids),
                    "created_at": request.created_at.isoformat(),
                    "updated_at": request.updated_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_experiment_results(
        self,
        symbol,
        experiment_results,
    ):
        """
        Save experiment results for one symbol.
        """

        path = (
            self.base
            / "experiments"
            / "results"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["experiment_result_id"]
            for item in data
            if "experiment_result_id" in item
        }

        for result in experiment_results:

            if result.experiment_result_id in existing_ids:
                continue

            existing_ids.add(result.experiment_result_id)

            data.append(
                {
                    "experiment_result_id": result.experiment_result_id,
                    "experiment_request_id": result.experiment_request_id,
                    "hypothesis_id": result.hypothesis_id,
                    "symbol": result.symbol,
                    "test_type": result.test_type.value,
                    "status": result.status.value,
                    "started_at": result.started_at.isoformat(),
                    "completed_at": (
                        result.completed_at.isoformat()
                        if result.completed_at is not None
                        else None
                    ),
                    "metrics": {
                        "total_return": result.metrics.total_return,
                        "win_rate": result.metrics.win_rate,
                        "max_drawdown": result.metrics.max_drawdown,
                        "trade_count": result.metrics.trade_count,
                        "average_return": result.metrics.average_return,
                        "average_holding_period": result.metrics.average_holding_period,
                        "profit_factor": result.metrics.profit_factor,
                        "annualized_return": result.metrics.annualized_return,
                        "volatility": result.metrics.volatility,
                        "sharpe_ratio": result.metrics.sharpe_ratio,
                        "expectancy": result.metrics.expectancy,
                        "extra_metrics": dict(result.metrics.extra_metrics),
                    },
                    "diagnostics": dict(result.diagnostics),
                    "summary": result.summary,
                    "failure_reason": result.failure_reason,
                    "created_at": result.created_at.isoformat(),
                    "updated_at": result.updated_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_hypothesis_reviews(
        self,
        symbol,
        hypothesis_reviews,
    ):
        """
        Save hypothesis reviews for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "reviews"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["review_id"]
            for item in data
            if "review_id" in item
        }

        for review in hypothesis_reviews:

            if review.review_id in existing_ids:
                continue

            existing_ids.add(review.review_id)

            data.append(
                {
                    "review_id": review.review_id,
                    "hypothesis_id": review.hypothesis_id,
                    "symbol": review.symbol,
                    "recommendation": review.recommendation.value,
                    "rationale": review.rationale,
                    "confidence": review.confidence,
                    "created_at": review.created_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_hypothesis_revision_proposals(
        self,
        symbol,
        proposals,
    ):
        """
        Save hypothesis revision proposals for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "revision_proposals"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["proposal_id"]
            for item in data
            if "proposal_id" in item
        }

        for proposal in proposals:

            if proposal.proposal_id in existing_ids:
                continue

            existing_ids.add(proposal.proposal_id)

            data.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "symbol": proposal.symbol,
                    "parent_hypothesis_id": proposal.parent_hypothesis_id,
                    "source_review_id": proposal.source_review_id,
                    "lifecycle_action": proposal.lifecycle_action.value,
                    "proposal_type": proposal.proposal_type.value,
                    "proposed_title": proposal.proposed_title,
                    "proposed_description": proposal.proposed_description,
                    "rationale": proposal.rationale,
                    "confidence": proposal.confidence,
                    "created_at": proposal.created_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def save_demo_trade_candidate(
        self,
        candidate,
    ):
        """Append one demo trade candidate to the JSONL store."""

        path = self.base / "demo_trade_candidates.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "trade_candidate_id": candidate.trade_candidate_id,
                        "source_trade_candidate_id": candidate.source_trade_candidate_id,
                        "symbol": candidate.symbol,
                        "source_hypothesis_id": candidate.source_hypothesis_id,
                        "source_research_candidate_decision": candidate.source_research_candidate_decision,
                        "created_at": candidate.created_at.isoformat(),
                        "status": candidate.status.value,
                        "entry_logic": candidate.entry_logic,
                        "exit_logic": candidate.exit_logic,
                        "invalidation_logic": candidate.invalidation_logic,
                        "maximum_holding_period": candidate.maximum_holding_period,
                        "position_sizing_rule": candidate.position_sizing_rule,
                        "max_loss_per_trade": candidate.max_loss_per_trade,
                        "max_portfolio_exposure": candidate.max_portfolio_exposure,
                        "demo_only": candidate.demo_only,
                        "monitoring_frequency": candidate.monitoring_frequency,
                        "pause_conditions": list(candidate.pause_conditions),
                        "source_evidence_summary": dict(candidate.source_evidence_summary),
                        "source_review_action": candidate.source_review_action,
                        "source_review_confidence": candidate.source_review_confidence,
                        "risk_flags": list(candidate.risk_flags),
                        "gate_checked_at": (
                            candidate.gate_checked_at.isoformat()
                            if candidate.gate_checked_at is not None
                            else None
                        ),
                        "gate_decision": candidate.gate_decision,
                        "failed_checks": list(candidate.failed_checks),
                        "gate_rationale": candidate.gate_rationale,
                        "created_by": candidate.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_trade_candidates(
        self,
        symbol=None,
    ):
        """Load demo trade candidates, optionally filtered by symbol."""

        path = self.base / "demo_trade_candidates.jsonl"
        if not path.exists():
            return []

        candidates = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                item = json.loads(stripped)
                item_symbol = item.get("symbol", "")
                if symbol is not None and item_symbol != symbol:
                    continue

                candidates.append(
                    DemoTradeCandidate(
                        trade_candidate_id=item["trade_candidate_id"],
                        source_trade_candidate_id=item.get("source_trade_candidate_id"),
                        symbol=item_symbol,
                        source_hypothesis_id=item.get("source_hypothesis_id", ""),
                        source_research_candidate_decision=item.get(
                            "source_research_candidate_decision",
                            "",
                        ),
                        created_at=self._parse_timestamp(item.get("created_at", item.get("created"))),
                        status=DemoTradeCandidateStatus(
                            item.get("status", DemoTradeCandidateStatus.PROPOSED.value)
                        ),
                        entry_logic=item.get("entry_logic", ""),
                        exit_logic=item.get("exit_logic", ""),
                        invalidation_logic=item.get("invalidation_logic", ""),
                        maximum_holding_period=item.get("maximum_holding_period", ""),
                        position_sizing_rule=item.get("position_sizing_rule", ""),
                        max_loss_per_trade=item.get("max_loss_per_trade", 0.0),
                        max_portfolio_exposure=item.get("max_portfolio_exposure", 0.0),
                        demo_only=bool(item.get("demo_only", True)),
                        monitoring_frequency=item.get("monitoring_frequency", ""),
                        pause_conditions=tuple(item.get("pause_conditions", [])),
                        source_evidence_summary=item.get("source_evidence_summary", {}),
                        source_review_action=item.get("source_review_action"),
                        source_review_confidence=item.get("source_review_confidence"),
                        risk_flags=tuple(item.get("risk_flags", [])),
                        gate_checked_at=(
                            self._parse_timestamp(item.get("gate_checked_at"))
                            if item.get("gate_checked_at")
                            else None
                        ),
                        gate_decision=item.get("gate_decision"),
                        failed_checks=tuple(item.get("failed_checks", [])),
                        gate_rationale=item.get("gate_rationale"),
                        created_by=item.get("created_by", ""),
                    )
                )

        return candidates

    def save_demo_trade_queue_item(
        self,
        item,
    ):
        """Append one demo trade queue item to the JSONL store."""

        path = self.base / "demo_trade_queue.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "queue_item_id": item.queue_item_id,
                        "symbol": item.symbol,
                        "demo_trade_candidate_id": item.demo_trade_candidate_id,
                        "source_hypothesis_id": item.source_hypothesis_id,
                        "created_at": item.created_at.isoformat(),
                        "status": item.status.value,
                        "demo_only": item.demo_only,
                        "queue_reason": item.queue_reason,
                        "risk_summary": item.risk_summary,
                        "requested_action": item.requested_action,
                        "created_by": item.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_trade_queue_items(
        self,
        symbol=None,
    ):
        """Load demo trade queue items, optionally filtered by symbol."""

        path = self.base / "demo_trade_queue.jsonl"
        if not path.exists():
            return []

        items = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_item = json.loads(stripped)
                item_symbol = raw_item.get("symbol", "")
                if symbol is not None and item_symbol != symbol:
                    continue

                items.append(
                    DemoTradeQueueItem(
                        queue_item_id=raw_item["queue_item_id"],
                        symbol=item_symbol,
                        demo_trade_candidate_id=raw_item.get("demo_trade_candidate_id", ""),
                        source_hypothesis_id=raw_item.get("source_hypothesis_id", ""),
                        created_at=self._parse_timestamp(
                            raw_item.get("created_at", raw_item.get("created"))
                        ),
                        status=DemoTradeQueueStatus(
                            raw_item.get("status", DemoTradeQueueStatus.QUEUED.value)
                        ),
                        demo_only=bool(raw_item.get("demo_only", True)),
                        queue_reason=raw_item.get("queue_reason", ""),
                        risk_summary=raw_item.get("risk_summary", ""),
                        requested_action=raw_item.get("requested_action", "prepare_demo_order"),
                        created_by=raw_item.get("created_by", ""),
                    )
                )

        return items

    def save_demo_order_intent(
        self,
        intent,
    ):
        """Append one demo order intent to the JSONL store."""

        path = self.base / "demo_order_intents.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "order_intent_id": intent.order_intent_id,
                        "symbol": intent.symbol,
                        "queue_item_id": intent.queue_item_id,
                        "demo_trade_candidate_id": intent.demo_trade_candidate_id,
                        "source_hypothesis_id": intent.source_hypothesis_id,
                        "created_at": intent.created_at.isoformat(),
                        "status": getattr(intent.status, "value", intent.status),
                        "demo_only": intent.demo_only,
                        "side": intent.side,
                        "order_type": intent.order_type,
                        "time_in_force": intent.time_in_force,
                        "notional": intent.notional,
                        "quantity": intent.quantity,
                        "limit_price": intent.limit_price,
                        "stop_price": intent.stop_price,
                        "max_loss_per_trade": intent.max_loss_per_trade,
                        "max_portfolio_exposure": intent.max_portfolio_exposure,
                        "intent_reason": intent.intent_reason,
                        "created_by": intent.created_by,
                    }
                )
            )
            f.write("\n")

    def save_demo_broker_order_record(
        self,
        record,
    ):
        """Append one broker-order record for a submitted demo order intent."""

        path = self.base / "demo_broker_order_records.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "broker_order_id": record.broker_order_id,
                        "order_intent_id": record.order_intent_id,
                        "symbol": record.symbol,
                        "queue_item_id": record.queue_item_id,
                        "demo_trade_candidate_id": record.demo_trade_candidate_id,
                        "source_hypothesis_id": record.source_hypothesis_id,
                        "created_at": record.created_at.isoformat(),
                        "status": getattr(record.status, "value", record.status),
                        "demo_only": record.demo_only,
                        "side": record.side,
                        "order_type": record.order_type,
                        "time_in_force": record.time_in_force,
                        "notional": record.notional,
                        "quantity": record.quantity,
                        "limit_price": record.limit_price,
                        "stop_price": record.stop_price,
                        "broker": record.broker,
                        "mode": record.mode,
                        "api_response_status": record.api_response_status,
                        "rationale": record.rationale,
                        "created_by": record.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_broker_order_records(
        self,
        symbol=None,
    ):
        """Load demo broker order records, optionally filtered by symbol."""

        path = self.base / "demo_broker_order_records.jsonl"
        if not path.exists():
            return []

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_record = json.loads(stripped)
                record_symbol = raw_record.get("symbol", "")
                if symbol is not None and record_symbol != symbol:
                    continue

                records.append(
                    type(
                        "DemoBrokerOrderRecord",
                        (),
                        {
                            "broker_order_id": raw_record.get("broker_order_id", ""),
                            "order_intent_id": raw_record.get("order_intent_id", ""),
                            "symbol": record_symbol,
                            "queue_item_id": raw_record.get("queue_item_id", ""),
                            "demo_trade_candidate_id": raw_record.get("demo_trade_candidate_id", ""),
                            "source_hypothesis_id": raw_record.get("source_hypothesis_id", ""),
                            "created_at": self._parse_timestamp(raw_record.get("created_at")),
                            "status": raw_record.get("status", "submitted"),
                            "demo_only": bool(raw_record.get("demo_only", True)),
                            "side": raw_record.get("side", "buy"),
                            "order_type": raw_record.get("order_type", "market"),
                            "time_in_force": raw_record.get("time_in_force", "day"),
                            "notional": raw_record.get("notional"),
                            "quantity": raw_record.get("quantity"),
                            "limit_price": raw_record.get("limit_price"),
                            "stop_price": raw_record.get("stop_price"),
                            "broker": raw_record.get("broker", "alpaca"),
                            "mode": raw_record.get("mode", "paper"),
                            "api_response_status": raw_record.get("api_response_status", "accepted"),
                            "rationale": raw_record.get("rationale", ""),
                            "created_by": raw_record.get("created_by", "sentinel"),
                        },
                    )()
                )

        return records

    def save_demo_broker_order_status(
        self,
        status_record,
    ):
        """Append one demo broker order status snapshot to the JSONL store."""

        path = self.base / "demo_broker_order_statuses.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "broker_order_status_id": status_record.broker_order_status_id,
                        "broker_order_record_id": status_record.broker_order_record_id,
                        "order_intent_id": status_record.order_intent_id,
                        "symbol": status_record.symbol,
                        "broker": status_record.broker,
                        "broker_mode": status_record.broker_mode,
                        "broker_order_id": status_record.broker_order_id,
                        "synced_at": status_record.synced_at.isoformat(),
                        "status": status_record.status,
                        "raw_status": status_record.raw_status,
                        "filled_qty": status_record.filled_qty,
                        "filled_avg_price": status_record.filled_avg_price,
                        "submitted_notional": status_record.submitted_notional,
                        "submitted_quantity": status_record.submitted_quantity,
                        "demo_only": status_record.demo_only,
                        "created_by": status_record.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_broker_order_statuses(
        self,
        symbol=None,
    ):
        """Load demo broker order status snapshots, optionally filtered by symbol."""

        path = self.base / "demo_broker_order_statuses.jsonl"
        if not path.exists():
            return []

        statuses = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_status = json.loads(stripped)
                status_symbol = raw_status.get("symbol", "")
                if symbol is not None and status_symbol != symbol:
                    continue

                statuses.append(
                    DemoBrokerOrderStatus(
                        broker_order_status_id=raw_status.get("broker_order_status_id", ""),
                        broker_order_record_id=raw_status.get("broker_order_record_id", ""),
                        order_intent_id=raw_status.get("order_intent_id", ""),
                        symbol=status_symbol,
                        broker=raw_status.get("broker", "alpaca"),
                        broker_mode=raw_status.get("broker_mode", "paper"),
                        broker_order_id=raw_status.get("broker_order_id", ""),
                        synced_at=self._parse_timestamp(raw_status.get("synced_at")),
                        status=raw_status.get("status", "n/a"),
                        raw_status=raw_status.get("raw_status", "n/a"),
                        filled_qty=raw_status.get("filled_qty"),
                        filled_avg_price=raw_status.get("filled_avg_price"),
                        submitted_notional=raw_status.get("submitted_notional"),
                        submitted_quantity=raw_status.get("submitted_quantity"),
                        demo_only=bool(raw_status.get("demo_only", True)),
                        created_by=raw_status.get("created_by", "sentinel"),
                    )
                )

        return statuses

    def save_demo_position_snapshot(
        self,
        snapshot,
    ):
        """Append one demo position snapshot to the JSONL store."""

        path = self.base / "demo_position_snapshots.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "position_snapshot_id": snapshot.position_snapshot_id,
                        "symbol": snapshot.symbol,
                        "broker": snapshot.broker,
                        "broker_mode": snapshot.broker_mode,
                        "synced_at": snapshot.synced_at.isoformat(),
                        "status": snapshot.status,
                        "qty": snapshot.qty,
                        "side": snapshot.side,
                        "market_value": snapshot.market_value,
                        "cost_basis": snapshot.cost_basis,
                        "avg_entry_price": snapshot.avg_entry_price,
                        "current_price": snapshot.current_price,
                        "unrealized_pl": snapshot.unrealized_pl,
                        "unrealized_plpc": snapshot.unrealized_plpc,
                        "asset_id": snapshot.asset_id,
                        "exchange": snapshot.exchange,
                        "demo_only": snapshot.demo_only,
                        "created_by": snapshot.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_position_snapshots(
        self,
        symbol=None,
    ):
        """Load demo position snapshots, optionally filtered by symbol."""

        path = self.base / "demo_position_snapshots.jsonl"
        if not path.exists():
            return []

        snapshots = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_snapshot = json.loads(stripped)
                snapshot_symbol = raw_snapshot.get("symbol", "")
                if symbol is not None and snapshot_symbol != symbol:
                    continue

                snapshots.append(
                    DemoPositionSnapshot(
                        position_snapshot_id=raw_snapshot.get("position_snapshot_id", ""),
                        symbol=snapshot_symbol,
                        broker=raw_snapshot.get("broker", "alpaca"),
                        broker_mode=raw_snapshot.get("broker_mode", "paper"),
                        synced_at=self._parse_timestamp(raw_snapshot.get("synced_at")),
                        status=raw_snapshot.get("status", "failed"),
                        qty=raw_snapshot.get("qty"),
                        side=raw_snapshot.get("side", "none"),
                        market_value=raw_snapshot.get("market_value"),
                        cost_basis=raw_snapshot.get("cost_basis"),
                        avg_entry_price=raw_snapshot.get("avg_entry_price"),
                        current_price=raw_snapshot.get("current_price"),
                        unrealized_pl=raw_snapshot.get("unrealized_pl"),
                        unrealized_plpc=raw_snapshot.get("unrealized_plpc"),
                        asset_id=raw_snapshot.get("asset_id", ""),
                        exchange=raw_snapshot.get("exchange", ""),
                        demo_only=bool(raw_snapshot.get("demo_only", True)),
                        created_by=raw_snapshot.get("created_by", "sentinel"),
                    )
                )

        return snapshots

    def save_demo_trade_performance_snapshot(
        self,
        snapshot,
    ):
        """Append one demo trade performance snapshot to the JSONL store."""

        path = self.base / "demo_trade_performance_snapshots.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "performance_snapshot_id": snapshot.performance_snapshot_id,
                        "symbol": snapshot.symbol,
                        "order_intent_id": snapshot.order_intent_id,
                        "broker_order_id": snapshot.broker_order_id,
                        "broker_order_record_id": snapshot.broker_order_record_id,
                        "queue_item_id": snapshot.queue_item_id,
                        "demo_trade_candidate_id": snapshot.demo_trade_candidate_id,
                        "source_hypothesis_id": snapshot.source_hypothesis_id,
                        "snapshot_at": snapshot.snapshot_at.isoformat(),
                        "status": snapshot.status,
                        "side": snapshot.side,
                        "filled_qty": snapshot.filled_qty,
                        "filled_avg_price": snapshot.filled_avg_price,
                        "current_price": snapshot.current_price,
                        "entry_value": snapshot.entry_value,
                        "current_value": snapshot.current_value,
                        "unrealized_pl": snapshot.unrealized_pl,
                        "unrealized_plpc": snapshot.unrealized_plpc,
                        "position_snapshot_id": snapshot.position_snapshot_id,
                        "demo_only": snapshot.demo_only,
                        "created_by": snapshot.created_by,
                    }
                )
            )
            f.write("\n")

    def load_demo_trade_performance_snapshots(
        self,
        symbol=None,
    ):
        """Load demo trade performance snapshots, optionally filtered by symbol."""

        path = self.base / "demo_trade_performance_snapshots.jsonl"
        if not path.exists():
            return []

        snapshots = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_snapshot = json.loads(stripped)
                snapshot_symbol = raw_snapshot.get("symbol", "")
                if symbol is not None and snapshot_symbol != symbol:
                    continue

                snapshots.append(
                    DemoTradePerformanceSnapshot(
                        performance_snapshot_id=raw_snapshot.get("performance_snapshot_id", ""),
                        symbol=snapshot_symbol,
                        order_intent_id=raw_snapshot.get("order_intent_id", ""),
                        broker_order_id=raw_snapshot.get("broker_order_id", ""),
                        broker_order_record_id=raw_snapshot.get("broker_order_record_id", ""),
                        queue_item_id=raw_snapshot.get("queue_item_id", ""),
                        demo_trade_candidate_id=raw_snapshot.get("demo_trade_candidate_id", ""),
                        source_hypothesis_id=raw_snapshot.get("source_hypothesis_id", ""),
                        snapshot_at=self._parse_timestamp(raw_snapshot.get("snapshot_at")),
                        status=raw_snapshot.get("status", "failed"),
                        side=raw_snapshot.get("side", "none"),
                        filled_qty=raw_snapshot.get("filled_qty"),
                        filled_avg_price=raw_snapshot.get("filled_avg_price"),
                        current_price=raw_snapshot.get("current_price"),
                        entry_value=raw_snapshot.get("entry_value"),
                        current_value=raw_snapshot.get("current_value"),
                        unrealized_pl=raw_snapshot.get("unrealized_pl"),
                        unrealized_plpc=raw_snapshot.get("unrealized_plpc"),
                        position_snapshot_id=raw_snapshot.get("position_snapshot_id", ""),
                        demo_only=bool(raw_snapshot.get("demo_only", True)),
                        created_by=raw_snapshot.get("created_by", "sentinel"),
                    )
                )

        return snapshots

    def load_demo_order_intents(
        self,
        symbol=None,
    ):
        """Load demo order intents, optionally filtered by symbol."""

        path = self.base / "demo_order_intents.jsonl"
        if not path.exists():
            return []

        intents = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                raw_intent = json.loads(stripped)
                item_symbol = raw_intent.get("symbol", "")
                if symbol is not None and item_symbol != symbol:
                    continue

                intents.append(
                    DemoOrderIntent(
                        order_intent_id=raw_intent["order_intent_id"],
                        symbol=item_symbol,
                        queue_item_id=raw_intent.get("queue_item_id", ""),
                        demo_trade_candidate_id=raw_intent.get("demo_trade_candidate_id", ""),
                        source_hypothesis_id=raw_intent.get("source_hypothesis_id", ""),
                        created_at=self._parse_timestamp(raw_intent.get("created_at")),
                        status=DemoOrderIntentStatus(
                            raw_intent.get("status", DemoOrderIntentStatus.PREPARED.value)
                        ),
                        demo_only=bool(raw_intent.get("demo_only", True)),
                        side=raw_intent.get("side", "buy"),
                        order_type=raw_intent.get("order_type", "market"),
                        time_in_force=raw_intent.get("time_in_force", "day"),
                        notional=raw_intent.get("notional"),
                        quantity=raw_intent.get("quantity"),
                        limit_price=raw_intent.get("limit_price"),
                        stop_price=raw_intent.get("stop_price"),
                        max_loss_per_trade=raw_intent.get("max_loss_per_trade", 0.0),
                        max_portfolio_exposure=raw_intent.get("max_portfolio_exposure", 0.0),
                        intent_reason=raw_intent.get("intent_reason", ""),
                        created_by=raw_intent.get("created_by", ""),
                    )
                )

        return intents

    def save_hypothesis_revision_applications(
        self,
        symbol,
        applications,
    ):
        """
        Save hypothesis revision application events for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "revision_applications"
            / f"{symbol}.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = []

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        existing_ids = {
            item["application_id"]
            for item in data
            if "application_id" in item
        }

        for application in applications:

            if application.application_id in existing_ids:
                continue

            existing_ids.add(application.application_id)

            data.append(
                {
                    "application_id": application.application_id,
                    "proposal_id": application.proposal_id,
                    "symbol": application.symbol,
                    "parent_hypothesis_id": application.parent_hypothesis_id,
                    "status": application.status.value,
                    "apply_mode": application.apply_mode,
                    "child_hypothesis_id": application.child_hypothesis_id,
                    "message": application.message,
                    "created_at": application.created_at.isoformat(),
                }
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def load_observations(
        self,
        symbol,
    ):
        """
        Load observations for one symbol.
        """

        path = (
            self.base
            / "observations"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        observations = []

        for item in data:

            symbol_id = item.get("symbol_id", item.get("symbol", symbol))

            created_at = item.get("created_at", item.get("created", ""))

            effective_time = item.get("effective_time", created_at)

            statement = item["statement"]

            observation_id = item.get("observation_id")

            if not observation_id:
                digest = sha256(
                    f"{symbol_id}|{created_at}|{statement}".encode("utf-8")
                ).hexdigest()[:12]
                observation_id = f"legacy-{symbol_id}-{digest}"

            observations.append(
                Observation(
                    observation_id=observation_id,
                    symbol_id=symbol_id,
                    statement=statement,
                    evidence_refs=item.get("evidence_refs", []),
                    importance=item["importance"],
                    effective_time=effective_time,
                    created_at=created_at,
                    research_cycle_id=item.get("research_cycle_id", "legacy"),
                    ai_call_id=item.get("ai_call_id", "legacy"),
                    schema_version=item.get("schema_version", "1.0"),
                    duplicate_of=item.get("duplicate_of"),
                )
            )

        return observations

    def load_hypotheses(
        self,
        symbol,
    ):
        """
        Load hypotheses for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        hypotheses = []

        for item in data:

            status_value = item.get("status", HypothesisStatus.PROPOSED.value)

            hypotheses.append(
                Hypothesis(
                    hypothesis_id=item["hypothesis_id"],
                    symbol=item.get("symbol", symbol),
                    title=item["title"],
                    description=item["description"],
                    status=HypothesisStatus(status_value),
                    confidence=item.get("confidence", 0.0),
                    source_observation_ids=tuple(
                        item.get("source_observation_ids", item.get("observations", []))
                    ),
                    parent_hypothesis_id=item.get("parent_hypothesis_id"),
                    lineage_hypothesis_ids=tuple(
                        item.get("lineage_hypothesis_ids", [])
                    ),
                    source_revision_proposal_id=item.get("source_revision_proposal_id"),
                    experiment_refs=tuple(
                        item.get("experiment_refs", item.get("experiments", []))
                    ),
                    created_at=self._parse_timestamp(
                        item.get("created_at", item.get("created"))
                    ),
                    updated_at=self._parse_timestamp(
                        item.get("updated_at", item.get("updated"))
                    ),
                )
            )

        return hypotheses

    def load_experiment_requests(
        self,
        symbol,
    ):
        """
        Load experiment requests for one symbol.
        """

        path = (
            self.base
            / "experiments"
            / "requests"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        experiment_requests = []

        for item in data:

            experiment_requests.append(
                ExperimentRequest(
                    experiment_request_id=item["experiment_request_id"],
                    hypothesis_id=item["hypothesis_id"],
                    hypothesis_version_id=item.get(
                        "hypothesis_version_id",
                        item.get("hypothesis_version", ""),
                    ),
                    symbol=item.get("symbol", symbol),
                    title=item["title"],
                    objective=item["objective"],
                    test_type=ExperimentTestType(item["test_type"]),
                    entry_conditions=item["entry_conditions"],
                    machine_readable_entry_conditions=tuple(
                        item.get("machine_readable_entry_conditions", [])
                    ),
                    exit_conditions=item["exit_conditions"],
                    time_horizon=item["time_horizon"],
                    forward_horizon=item.get("forward_horizon"),
                    status=ExperimentRequestStatus(
                        item.get("status", ExperimentRequestStatus.PROPOSED.value)
                    ),
                    source_observation_ids=tuple(item.get("source_observation_ids", [])),
                    created_at=self._parse_timestamp(
                        item.get("created_at", item.get("created"))
                    ),
                    updated_at=self._parse_timestamp(
                        item.get("updated_at", item.get("updated"))
                    ),
                )
            )

        return experiment_requests

    def load_experiment_results(
        self,
        symbol,
    ):
        """
        Load experiment results for one symbol.
        """

        path = (
            self.base
            / "experiments"
            / "results"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        experiment_results = []

        for item in data:
            metrics_item = item.get("metrics", {})
            extra_metrics = {}
            diagnostics_item = item.get("diagnostics", {})

            if isinstance(metrics_item, dict):
                extra_metrics = metrics_item.get("extra_metrics", {})

            if not isinstance(diagnostics_item, dict):
                diagnostics_item = {}

            experiment_results.append(
                ExperimentResult(
                    experiment_result_id=item["experiment_result_id"],
                    experiment_request_id=item["experiment_request_id"],
                    hypothesis_id=item["hypothesis_id"],
                    symbol=item.get("symbol", symbol),
                    test_type=ExperimentTestType(item["test_type"]),
                    status=ExperimentResultStatus(
                        item.get("status", ExperimentResultStatus.RUNNING.value)
                    ),
                    started_at=self._parse_timestamp(item.get("started_at")),
                    completed_at=(
                        self._parse_timestamp(item.get("completed_at"))
                        if item.get("completed_at")
                        else None
                    ),
                    metrics=ExperimentMetrics(
                        total_return=metrics_item.get("total_return"),
                        win_rate=metrics_item.get("win_rate"),
                        max_drawdown=metrics_item.get("max_drawdown"),
                        trade_count=metrics_item.get("trade_count"),
                        average_return=metrics_item.get("average_return"),
                        average_holding_period=metrics_item.get("average_holding_period"),
                        profit_factor=metrics_item.get("profit_factor"),
                        annualized_return=metrics_item.get("annualized_return"),
                        volatility=metrics_item.get("volatility"),
                        sharpe_ratio=metrics_item.get("sharpe_ratio"),
                        expectancy=metrics_item.get("expectancy"),
                        extra_metrics=extra_metrics,
                    ),
                    diagnostics=diagnostics_item,
                    summary=item.get("summary", ""),
                    failure_reason=item.get("failure_reason"),
                    created_at=self._parse_timestamp(
                        item.get("created_at", item.get("created"))
                    ),
                    updated_at=self._parse_timestamp(
                        item.get("updated_at", item.get("updated"))
                    ),
                )
            )

        return experiment_results

    def load_hypothesis_reviews(
        self,
        symbol,
    ):
        """
        Load hypothesis reviews for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "reviews"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        hypothesis_reviews = []

        for item in data:
            hypothesis_reviews.append(
                HypothesisReview(
                    review_id=item["review_id"],
                    hypothesis_id=item["hypothesis_id"],
                    symbol=item.get("symbol", symbol),
                    recommendation=HypothesisReviewRecommendation(item["recommendation"]),
                    rationale=item["rationale"],
                    confidence=item["confidence"],
                    created_at=self._parse_timestamp(item.get("created_at", item.get("created"))),
                )
            )

        return hypothesis_reviews

    def load_hypothesis_revision_proposals(
        self,
        symbol,
    ):
        """
        Load hypothesis revision proposals for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "revision_proposals"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        proposals = []

        for item in data:
            proposals.append(
                HypothesisRevisionProposal(
                    proposal_id=item["proposal_id"],
                    symbol=item.get("symbol", symbol),
                    parent_hypothesis_id=item["parent_hypothesis_id"],
                    source_review_id=item.get("source_review_id"),
                    lifecycle_action=HypothesisLifecycleAction(item["lifecycle_action"]),
                    proposal_type=HypothesisRevisionProposalType(item["proposal_type"]),
                    proposed_title=item.get("proposed_title", ""),
                    proposed_description=item.get("proposed_description", ""),
                    rationale=item["rationale"],
                    confidence=item["confidence"],
                    created_at=self._parse_timestamp(item.get("created_at", item.get("created"))),
                )
            )

        return proposals

    def load_hypothesis_revision_applications(
        self,
        symbol,
    ):
        """
        Load hypothesis revision application events for one symbol.
        """

        path = (
            self.base
            / "hypotheses"
            / "revision_applications"
            / f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        applications = []

        for item in data:
            applications.append(
                HypothesisRevisionApplication(
                    application_id=item["application_id"],
                    proposal_id=item["proposal_id"],
                    symbol=item.get("symbol", symbol),
                    parent_hypothesis_id=item["parent_hypothesis_id"],
                    status=HypothesisRevisionApplicationStatus(item["status"]),
                    apply_mode=bool(item.get("apply_mode", False)),
                    child_hypothesis_id=item.get("child_hypothesis_id"),
                    message=item.get("message", ""),
                    created_at=self._parse_timestamp(item.get("created_at", item.get("created"))),
                )
            )

        return applications
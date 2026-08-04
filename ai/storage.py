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
from research.hypothesis import Hypothesis, HypothesisStatus
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

            if isinstance(metrics_item, dict):
                extra_metrics = metrics_item.get("extra_metrics", {})

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
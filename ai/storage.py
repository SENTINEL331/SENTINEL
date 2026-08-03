import json
from hashlib import sha256
from pathlib import Path

from research.observation import Observation


class Storage:
    """
    Handles persistent storage for Sentinel AI.
    """

    def __init__(self):

        self.base = Path(__file__).parent / "memory"

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
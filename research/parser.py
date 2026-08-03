import json
from hashlib import sha256

from datetime import datetime, timezone

from research.observation import Observation


def parse_observations(
    snapshot,
    response,
    research_cycle_id="unknown-cycle",
    ai_call_id="unknown-ai-call",
    schema_version="1.0",
):
    """
    Convert an AI observation response into
    Observation objects.
    """

    data = json.loads(response)

    observations = []

    snapshot_ref = f"snapshot:{snapshot.symbol}:{snapshot.date}"

    effective_time = str(snapshot.date)

    created_at = datetime.now(timezone.utc).isoformat()

    for item in data["observations"]:

        statement = item["statement"]

        digest = sha256(
            f"{snapshot.symbol}|{effective_time}|{statement}".encode("utf-8")
        ).hexdigest()[:12]

        observation = Observation(

            observation_id=f"obs-{snapshot.symbol}-{digest}",

            symbol_id=snapshot.symbol,

            statement=statement,

            evidence_refs=[snapshot_ref],

            importance=item["importance"],

            effective_time=effective_time,

            created_at=created_at,

            research_cycle_id=research_cycle_id,

            ai_call_id=ai_call_id,

            schema_version=schema_version,

        )

        observations.append(observation)

    return observations
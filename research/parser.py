import json

from datetime import date

from research.record import ResearchRecord


def parse_observations(
    symbol,
    response,
):
    """
    Convert an AI observation response into
    ResearchRecord objects.
    """

    data = json.loads(response)

    records = []

    for observation in data["observations"]:

        record = ResearchRecord(

            symbol=symbol,

            category="Observation",

            summary=observation["statement"],

            created=str(date.today()),

        )

        records.append(record)

    return records
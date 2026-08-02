import json

from datetime import date

from research.observation import Observation


def parse_observations(
    symbol,
    response,
):
    """
    Convert an AI observation response into
    Observation objects.
    """

    data = json.loads(response)

    observations = []

    for item in data["observations"]:

        observation = Observation(

            symbol=symbol,

            statement=item["statement"],

            importance=item["importance"],

            created=str(date.today()),

        )

        observations.append(observation)

    return observations
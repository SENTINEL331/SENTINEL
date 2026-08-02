import json
from pathlib import Path


class Storage:
    """
    Handles persistent storage for Sentinel AI.
    """

    def __init__(self):

        self.base = (
            Path(__file__).parent /
            "memory"
        )

    def save_observations(
        self,
        symbol,
        records,
    ):
        """
        Save observations for one symbol.
        """

        path = (
            self.base /
            "observations" /
            f"{symbol}.json"
        )

        data = []

        for record in records:

            data.append(
                {
                    "symbol": record.symbol,
                    "category": record.category,
                    "summary": record.summary,
                    "created": record.created,
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

        path = (
            self.base /
            "observations" /
            f"{symbol}.json"
        )

        if not path.exists():

            return []

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)
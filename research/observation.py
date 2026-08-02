from dataclasses import dataclass


@dataclass
class Observation:
    """
    Represents one objective observation
    produced by the AI researcher.
    """

    symbol: str

    statement: str

    importance: int

    created: str
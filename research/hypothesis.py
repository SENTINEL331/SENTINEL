from dataclasses import dataclass, field

from typing import List


@dataclass
class Hypothesis:
    """
    Represents one trading hypothesis generated
    by the AI researcher.
    """

    #
    # Identity
    #

    id: str

    symbol: str

    #
    # Description
    #

    title: str

    description: str

    #
    # Research
    #

    observations: List[str] = field(default_factory=list)

    #
    # Status
    #

    status: str = "NEW"

    confidence: float = 0.0

    #
    # Experiment History
    #

    experiments: List[str] = field(default_factory=list)

    #
    # Dates
    #

    created: str = ""

    updated: str = ""
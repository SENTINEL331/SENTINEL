from research.observation import Observation


class ResearchMemory:
    """Stores accepted observations for the active run."""

    def __init__(self):

        self.observations: list[Observation] = []

    def add(
        self,
        observation,
    ):
        """Add an observation."""

        self.observations.append(observation)

    def get_all(self):
        """Return every observation."""

        return self.observations

    def get_symbol(
        self,
        symbol,
    ):
        """Return observations for one symbol."""

        return [

            observation

            for observation in self.observations

            if observation.symbol_id == symbol

        ]

    def count(self):
        """Return total number of observations."""

        return len(self.observations)
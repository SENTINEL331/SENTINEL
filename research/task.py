class Task:
    """Represents work requested by the AI."""

    def __init__(
        self,
        action,
        symbol=None,
        parameters=None,
    ):

        self.action = action

        self.symbol = symbol

        self.parameters = parameters or {}
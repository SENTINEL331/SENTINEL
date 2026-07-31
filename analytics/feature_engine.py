from analytics.feature_registry import FEATURE_REGISTRY


class FeatureEngine:
    """Calculates market features."""

    def __init__(self):

        self.features = []

    def add_feature(
        self,
        name,
        **parameters,
    ):
        """Register a feature to calculate."""

        self.features.append(
            {
                "name": name,
                "parameters": parameters,
            }
        )

    def calculate(
        self,
        data,
    ):
        """Calculate all registered features."""

        for feature in self.features:

            name = feature["name"]

            parameters = feature["parameters"]

            calculate = FEATURE_REGISTRY[name]

            data = calculate(
                data,
                **parameters,
            )

        return data
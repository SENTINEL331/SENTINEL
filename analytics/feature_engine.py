from analytics.feature_registry import FEATURE_REGISTRY


class FeatureEngine:
    """Creates market features from historical data."""

    def __init__(self):
        self.features = []

    def add_feature(self, name, **parameters):
        """Register a feature for calculation."""

        self.features.append(
            {
                "name": name.upper(),
                "parameters": parameters,
            }
        )

    def calculate(self, data):
        """Calculate all registered features."""

        data = data.copy()

        for feature in self.features:

            name = feature["name"]
            params = feature["parameters"]

            calculator = FEATURE_REGISTRY.get(name)

            if calculator is None:
                raise ValueError(f"Unknown feature: {name}")

            data = calculator(data, **params)

        return data
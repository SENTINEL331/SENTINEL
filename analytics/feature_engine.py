from analytics.feature_registry import FeatureRegistry


class FeatureEngine:
    """Calculates configured market features."""

    def __init__(self):
        self.features = []
        self.registry = FeatureRegistry()

    def add_feature(
        self,
        name,
        **parameters,
    ):
        """Register a feature for calculation."""

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

            if not self.registry.exists(name):
                raise ValueError(f"Unknown feature: {name}")

            feature_definition = self.registry.get(name)

            calculate = feature_definition["function"]

            data = calculate(
                data,
                **parameters,
            )

        return data
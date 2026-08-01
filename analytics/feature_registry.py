from os import name

from analytics.features import sma
from analytics.features import ema
from analytics.features import rsi
from analytics.features import atr
from analytics.features import bollinger

FEATURE_REGISTRY = {

    "SMA": {

        "function": sma.calculate,

        "category": "Trend",

        "description": "Simple Moving Average",

        "inputs": [
            "Close",
        ],

        "outputs": [
            "SMA_20",
        ],

        "unit": "Price",

        "source": "Calculated",
    },

    "EMA": {

        "function": ema.calculate,

        "category": "Trend",

        "description": "Exponential Moving Average",

        "inputs": [
            "Close",
        ],

        "outputs": [
            "EMA_20",
        ],

        "unit": "Price",

        "source": "Calculated",
    },

    "RSI": {

        "function": rsi.calculate,

        "category": "Momentum",

        "description": "Relative Strength Index",

        "inputs": [
            "Close",
        ],

        "outputs": [
            "RSI_14",
        ],

        "unit": "Index",

        "source": "Calculated",
    },

    "ATR": {

        "function": atr.calculate,

        "category": "Volatility",

        "description": "Average True Range",

        "inputs": [
            "High",
            "Low",
            "Close",
        ],

        "outputs": [
            "ATR_14",
        ],

        "unit": "Price",

        "source": "Calculated",
    },

    "BOLLINGER": {

        "function": bollinger.calculate,

        "category": "Volatility",

        "description": "Bollinger Bands",

        "inputs": [
            "Close",
        ],

        "outputs": [
            "BB_MIDDLE",
            "BB_UPPER",
            "BB_LOWER",
        ],


        "unit": "Price",

        "source": "Calculated",
    },

}


class FeatureRegistry:
    """Provides access to Sentinel's registered market measurements."""

    def get(self, name):
        """Return a single feature definition."""
        return FEATURE_REGISTRY[name]

    def list_features(self):
        """Return all registered feature names."""
        return list(FEATURE_REGISTRY.keys())

    def list_categories(self):
        """Return all unique feature categories."""
        return sorted({
            feature["category"]
            for feature in FEATURE_REGISTRY.values()
        })

    def list_by_category(self, category):
        """Return all features belonging to a category."""
        return {
            name: feature
            for name, feature in FEATURE_REGISTRY.items()
            if feature["category"] == category
        }

    def describe(self):
        """Display all registered features."""

        for name, feature in FEATURE_REGISTRY.items():

            print(f"\n{name}")

            print(f"  Category    : {feature['category']}")

            print(f"  Description : {feature['description']}")

            print(f"  Inputs      : {', '.join(feature['inputs'])}")

            print(f"  Outputs     : {', '.join(feature['outputs'])}")

            print(f"  Unit        : {feature['unit']}")

            print(f"  Source      : {feature['source']}")

    def list_outputs(self):
        """Return all output columns produced by registered features."""

        outputs = []

        for feature in FEATURE_REGISTRY.values():
            outputs.extend(feature["outputs"])

        return outputs

    def list_inputs(self):
        """Return all unique required input columns."""

        inputs = set()

        for feature in FEATURE_REGISTRY.values():
            inputs.update(feature["inputs"])

        return sorted(inputs)

    def exists(self, name):
        """Return True if a feature exists."""
        return name in FEATURE_REGISTRY
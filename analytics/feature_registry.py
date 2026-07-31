from analytics.features import sma

FEATURE_REGISTRY = {
    "SMA": sma.calculate,
}
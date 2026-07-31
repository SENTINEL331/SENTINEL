from analytics.features import sma
from analytics.features import ema

FEATURE_REGISTRY = {
    "SMA": sma.calculate,
    "EMA": ema.calculate,
}
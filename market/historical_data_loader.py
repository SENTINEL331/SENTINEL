"""Deterministic loader for historical backtest data."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from analytics.feature_registry import FeatureRegistry
from analytics.feature_store import FeatureStore
from config.settings import DEFAULT_INTERVAL, FEATURE_SET
from market.history_manager import HistoryManager


_REQUIRED_COLUMNS = (
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
)


def _missing_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> list[str]:
    return [column for column in required_columns if column not in data.columns]


def _normalize_date_index(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()
    normalized["Date"] = pd.to_datetime(normalized["Date"])
    normalized = normalized.set_index("Date")
    normalized.index.name = "Date"
    return normalized.sort_index()


class HistoricalDataLoader:
    """Load historical market data and available features for backtesting."""

    def __init__(
        self,
        history_manager: HistoryManager | None = None,
        feature_store: FeatureStore | None = None,
        feature_registry: FeatureRegistry | None = None,
    ) -> None:
        self._history_manager = history_manager or HistoryManager()
        self._feature_store = feature_store or FeatureStore()
        self._feature_registry = feature_registry or FeatureRegistry()

    def _prepare_required_features(self, data: pd.DataFrame) -> pd.DataFrame:
        prepared = data.copy()

        for feature_definition in FEATURE_SET:
            feature_name = feature_definition["name"]
            parameters = dict(feature_definition.get("parameters", {}))
            registry_entry = self._feature_registry.get(feature_name)
            output_columns = registry_entry["outputs"]

            if all(column in prepared.columns for column in output_columns):
                continue

            prepared = registry_entry["function"](prepared, **parameters)

        derived_feature_columns = [
            column
            for column in self._feature_registry.list_outputs()
            if column in prepared.columns
        ]

        if not derived_feature_columns:
            return prepared

        return prepared.dropna(subset=derived_feature_columns)

    def load(self, symbol: str, interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
        raw_data = self._history_manager.load_history(symbol, interval)

        if not isinstance(raw_data, pd.DataFrame):
            raise ValueError("historical market data must be a pandas DataFrame")

        missing_required_columns = _missing_columns(raw_data, _REQUIRED_COLUMNS)
        if missing_required_columns:
            raise ValueError(
                "historical market data is missing required columns: "
                + ", ".join(missing_required_columns)
            )

        combined_data = _normalize_date_index(raw_data)

        if not self._feature_store.features_exist(symbol, interval):
            return self._prepare_required_features(combined_data)

        feature_data = self._feature_store.load_features(symbol, interval)
        if not isinstance(feature_data, pd.DataFrame):
            raise ValueError("historical feature data must be a pandas DataFrame")

        if "Date" not in feature_data.columns:
            raise ValueError("historical feature data is missing required columns: Date")

        normalized_features = _normalize_date_index(feature_data)
        additional_feature_columns = [
            column for column in normalized_features.columns if column not in combined_data.columns
        ]

        if not additional_feature_columns:
            return self._prepare_required_features(combined_data)

        combined_data = combined_data.join(
            normalized_features[additional_feature_columns],
            how="left",
        )

        return self._prepare_required_features(combined_data)
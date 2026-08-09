"""Deterministic loader for historical backtest data."""

from __future__ import annotations

import re
from typing import Any, Iterable, TYPE_CHECKING

import pandas as pd

from analytics.feature_registry import FeatureRegistry
from analytics.feature_store import FeatureStore
from config.settings import DEFAULT_INTERVAL, FEATURE_SET
from market.history_manager import HistoryManager

if TYPE_CHECKING:
    from market.data_manager import MarketDataManager


_REQUIRED_COLUMNS = (
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
)

_LOOKBACK_PATTERN = re.compile(r"^\s*(\d+)\s*([dDwWmMyY])\s*$")


def _missing_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> list[str]:
    return [column for column in required_columns if column not in data.columns]


def _normalize_date_index(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()
    normalized["Date"] = pd.to_datetime(normalized["Date"])
    normalized = normalized.set_index("Date")
    normalized.index.name = "Date"
    return normalized.sort_index()


def _apply_lookback_period(data: pd.DataFrame, period: str | None) -> pd.DataFrame:
    if period is None:
        return data

    match = _LOOKBACK_PATTERN.match(period)
    if match is None:
        raise ValueError(
            "period must be a positive lookback string such as '30d', '8w', '6m', or '2y'"
        )

    amount = int(match.group(1))
    if amount <= 0:
        raise ValueError(
            "period must be a positive lookback string such as '30d', '8w', '6m', or '2y'"
        )

    unit = match.group(2).lower()
    if unit == "d":
        offset = pd.DateOffset(days=amount)
    elif unit == "w":
        offset = pd.DateOffset(weeks=amount)
    elif unit == "m":
        offset = pd.DateOffset(months=amount)
    else:
        offset = pd.DateOffset(years=amount)

    if data.empty:
        return data

    latest_timestamp = data.index.max()
    lookback_start = latest_timestamp - offset
    return data.loc[data.index >= lookback_start]


def _build_lookback_offset(period: str) -> pd.DateOffset:
    match = _LOOKBACK_PATTERN.match(period)
    if match is None:
        raise ValueError(
            "period must be a positive lookback string such as '30d', '8w', '6m', or '2y'"
        )

    amount = int(match.group(1))
    if amount <= 0:
        raise ValueError(
            "period must be a positive lookback string such as '30d', '8w', '6m', or '2y'"
        )

    unit = match.group(2).lower()
    if unit == "d":
        return pd.DateOffset(days=amount)

    if unit == "w":
        return pd.DateOffset(weeks=amount)

    if unit == "m":
        return pd.DateOffset(months=amount)

    return pd.DateOffset(years=amount)


def _covers_requested_period(data: pd.DataFrame, period: str | None) -> bool:
    if period is None:
        return True

    if data.empty:
        return False

    offset = _build_lookback_offset(period)
    latest_timestamp = data.index.max()
    lookback_start = latest_timestamp - offset
    earliest_timestamp = data.index.min()
    return earliest_timestamp <= lookback_start


class HistoricalDataLoader:
    """Load historical market data and available features for backtesting."""

    def __init__(
        self,
        history_manager: HistoryManager | None = None,
        market_data_manager: Any | None = None,
        feature_store: FeatureStore | None = None,
        feature_registry: FeatureRegistry | None = None,
    ) -> None:
        self._history_manager = history_manager or HistoryManager()
        if market_data_manager is None:
            from market.data_manager import MarketDataManager

            market_data_manager = MarketDataManager()

        self._market_data_manager = market_data_manager
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

    def load(
        self,
        symbol: str,
        period: str | None = None,
        interval: str = DEFAULT_INTERVAL,
    ) -> pd.DataFrame:
        raw_data = self._history_manager.load_history(symbol, interval)

        if not isinstance(raw_data, pd.DataFrame):
            raise ValueError("historical market data must be a pandas DataFrame")

        missing_required_columns = _missing_columns(raw_data, _REQUIRED_COLUMNS)
        if missing_required_columns:
            raise ValueError(
                "historical market data is missing required columns: "
                + ", ".join(missing_required_columns)
            )

        normalized_raw_data = _normalize_date_index(raw_data)
        if not _covers_requested_period(normalized_raw_data, period):
            refreshed_raw_data = self._market_data_manager.download_history(
                symbol,
                period=period,
                interval=interval,
            )

            if not isinstance(refreshed_raw_data, pd.DataFrame):
                raise ValueError("historical market data must be a pandas DataFrame")

            missing_required_columns = _missing_columns(refreshed_raw_data, _REQUIRED_COLUMNS)
            if missing_required_columns:
                raise ValueError(
                    "historical market data is missing required columns: "
                    + ", ".join(missing_required_columns)
                )

            self._history_manager.save_history(refreshed_raw_data, symbol, interval)
            normalized_raw_data = _normalize_date_index(refreshed_raw_data)

        combined_data = _apply_lookback_period(normalized_raw_data, period)
        rows_loaded = len(combined_data.index)

        if not self._feature_store.features_exist(symbol, interval):
            prepared_data = self._prepare_required_features(combined_data)
            prepared_data.attrs["rows_loaded"] = rows_loaded
            prepared_data.attrs["rows_after_cleaning"] = len(prepared_data.index)
            return prepared_data

        feature_data = self._feature_store.load_features(symbol, interval)
        if not isinstance(feature_data, pd.DataFrame):
            raise ValueError("historical feature data must be a pandas DataFrame")

        if "Date" not in feature_data.columns:
            raise ValueError("historical feature data is missing required columns: Date")

        normalized_features = _normalize_date_index(feature_data)
        if period is not None and not _covers_requested_period(normalized_features, period):
            prepared_data = self._prepare_required_features(combined_data)
            prepared_data.attrs["rows_loaded"] = rows_loaded
            prepared_data.attrs["rows_after_cleaning"] = len(prepared_data.index)
            return prepared_data

        additional_feature_columns = [
            column for column in normalized_features.columns if column not in combined_data.columns
        ]

        if not additional_feature_columns:
            prepared_data = self._prepare_required_features(combined_data)
            prepared_data.attrs["rows_loaded"] = rows_loaded
            prepared_data.attrs["rows_after_cleaning"] = len(prepared_data.index)
            return prepared_data

        combined_data = combined_data.join(
            normalized_features[additional_feature_columns],
            how="left",
        )

        prepared_data = self._prepare_required_features(combined_data)
        prepared_data.attrs["rows_loaded"] = rows_loaded
        prepared_data.attrs["rows_after_cleaning"] = len(prepared_data.index)
        return prepared_data
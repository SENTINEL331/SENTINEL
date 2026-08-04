"""Deterministic forward return calculation for historical setup rows."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any, Iterable

import pandas as pd


def _is_numeric(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class ForwardReturnResult:
    """Structured forward return outcome for one historical setup row."""

    setup_index: Any
    entry_close: float
    exit_close: float | None
    horizon: int
    forward_return: float | None
    is_available: bool

    def __post_init__(self) -> None:
        if not _is_numeric(self.entry_close):
            raise ValueError("entry_close must be numeric")

        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int):
            raise ValueError("horizon must be a positive integer")

        if self.horizon <= 0:
            raise ValueError("horizon must be a positive integer")

        if self.is_available:
            if self.exit_close is None:
                raise ValueError("exit_close is required when result is available")

            if self.forward_return is None:
                raise ValueError("forward_return is required when result is available")

            if not _is_numeric(self.exit_close):
                raise ValueError("exit_close must be numeric when result is available")

            if not _is_numeric(self.forward_return):
                raise ValueError("forward_return must be numeric when result is available")

            return

        if self.exit_close is not None:
            raise ValueError("exit_close must be None when result is unavailable")

        if self.forward_return is not None:
            raise ValueError("forward_return must be None when result is unavailable")


def _validate_horizon(horizon: int) -> None:
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise ValueError("horizon must be a positive integer")


def _validate_price_column(feature_data: pd.DataFrame, price_column: str) -> None:
    if price_column not in feature_data.columns:
        raise ValueError(f"missing required price column: {price_column}")


def _coerce_numeric_price(price_value: Any, *, price_column: str, row_identifier: Any) -> float:
    if pd.isna(price_value):
        raise ValueError(
            f"price column '{price_column}' is missing at row {row_identifier!r}"
        )

    if not _is_numeric(price_value):
        raise ValueError(
            f"price column '{price_column}' must be numeric at row {row_identifier!r}"
        )

    return float(price_value)


def _resolve_setup_position(
    feature_data: pd.DataFrame,
    setup_row: Any,
    *,
    setup_rows_are_positions: bool,
) -> int:
    if setup_rows_are_positions:
        if isinstance(setup_row, bool) or not isinstance(setup_row, int):
            raise ValueError(f"invalid setup position: {setup_row!r}")

        if setup_row < 0 or setup_row >= len(feature_data.index):
            raise ValueError(f"setup position out of range: {setup_row!r}")

        return setup_row

    matches = feature_data.index[feature_data.index == setup_row]

    if len(matches) == 0:
        raise ValueError(f"invalid setup index: {setup_row!r}")

    if len(matches) > 1:
        raise ValueError(f"setup index is not unique: {setup_row!r}")

    return int(feature_data.index.get_loc(setup_row))


def calculate_forward_returns(
    feature_data: pd.DataFrame,
    setup_rows: Iterable[Any],
    horizon: int,
    *,
    price_column: str = "Close",
    setup_rows_are_positions: bool = False,
) -> list[ForwardReturnResult]:
    """Calculate forward close-to-close returns for historical setup rows."""

    if not isinstance(feature_data, pd.DataFrame):
        raise ValueError("feature_data must be a pandas DataFrame")

    _validate_horizon(horizon)
    _validate_price_column(feature_data, price_column)

    if isinstance(setup_rows, (str, bytes)):
        raise ValueError("setup_rows must be an iterable of indexes or positions")

    try:
        resolved_setup_rows = list(setup_rows)
    except TypeError as exc:
        raise ValueError("setup_rows must be an iterable of indexes or positions") from exc

    results: list[ForwardReturnResult] = []

    for setup_row in resolved_setup_rows:
        setup_position = _resolve_setup_position(
            feature_data,
            setup_row,
            setup_rows_are_positions=setup_rows_are_positions,
        )
        setup_index = feature_data.index[setup_position]
        entry_close = _coerce_numeric_price(
            feature_data.iloc[setup_position][price_column],
            price_column=price_column,
            row_identifier=setup_index,
        )
        exit_position = setup_position + horizon

        if exit_position >= len(feature_data.index):
            results.append(
                ForwardReturnResult(
                    setup_index=setup_index,
                    entry_close=entry_close,
                    exit_close=None,
                    horizon=horizon,
                    forward_return=None,
                    is_available=False,
                )
            )
            continue

        exit_index = feature_data.index[exit_position]
        exit_close = _coerce_numeric_price(
            feature_data.iloc[exit_position][price_column],
            price_column=price_column,
            row_identifier=exit_index,
        )
        forward_return = (exit_close - entry_close) / entry_close

        results.append(
            ForwardReturnResult(
                setup_index=setup_index,
                entry_close=entry_close,
                exit_close=exit_close,
                horizon=horizon,
                forward_return=forward_return,
                is_available=True,
            )
        )

    return results
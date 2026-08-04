"""Deterministic summary metrics for forward-return backtest slices."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from numbers import Real
from statistics import median
from typing import Any

from research.forward_return_calculator import ForwardReturnResult


def _is_numeric(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _coerce_forward_return_result(item: Any) -> tuple[bool, float | None]:
    if isinstance(item, ForwardReturnResult):
        return item.is_available, item.forward_return

    if not isinstance(item, Mapping):
        raise ValueError(
            "forward return results must contain ForwardReturnResult objects or mappings"
        )

    if "is_available" not in item:
        raise ValueError("forward return result is missing required field: is_available")

    is_available = item["is_available"]
    if not isinstance(is_available, bool):
        raise ValueError("forward return result field 'is_available' must be a boolean")

    if "forward_return" not in item:
        raise ValueError("forward return result is missing required field: forward_return")

    forward_return = item["forward_return"]

    if not is_available:
        return False, None

    if forward_return is None:
        raise ValueError(
            "forward return result field 'forward_return' is required when available"
        )

    if not _is_numeric(forward_return):
        raise ValueError("forward return result field 'forward_return' must be numeric")

    return True, float(forward_return)


def calculate_backtest_metrics(
    forward_return_results: Iterable[ForwardReturnResult | Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize available forward returns into objective experiment metrics."""

    if isinstance(forward_return_results, (str, bytes)):
        raise ValueError(
            "forward_return_results must be an iterable of result objects or mappings"
        )

    try:
        resolved_results = list(forward_return_results)
    except TypeError as exc:
        raise ValueError(
            "forward_return_results must be an iterable of result objects or mappings"
        ) from exc

    available_returns: list[float] = []

    for item in resolved_results:
        is_available, forward_return = _coerce_forward_return_result(item)
        if is_available and forward_return is not None:
            available_returns.append(forward_return)

    if not available_returns:
        raise ValueError("no available forward returns to summarize")

    trade_count = len(available_returns)
    win_count = sum(1 for item in available_returns if item > 0)
    loss_count = sum(1 for item in available_returns if item < 0)

    return {
        "trade_count": trade_count,
        "average_return": sum(available_returns) / trade_count,
        "total_return": sum(available_returns),
        "win_rate": win_count / trade_count,
        "extra_metrics": {
            "loss_rate": loss_count / trade_count,
            "best_return": max(available_returns),
            "worst_return": min(available_returns),
            "median_return": float(median(available_returns)),
        },
    }
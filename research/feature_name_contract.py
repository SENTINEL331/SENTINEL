"""Canonical feature names and alias resolution for deterministic backtests."""

from __future__ import annotations

import re
from collections.abc import Iterable


_NORMALIZE_PATTERN = re.compile(r"[^A-Za-z0-9]+")

CANONICAL_FEATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "SMA_20": ("SMA_20", "SMA20"),
    "EMA_20": ("EMA_20", "EMA20"),
    "RSI_14": ("RSI_14", "RSI14"),
    "ATR_14": ("ATR_14", "ATR14"),
    "BB_LOWER": ("BB_LOWER", "BB_LOWER_20", "BB_Lower_20", "BBLower20"),
    "BB_MIDDLE": (
        "BB_MIDDLE",
        "BB_MIDDLE_20",
        "BB_Middle_20",
        "BBMiddle20",
    ),
    "BB_UPPER": ("BB_UPPER", "BB_UPPER_20", "BB_Upper_20", "BBUpper20"),
}


def _normalize_feature_name(name: str) -> str:
    return _NORMALIZE_PATTERN.sub("", name).upper()


def resolve_feature_name(name: str, available_columns: Iterable[object]) -> str:
    """Resolve a requested feature name to an available dataframe column when possible."""

    available_map = {
        _normalize_feature_name(column): column
        for column in available_columns
        if isinstance(column, str)
    }

    normalized_name = _normalize_feature_name(name)

    if normalized_name in available_map:
        return available_map[normalized_name]

    for canonical_name, aliases in CANONICAL_FEATURE_ALIASES.items():
        if normalized_name not in {_normalize_feature_name(alias) for alias in aliases}:
            continue

        normalized_canonical = _normalize_feature_name(canonical_name)
        if normalized_canonical in available_map:
            return available_map[normalized_canonical]

        return canonical_name

    return name
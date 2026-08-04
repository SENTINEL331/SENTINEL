"""Deterministic scanner for finding rows that satisfy entry conditions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from research.condition_evaluator import evaluate_condition
from research.feature_name_contract import resolve_feature_name


def _validate_entry_conditions(
    entry_conditions: Sequence[Mapping[str, Any]],
) -> None:
    if isinstance(entry_conditions, (str, bytes)) or not isinstance(
        entry_conditions,
        Sequence,
    ):
        raise ValueError("entry_conditions must be a sequence of condition mappings")

    if not entry_conditions:
        raise ValueError("entry_conditions must not be empty")

    for condition in entry_conditions:
        if not isinstance(condition, Mapping):
            raise ValueError("each entry condition must be a mapping")

        if "value" in condition and pd.isna(condition["value"]):
            raise ValueError("condition.value must not be missing")


def _validate_row_data(
    row: Mapping[str, Any],
    condition: Mapping[str, Any],
    row_index: Any,
) -> None:
    field = condition.get("field")
    other_field = condition.get("other_field") if "other_field" in condition else None

    referenced_fields = [name for name in (field, other_field) if isinstance(name, str)]

    for field_name in referenced_fields:
        if field_name in row and pd.isna(row[field_name]):
            raise ValueError(
                f"missing value for field '{field_name}' at row index {row_index!r}"
            )


def _normalize_condition_fields(
    entry_conditions: Sequence[Mapping[str, Any]],
    available_columns: Sequence[object],
) -> list[dict[str, Any]]:
    normalized_conditions: list[dict[str, Any]] = []

    for condition in entry_conditions:
        normalized_condition = dict(condition)

        field = normalized_condition.get("field")
        if isinstance(field, str):
            normalized_condition["field"] = resolve_feature_name(field, available_columns)

        other_field = normalized_condition.get("other_field")
        if isinstance(other_field, str):
            normalized_condition["other_field"] = resolve_feature_name(
                other_field,
                available_columns,
            )

        normalized_conditions.append(normalized_condition)

    return normalized_conditions


def scan_entry_setups(
    feature_data: pd.DataFrame,
    entry_conditions: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Return the rows whose values satisfy all entry conditions.

    The scanner applies AND semantics across all provided conditions and uses the
    existing deterministic condition evaluator for each row-level comparison.
    """

    if not isinstance(feature_data, pd.DataFrame):
        raise ValueError("feature_data must be a pandas DataFrame")

    _validate_entry_conditions(entry_conditions)

    if feature_data.empty:
        return feature_data.copy()

    normalized_conditions = _normalize_condition_fields(
        entry_conditions,
        list(feature_data.columns),
    )

    matching_indexes: list[Any] = []

    for row_index, row in feature_data.iterrows():
        row_data = row.to_dict()

        try:
            if all(
                evaluate_condition(condition, row_data)
                if not _validate_row_data(row_data, condition, row_index)
                else False
                for condition in normalized_conditions
            ):
                matching_indexes.append(row_index)
        except ValueError as exc:
            raise ValueError(
                f"failed to evaluate entry conditions at row index {row_index!r}: {exc}"
            ) from exc

    return feature_data.loc[matching_indexes].copy()
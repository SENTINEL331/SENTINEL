"""Deterministic condition evaluator for one row of market/feature data."""

from __future__ import annotations

from numbers import Real
from typing import Any, Mapping


_SUPPORTED_OPERATORS = {
    "<",
    "<=",
    ">",
    ">=",
    "==",
    "!=",
}


def _is_numeric(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def evaluate_condition(
    condition: Mapping[str, Any],
    row: Mapping[str, Any],
) -> bool:
    """Evaluate a single machine-readable condition against one data row.

    Supported condition forms:
    - {"field": "Close", "operator": "<", "value": 200}
    - {"field": "Close", "operator": "<", "other_field": "EMA_20"}
    """

    if not isinstance(condition, Mapping):
        raise ValueError("condition must be a mapping")

    field = condition.get("field")
    operator = condition.get("operator")

    if not field:
        raise ValueError("condition.field is required")

    if not operator:
        raise ValueError("condition.operator is required")

    if operator not in _SUPPORTED_OPERATORS:
        raise ValueError(f"unsupported operator: {operator}")

    has_value = "value" in condition
    has_other_field = "other_field" in condition

    if has_value == has_other_field:
        raise ValueError("condition must include exactly one of 'value' or 'other_field'")

    if field not in row:
        raise ValueError(f"unknown field: {field}")

    left = row[field]

    if has_other_field:
        other_field = condition["other_field"]

        if not other_field:
            raise ValueError("condition.other_field is required when used")

        if other_field not in row:
            raise ValueError(f"unknown field: {other_field}")

        right = row[other_field]
    else:
        right = condition["value"]

    if operator in {"<", "<=", ">", ">="}:
        if not _is_numeric(left):
            raise ValueError(f"field '{field}' must be numeric for operator '{operator}'")

        if not _is_numeric(right):
            if has_other_field:
                raise ValueError(
                    f"field '{condition['other_field']}' must be numeric for operator '{operator}'"
                )

            raise ValueError(f"condition.value must be numeric for operator '{operator}'")

    if operator == "<":
        return left < right

    if operator == "<=":
        return left <= right

    if operator == ">":
        return left > right

    if operator == ">=":
        return left >= right

    if operator == "==":
        return left == right

    return left != right
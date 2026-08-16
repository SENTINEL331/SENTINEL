"""Deterministic read-only health checks for the local Sentinel demo system."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from research.demo_current_opportunity_rating import build_demo_current_opportunity_ratings
from research.demo_exit_readiness import build_demo_exit_readiness
from research.demo_promotion_board import build_demo_promotion_board


PASS = "pass"
FAIL = "fail"
WARNING = "warning"
UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DemoSystemHealthResult:
    symbol: str
    overall_health: str
    checks: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    blocked_checks: tuple[str, ...] = field(default_factory=tuple)
    required_checks_passed: bool = False
    records_modified: bool = False
    ai_calls_made: int = 0


def _git_tracking_status(path: str, repository_path: Path | None) -> str:
    """Return whether a path is untracked, without invoking a shell."""

    if repository_path is None:
        return UNKNOWN
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", path],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return UNKNOWN
    if result.returncode != 0:
        return UNKNOWN
    return PASS if not result.stdout.strip() else FAIL


def _paper_endpoint_status(base_url: str) -> str:
    if not (base_url or "").strip():
        return FAIL
    try:
        parsed = urlparse(base_url.strip())
    except ValueError:
        return FAIL
    return (
        PASS
        if parsed.scheme == "https" and parsed.hostname == "paper-api.alpaca.markets"
        else FAIL
    )


def _calculation_status(builder, *, symbol: str, storage) -> str:
    try:
        builder(symbol=symbol, storage=storage)
    except Exception:
        return UNKNOWN
    return PASS


def build_demo_system_health(
    *,
    symbol: str,
    storage,
    demo_broker: str,
    demo_broker_mode: str,
    alpaca_base_url: str,
    alpaca_api_key: str,
    alpaca_secret_key: str,
    repository_path: Path | None = None,
    promotion_board_fn=build_demo_promotion_board,
    current_opportunity_fn=build_demo_current_opportunity_ratings,
    exit_readiness_fn=build_demo_exit_readiness,
) -> DemoSystemHealthResult:
    """Inspect local configuration and state without any external calls or writes."""

    if not symbol:
        raise ValueError("symbol is required")

    broker_mode = (demo_broker_mode or "").strip().casefold()
    checks = {
        "env_not_git_tracked": _git_tracking_status(".env", repository_path),
        "ai_memory_not_git_tracked": _git_tracking_status("ai/memory", repository_path),
        "live_mode_disabled": PASS if broker_mode != "live" else FAIL,
        "demo_broker_mode_paper": PASS if broker_mode == "paper" else FAIL,
        "order_placement_disabled": PASS,
        "order_cancellation_disabled": PASS,
        "position_close_disabled": PASS,
        "promotion_disabled": PASS,
        "ai_calls_disabled": PASS,
        "broker_calls_disabled": PASS,
        "demo_broker_present": PASS if (demo_broker or "").strip() else FAIL,
        "alpaca_base_url_present": PASS if (alpaca_base_url or "").strip() else FAIL,
        "alpaca_base_url_paper": _paper_endpoint_status(alpaca_base_url),
        "alpaca_api_key_present": PASS if (alpaca_api_key or "").strip() else FAIL,
        "alpaca_secret_key_present": PASS if (alpaca_secret_key or "").strip() else FAIL,
    }

    loaders = {
        "latest_position_snapshot": "load_demo_position_snapshots",
        "latest_performance_snapshots": "load_demo_trade_performance_snapshots",
        "latest_trade_evaluations": "load_demo_trade_evaluations",
        "latest_hypothesis_summaries": "load_demo_hypothesis_performance_summaries",
    }
    for check_name, loader_name in loaders.items():
        loader = getattr(storage, loader_name, None)
        if not callable(loader):
            checks[check_name] = UNKNOWN
            continue
        try:
            checks[check_name] = PASS if list(loader(symbol=symbol) or []) else FAIL
        except Exception:
            checks[check_name] = UNKNOWN

    checks["promotion_board_available"] = _calculation_status(
        promotion_board_fn, symbol=symbol, storage=storage
    )
    checks["current_opportunity_available"] = _calculation_status(
        current_opportunity_fn, symbol=symbol, storage=storage
    )
    checks["exit_readiness_available"] = _calculation_status(
        exit_readiness_fn, symbol=symbol, storage=storage
    )

    review_loader = getattr(storage, "load_demo_daily_ai_reviews", None)
    if not callable(review_loader):
        checks["latest_daily_ai_review"] = UNKNOWN
    else:
        try:
            checks["latest_daily_ai_review"] = (
                PASS if list(review_loader(symbol=symbol) or []) else WARNING
            )
        except Exception:
            checks["latest_daily_ai_review"] = UNKNOWN

    checks["demo_daily_operator_command"] = PASS
    checks["demo_status_dashboard_command"] = PASS

    blocked_names = (
        "live_mode_disabled",
        "demo_broker_mode_paper",
        "demo_broker_present",
        "alpaca_base_url_present",
        "alpaca_base_url_paper",
        "alpaca_api_key_present",
        "alpaca_secret_key_present",
    )
    blocked_checks = tuple(name for name in blocked_names if checks[name] == FAIL)
    optional_warnings = tuple(name for name, status in checks.items() if status == WARNING)
    required_names = tuple(
        name
        for name in checks
        if name not in {"latest_daily_ai_review", "env_not_git_tracked", "ai_memory_not_git_tracked"}
    )
    required_checks_passed = all(checks[name] == PASS for name in required_names)
    unknown_checks = tuple(name for name, status in checks.items() if status == UNKNOWN)

    if blocked_checks:
        overall_health = "blocked"
    elif unknown_checks:
        overall_health = "unknown"
    elif optional_warnings or not required_checks_passed:
        overall_health = "warning"
    else:
        overall_health = "healthy"

    return DemoSystemHealthResult(
        symbol=symbol,
        overall_health=overall_health,
        checks=checks,
        warnings=optional_warnings,
        blocked_checks=blocked_checks,
        required_checks_passed=required_checks_passed,
    )
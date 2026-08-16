import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_system_health import FAIL, PASS, WARNING, build_demo_system_health
from research.runner import _build_arg_parser, run_manual_demo_system_health


def _storage(*, populated=True, reviews=True):
    storage = Mock()
    value = [SimpleNamespace()] if populated else []
    storage.load_demo_position_snapshots.return_value = value
    storage.load_demo_trade_performance_snapshots.return_value = value
    storage.load_demo_trade_evaluations.return_value = value
    storage.load_demo_hypothesis_performance_summaries.return_value = value
    storage.load_demo_daily_ai_reviews.return_value = value if reviews else []
    return storage


def _health(*, storage, mode="paper"):
    with patch("research.demo_system_health._git_tracking_status", return_value=PASS):
        return build_demo_system_health(
            symbol="NVDA",
            storage=storage,
            demo_broker="alpaca",
            demo_broker_mode=mode,
            alpaca_base_url="https://paper-api.alpaca.markets",
            alpaca_api_key="key",
            alpaca_secret_key="secret",
            promotion_board_fn=Mock(),
            current_opportunity_fn=Mock(),
            exit_readiness_fn=Mock(),
        )


class DemoSystemHealthTests(unittest.TestCase):
    def test_cli_help_includes_system_health(self):
        self.assertIn("demo-system-health", _build_arg_parser().format_help())

    def test_paper_configuration_and_local_state_are_healthy(self):
        result = _health(storage=_storage())

        self.assertEqual("healthy", result.overall_health)
        self.assertTrue(result.required_checks_passed)
        self.assertEqual(PASS, result.checks["demo_broker_mode_paper"])

    def test_live_mode_is_blocked(self):
        result = _health(storage=_storage(), mode="live")

        self.assertEqual("blocked", result.overall_health)
        self.assertEqual(FAIL, result.checks["live_mode_disabled"])
        self.assertIn("demo_broker_mode_paper", result.blocked_checks)

    def test_missing_optional_ai_review_is_warning(self):
        result = _health(storage=_storage(reviews=False))

        self.assertEqual("warning", result.overall_health)
        self.assertEqual(WARNING, result.checks["latest_daily_ai_review"])

    def test_missing_local_snapshots_are_safe_and_not_healthy(self):
        result = _health(storage=_storage(populated=False))

        self.assertEqual("warning", result.overall_health)
        self.assertFalse(result.required_checks_passed)
        self.assertEqual(FAIL, result.checks["latest_position_snapshot"])

    def test_is_read_only_and_makes_no_http_calls(self):
        storage = _storage()
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = _health(storage=storage)

        self.assertFalse(result.records_modified)
        self.assertEqual(0, result.ai_calls_made)
        mock_urlopen.assert_not_called()
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))

    def test_runner_prints_next_commands_without_secrets(self):
        check_names = (
            "live_mode_disabled", "demo_broker_mode_paper", "order_placement_disabled",
            "order_cancellation_disabled", "position_close_disabled", "promotion_disabled",
            "ai_calls_disabled", "broker_calls_disabled", "demo_broker_present",
            "alpaca_base_url_present", "alpaca_base_url_paper", "alpaca_api_key_present",
            "alpaca_secret_key_present", "latest_position_snapshot",
            "latest_performance_snapshots", "latest_trade_evaluations",
            "latest_hypothesis_summaries", "promotion_board_available",
            "current_opportunity_available", "exit_readiness_available", "latest_daily_ai_review",
            "demo_daily_operator_command", "demo_status_dashboard_command",
            "env_not_git_tracked", "ai_memory_not_git_tracked",
        )
        result = Mock(
            overall_health="healthy",
            required_checks_passed=True,
            warnings=(),
            blocked_checks=(),
            checks={name: PASS for name in check_names},
        )
        with patch("builtins.print") as mock_print:
            run_manual_demo_system_health(
                symbol="NVDA", health_fn=Mock(return_value=result)
            )

        mock_print.assert_any_call("AI Calls Made : 0")
        mock_print.assert_any_call("- demo_daily_operator_command: pass")
        mock_print.assert_any_call("python -m research.runner demo-daily-operator NVDA")
        mock_print.assert_any_call("python -m research.runner demo-daily-operator NVDA --ai-review --confirm-ai-call")


if __name__ == "__main__":
    unittest.main()
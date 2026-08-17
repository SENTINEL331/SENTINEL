import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from research.runner import (
    _build_arg_parser,
    main,
    run_manual_demo_operator_runbook,
    run_manual_demo_operator_runs,
)


class DemoOperatorRunbookTests(unittest.TestCase):
    def test_cli_help_includes_runbook(self):
        self.assertIn("demo-operator-runbook", _build_arg_parser().format_help())

    def test_cli_help_includes_operator_run_history(self):
        self.assertIn("demo-operator-runs", _build_arg_parser().format_help())

    def test_operator_run_history_parser_accepts_filters(self):
        args = _build_arg_parser().parse_args(
            [
                "demo-operator-runs",
                "NVDA",
                "--limit",
                "5",
                "--decision",
                "request_fresh_ai_review",
                "--ai-review-action",
                "reviewed",
                "--status",
                "completed",
            ]
        )

        self.assertEqual(5, args.limit)
        self.assertEqual("request_fresh_ai_review", args.decision)
        self.assertEqual("reviewed", args.ai_review_action)
        self.assertEqual("completed", args.status)

    def test_operator_run_history_parser_accepts_run_detail_id(self):
        args = _build_arg_parser().parse_args(
            ["demo-operator-runs", "NVDA", "--run-id", "dor-detail"]
        )

        self.assertEqual("dor-detail", args.run_id)

    def test_prints_commands_safety_notes_and_read_only_contract(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = run_manual_demo_operator_runbook(symbol="NVDA")

        output = buffer.getvalue()
        self.assertFalse(result["records_modified"])
        self.assertIn("Manual Demo Operator Runbook: NVDA", output)
        self.assertIn("Records Modified : no", output)
        self.assertIn("AI Calls Allowed : no", output)
        self.assertIn("AI Calls Made : 0", output)
        self.assertIn("Broker Calls Allowed : no", output)
        self.assertIn("Market Data Calls Allowed : no", output)
        self.assertIn("Order Placement Allowed : no", output)
        self.assertIn("Order Cancellation Allowed : no", output)
        self.assertIn("Position Close Allowed : no", output)
        self.assertIn("Promotion Actions Taken : 0", output)
        self.assertIn("python -m research.runner demo-daily-operator NVDA", output)
        self.assertIn(
            "python -m research.runner demo-daily-operator NVDA --ai-review --confirm-ai-call",
            output,
        )
        self.assertIn("python -m research.runner demo-daily-ai-reviews NVDA", output)
        self.assertIn("Daily operator does not submit, cancel, replace, or close orders.", output)
        self.assertIn("AI review requires --confirm-ai-call.", output)
        self.assertIn("Runtime records under ai/memory/ are not committed.", output)

    def test_main_dispatches_only_runbook_runner(self):
        with patch("research.runner.run_manual_demo_operator_runbook") as mock_runbook, patch(
            "research.runner.run_manual_demo_daily_operator"
        ) as mock_operator:
            exit_code = main(["demo-operator-runbook", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_runbook.assert_called_once_with(symbol="NVDA")
        mock_operator.assert_not_called()

    def test_main_dispatches_only_operator_run_history(self):
        with patch("research.runner.run_manual_demo_operator_runs") as mock_runs, patch(
            "research.runner.run_manual_demo_daily_operator"
        ) as mock_operator:
            exit_code = main(["demo-operator-runs", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_runs.assert_called_once_with(
            symbol="NVDA",
            limit=None,
            decision=None,
            ai_review_action=None,
            status=None,
			run_id=None,
        )
        mock_operator.assert_not_called()

    def test_makes_no_http_calls(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            run_manual_demo_operator_runbook(symbol="NVDA")

        mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_ai_review_trigger import build_demo_ai_review_trigger
from research.runner import _build_arg_parser, run_manual_demo_ai_review_trigger


def _trade(**overrides):
    values = {
        "source_hypothesis_id": "hyp-001",
        "trade_evaluation_status": "needs_more_time",
        "entry_performance_rating": "flat_open",
        "board_recommendation": "not_ready",
        "current_opportunity_rating": "not_ready",
        "exit_readiness": "needs_more_time",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _exit(**overrides):
    values = {
        "source_hypothesis_id": "hyp-001",
        "broker_order_id": "broker-001",
        "order_intent_id": "intent-001",
        "evaluation_window_complete": False,
        "risk_breached": False,
        "exit_readiness": "needs_more_time",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _status(trades=()):
    return SimpleNamespace(open_demo_trades=len(trades), trades=tuple(trades))


def _exit_result(items=(), evaluations_loaded=1):
    return SimpleNamespace(items=tuple(items), evaluations_loaded=evaluations_loaded)


class DemoAIReviewTriggerTests(unittest.TestCase):
    def test_cli_help_includes_trigger(self):
        self.assertIn("demo-ai-review-trigger", _build_arg_parser().format_help())

    def _build(self, trade=None, exit_item=None):
        with patch(
            "research.demo_ai_review_trigger.build_demo_status_dashboard",
            return_value=_status([trade] if trade else []),
        ), patch(
            "research.demo_ai_review_trigger.build_demo_exit_readiness",
            return_value=_exit_result([exit_item] if exit_item else []),
        ):
            return build_demo_ai_review_trigger(symbol="NVDA", storage=Mock())

    def test_incomplete_needs_more_time_does_not_trigger_review(self):
        result = self._build(_trade(), _exit())

        self.assertFalse(result.ai_review_needed)
        self.assertEqual("none", result.primary_trigger)
        self.assertEqual("evaluation_window_incomplete", result.reason)
        self.assertEqual("continue_demo_monitoring", result.recommended_action)
        self.assertFalse(result.credits_spend_recommended)

    def test_risk_exit_exit_candidate_completed_review_and_board_triggers(self):
        cases = [
            (_trade(), _exit(risk_breached=True, exit_readiness="risk_exit_candidate"), "risk_breach"),
            (_trade(), _exit(exit_readiness="exit_candidate"), "exit_candidate"),
            (_trade(trade_evaluation_status="successful_window"), _exit(evaluation_window_complete=True, exit_readiness="hold"), "evaluation_window_complete"),
            (_trade(board_recommendation="review_later"), _exit(), "promotion_review_candidate"),
            (_trade(board_recommendation="blocked"), _exit(), "risk_breach"),
        ]

        for trade, exit_item, expected_trigger in cases:
            with self.subTest(expected_trigger=expected_trigger):
                result = self._build(trade, exit_item)
                self.assertTrue(result.ai_review_needed)
                self.assertEqual(expected_trigger, result.primary_trigger)
                self.assertTrue(result.credits_spend_recommended)

    def test_read_only_empty_state_makes_no_http_calls(self):
        storage = Mock()
        with patch("urllib.request.urlopen") as mock_urlopen, patch(
            "research.demo_ai_review_trigger.build_demo_status_dashboard",
            return_value=_status(),
        ), patch(
            "research.demo_ai_review_trigger.build_demo_exit_readiness",
            return_value=_exit_result(items=(), evaluations_loaded=0),
        ):
            result = build_demo_ai_review_trigger(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)
        self.assertFalse(result.ai_review_needed)
        self.assertEqual("unknown", result.primary_trigger)

    def test_runner_prints_ai_zero_and_no_credit_contract(self):
        result = SimpleNamespace(
            symbol="NVDA",
            ai_review_needed=False,
            primary_trigger="none",
            recommended_action="continue_demo_monitoring",
            reason="evaluation_window_incomplete",
            review_scope="none",
            credits_spend_recommended=False,
            open_demo_trades=1,
            evaluations_loaded=1,
            completed_evaluation_windows=0,
            risk_breaches=0,
            exit_candidates=0,
            risk_exit_candidates=0,
            promotion_review_candidates=0,
            disagreement_candidates=0,
            items=(),
        )
        with patch("builtins.print") as mock_print:
            run_manual_demo_ai_review_trigger(
                symbol="NVDA", trigger_fn=Mock(return_value=result)
            )

        mock_print.assert_any_call("AI Calls Made : 0")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("credits_spend_recommended=no")
        mock_print.assert_any_call("Promotion Actions Taken : 0")


if __name__ == "__main__":
    unittest.main()
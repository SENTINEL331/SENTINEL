import unittest
from datetime import datetime, timezone
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_daily_ai_review import parse_demo_daily_ai_review
from research.demo_daily_ai_review import new_review_from_payload
from ai.storage import Storage
from research.runner import _build_arg_parser, run_manual_demo_daily_ai_review


def _status():
    return SimpleNamespace(
        symbol="NVDA",
        open_demo_trades=1,
        total_entry_value=100.0,
        total_current_value=100.0,
        total_unrealized_pl=0.0,
        total_unrealized_plpc=0.0,
        trades=(),
        hypotheses=(),
    )


def _exit():
    return SimpleNamespace(items=(), readiness_counts={}, evaluations_loaded=1)


def _trigger():
    return SimpleNamespace(
        ai_review_needed=False,
        primary_trigger="none",
        recommended_action="continue_demo_monitoring",
        reason="evaluation_window_incomplete",
        items=(),
    )


def _payload():
    return '{"overall_assessment":"Continue monitoring.","what_changed_or_matters_today":"Evaluation window incomplete.","demo_trade_assessment":"Early demo evidence only.","exit_assessment":"No exit evidence yet.","promotion_assessment":"No promotion evidence yet.","current_opportunity_assessment":"Not ready.","risk_notes":"No current risk breach.","recommended_human_attention":"Continue local monitoring.","deeper_ai_review_needed":false,"reason":"evaluation_window_incomplete","confidence":"high"}'


class DemoDailyAIReviewTests(unittest.TestCase):
    def test_cli_help_includes_command_and_confirmation_flag(self):
        help_text = _build_arg_parser().format_help()
        self.assertIn("demo-daily-ai-review", help_text)
        parser = _build_arg_parser()
        args = parser.parse_args(["demo-daily-ai-review", "NVDA", "--confirm-ai-call"])
        self.assertTrue(args.confirm_ai_call)

    def _patch_context(self):
        return (
            patch("research.runner.build_demo_status_dashboard", return_value=_status()),
            patch("research.runner.build_demo_exit_readiness", return_value=_exit()),
            patch("research.runner.build_demo_ai_review_trigger", return_value=_trigger()),
        )

    def test_without_confirmation_makes_no_ai_call_or_write(self):
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = []
        ai_client = Mock()
        patches = self._patch_context()
        with patches[0], patches[1], patches[2], patch("builtins.print"):
            result = run_manual_demo_daily_ai_review(
                symbol="NVDA",
                storage=storage,
                confirm_ai_call=False,
                ai_client=ai_client,
            )

        ai_client.demo_daily_ai_review.assert_not_called()
        storage.save_demo_daily_ai_review.assert_not_called()
        self.assertEqual(0, result["ai_calls_made"])
        self.assertEqual(0, result["daily_reviews_created"])

    def test_confirmation_makes_exactly_one_call_and_saves_one_record(self):
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = []
        storage.save_demo_daily_ai_review.return_value = True
        ai_client = Mock(model="test-model")
        ai_client.demo_daily_ai_review.return_value = _payload()
        patches = self._patch_context()
        with patches[0], patches[1], patches[2], patch("builtins.print"):
            result = run_manual_demo_daily_ai_review(
                symbol="NVDA",
                storage=storage,
                confirm_ai_call=True,
                ai_client=ai_client,
            )

        ai_client.demo_daily_ai_review.assert_called_once()
        storage.save_demo_daily_ai_review.assert_called_once()
        saved = storage.save_demo_daily_ai_review.call_args.args[0]
        self.assertEqual("daily_light_demo_review", saved.ai_review_type)
        self.assertEqual(1, saved.ai_calls_made)
        self.assertEqual(1, result["daily_reviews_created"])

    def test_duplicate_fingerprint_skips_without_second_call(self):
        duplicate = SimpleNamespace(
            source_dashboard_fingerprint="a",
            source_trigger_fingerprint="b",
        )
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = [duplicate]
        ai_client = Mock()
        patches = self._patch_context()
        with patches[0], patches[1], patches[2], patch(
            "research.runner.fingerprint_context", side_effect=["a", "b"]
        ), patch("builtins.print"):
            result = run_manual_demo_daily_ai_review(
                symbol="NVDA",
                storage=storage,
                confirm_ai_call=True,
                ai_client=ai_client,
            )

        ai_client.demo_daily_ai_review.assert_not_called()
        storage.save_demo_daily_ai_review.assert_not_called()
        self.assertEqual(1, result["skipped_existing"])
        self.assertIs(duplicate, result["existing_latest_review"])

    def test_parser_accepts_strict_json_and_rejects_invalid_json(self):
        parsed = parse_demo_daily_ai_review(_payload())
        self.assertFalse(parsed["deeper_ai_review_needed"])
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_demo_daily_ai_review("not json")

    def test_runner_output_contains_zero_ai_contract(self):
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = []
        patches = self._patch_context()
        with patches[0], patches[1], patches[2], patch("builtins.print") as mock_print:
            run_manual_demo_daily_ai_review(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("AI Calls Made : 0")
        mock_print.assert_any_call("Promotion Actions Taken : 0")
        mock_print.assert_any_call("No credits were spent.")

    def test_storage_appends_and_suppresses_fingerprint_duplicate(self):
        storage = Storage()
        payload = parse_demo_daily_ai_review(_payload())
        review = new_review_from_payload(
            symbol="NVDA",
            dashboard_fingerprint="dashboard-a",
            trigger_fingerprint="trigger-a",
            ai_model="test-model",
            payload=payload,
            reviewed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            storage.base = Path(temp_dir)
            self.assertTrue(storage.save_demo_daily_ai_review(review))
            self.assertFalse(storage.save_demo_daily_ai_review(review))
            loaded = storage.load_demo_daily_ai_reviews(symbol="NVDA")

        self.assertEqual(1, len(loaded))
        self.assertEqual("daily_light_demo_review", loaded[0].ai_review_type)
        self.assertEqual("dashboard-a", loaded[0].source_dashboard_fingerprint)


if __name__ == "__main__":
    unittest.main()
import unittest
from types import SimpleNamespace

from research.demo_broker_readiness import evaluate_demo_broker_readiness


class DemoBrokerReadinessTests(unittest.TestCase):
    def test_missing_keys_and_base_url_fail_readiness(self):
        readiness = evaluate_demo_broker_readiness(
            broker_mode="demo",
            broker_base_url="",
            broker_api_key="",
            broker_api_secret="",
            queue_items=[],
        )

        self.assertFalse(readiness.ready)
        self.assertIn("broker_base_url_missing", readiness.failed_checks)
        self.assertIn("broker_api_key_missing", readiness.failed_checks)
        self.assertIn("broker_api_secret_missing", readiness.failed_checks)

    def test_live_mode_is_rejected(self):
        readiness = evaluate_demo_broker_readiness(
            broker_mode="live",
            broker_base_url="https://paper.example.local",
            broker_api_key="key",
            broker_api_secret="secret",
            queue_items=[],
        )

        self.assertFalse(readiness.ready)
        self.assertIn("live_mode_not_allowed", readiness.failed_checks)

    def test_paper_mode_can_be_ready(self):
        readiness = evaluate_demo_broker_readiness(
            broker_mode="paper",
            broker_base_url="https://paper.example.local",
            broker_api_key="key",
            broker_api_secret="secret",
            queue_items=[SimpleNamespace(status="queued", demo_only=True)],
        )

        self.assertTrue(readiness.ready)
        self.assertEqual(1, readiness.queue_items_loaded)
        self.assertEqual(1, readiness.active_queue_items)
        self.assertTrue(readiness.demo_only_queue_safe)

    def test_non_demo_queue_item_fails_safety(self):
        readiness = evaluate_demo_broker_readiness(
            broker_mode="demo",
            broker_base_url="https://paper.example.local",
            broker_api_key="key",
            broker_api_secret="secret",
            queue_items=[SimpleNamespace(status="queued", demo_only=False)],
        )

        self.assertFalse(readiness.ready)
        self.assertIn("queue_contains_non_demo_item", readiness.failed_checks)


if __name__ == "__main__":
    unittest.main()
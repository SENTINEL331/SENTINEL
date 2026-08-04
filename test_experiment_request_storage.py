import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)


class ExperimentRequestStorageTests(unittest.TestCase):
    def test_save_and_load_experiment_requests_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
            updated_at = datetime(2026, 8, 3, 0, 15, tzinfo=timezone.utc)

            request = ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Test whether breakout continuation persists over the next five sessions.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Enter after breakout close above prior 20-day high.",
                machine_readable_entry_conditions=(
                    {
                        "field": "Close",
                        "operator": ">",
                        "other_field": "EMA_20",
                    },
                ),
                exit_conditions="Exit on stop breach or five-session horizon.",
                time_horizon="5D",
                forward_horizon=5,
                status=ExperimentRequestStatus.ACCEPTED,
                source_observation_ids=("obs-1", "obs-2"),
                created_at=created_at,
                updated_at=updated_at,
            )

            storage.save_experiment_requests("NVDA", [request])

            loaded = storage.load_experiment_requests("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], ExperimentRequest)
            self.assertEqual("expreq-001", loaded[0].experiment_request_id)
            self.assertEqual("hyp-001", loaded[0].hypothesis_id)
            self.assertEqual("hyp-001:v1", loaded[0].hypothesis_version_id)
            self.assertEqual("NVDA", loaded[0].symbol)
            self.assertEqual("Validate momentum continuation", loaded[0].title)
            self.assertEqual(
                "Test whether breakout continuation persists over the next five sessions.",
                loaded[0].objective,
            )
            self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, loaded[0].test_type)
            self.assertEqual(
                "Enter after breakout close above prior 20-day high.",
                loaded[0].entry_conditions,
            )
            self.assertEqual(
                "EMA_20",
                loaded[0].machine_readable_entry_conditions[0]["other_field"],
            )
            self.assertEqual(5, loaded[0].forward_horizon)
            self.assertEqual(
                "Exit on stop breach or five-session horizon.",
                loaded[0].exit_conditions,
            )
            self.assertEqual("5D", loaded[0].time_horizon)
            self.assertEqual(ExperimentRequestStatus.ACCEPTED, loaded[0].status)
            self.assertEqual(("obs-1", "obs-2"), loaded[0].source_observation_ids)
            self.assertEqual(created_at, loaded[0].created_at)
            self.assertEqual(updated_at, loaded[0].updated_at)

            requests_file = Path(tmp_dir) / "experiments" / "requests" / "NVDA.json"
            self.assertTrue(requests_file.exists())

    def test_save_experiment_requests_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

            first = ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective one.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=created_at,
                updated_at=created_at,
            )

            duplicate = ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation updated",
                objective="Objective two.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry changed",
                exit_conditions="Exit changed",
                time_horizon="10D",
                created_at=created_at,
                updated_at=created_at,
            )

            storage.save_experiment_requests("NVDA", [first])
            storage.save_experiment_requests("NVDA", [duplicate])

            loaded = storage.load_experiment_requests("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("Validate momentum continuation", loaded[0].title)


if __name__ == "__main__":
    unittest.main()
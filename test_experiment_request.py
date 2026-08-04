import unittest
from datetime import datetime, timezone

from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)


class ExperimentRequestTests(unittest.TestCase):
    def test_creation_and_defaults(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakout continuation persists over the next five sessions.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter after breakout close above prior 20-day high.",
            exit_conditions="Exit on stop breach or five-session horizon.",
            time_horizon="5D",
            created_at=created_at,
            updated_at=created_at,
        )

        self.assertEqual("expreq-001", request.experiment_request_id)
        self.assertEqual("expreq-001", request.id)
        self.assertEqual("hyp-001", request.hypothesis_id)
        self.assertEqual("hyp-001:v1", request.hypothesis_version_id)
        self.assertEqual("NVDA", request.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, request.test_type)
        self.assertEqual(ExperimentRequestStatus.PROPOSED, request.status)
        self.assertIsNone(request.forward_horizon)
        self.assertEqual((), request.machine_readable_entry_conditions)
        self.assertEqual((), request.source_observation_ids)
        self.assertEqual(created_at, request.created_at)
        self.assertEqual(created_at, request.updated_at)

    def test_accepts_valid_machine_readable_entry_conditions(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        request = ExperimentRequest(
            experiment_request_id="expreq-structured-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter on close above EMA with RSI confirmation.",
            machine_readable_entry_conditions=(
                {
                    "field": "Close",
                    "operator": ">",
                    "other_field": "EMA_20",
                },
                {
                    "field": "RSI_14",
                    "operator": "<",
                    "value": 50,
                },
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            created_at=created_at,
            updated_at=created_at,
        )

        self.assertEqual(5, request.forward_horizon)
        self.assertEqual(2, len(request.machine_readable_entry_conditions))
        self.assertEqual(
            "EMA_20",
            request.machine_readable_entry_conditions[0]["other_field"],
        )

    def test_rejects_malformed_machine_readable_entry_conditions(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        with self.assertRaisesRegex(
            ValueError,
            r"machine_readable_entry_conditions\[0\]\.operator is required",
        ):
            ExperimentRequest(
                experiment_request_id="expreq-bad-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                machine_readable_entry_conditions=(
                    {
                        "field": "Close",
                        "value": 100,
                    },
                ),
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=created_at,
                updated_at=created_at,
            )

        with self.assertRaisesRegex(
            ValueError,
            "forward_horizon is required when machine_readable_entry_conditions are provided",
        ):
            ExperimentRequest(
                experiment_request_id="expreq-bad-002",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                machine_readable_entry_conditions=(
                    {
                        "field": "Close",
                        "operator": ">",
                        "value": 100,
                    },
                ),
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=created_at,
                updated_at=created_at,
            )

        with self.assertRaisesRegex(
            ValueError,
            "machine_readable_entry_conditions are required when forward_horizon is provided",
        ):
            ExperimentRequest(
                experiment_request_id="expreq-bad-003",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                exit_conditions="Exit",
                time_horizon="5D",
                forward_horizon=5,
                created_at=created_at,
                updated_at=created_at,
            )

    def test_rejects_missing_required_fields_and_invalid_timestamps(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)

        with self.assertRaisesRegex(ValueError, "title is required"):
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=created_at,
                updated_at=created_at,
            )

        with self.assertRaisesRegex(ValueError, "created_at must be timezone-aware"):
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=datetime(2026, 8, 3, 0, 0),
                updated_at=created_at,
            )

        with self.assertRaisesRegex(
            ValueError,
            "updated_at must not be earlier than created_at",
        ):
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Objective",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                exit_conditions="Exit",
                time_horizon="5D",
                created_at=created_at,
                updated_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            )

    def test_status_transitions(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2026, 8, 3, 0, 5, tzinfo=timezone.utc)

        request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            exit_conditions="Exit",
            time_horizon="5D",
            created_at=created_at,
            updated_at=created_at,
        )

        accepted = request.with_status(ExperimentRequestStatus.ACCEPTED, updated_at)
        queued = accepted.with_status(ExperimentRequestStatus.QUEUED, updated_at)
        running = queued.with_status(ExperimentRequestStatus.RUNNING, updated_at)
        completed = running.with_status(ExperimentRequestStatus.COMPLETED, updated_at)

        self.assertEqual(ExperimentRequestStatus.ACCEPTED, accepted.status)
        self.assertEqual(ExperimentRequestStatus.QUEUED, queued.status)
        self.assertEqual(ExperimentRequestStatus.RUNNING, running.status)
        self.assertEqual(ExperimentRequestStatus.COMPLETED, completed.status)

        with self.assertRaisesRegex(ValueError, "invalid status transition"):
            request.with_status(ExperimentRequestStatus.RUNNING, updated_at)


if __name__ == "__main__":
    unittest.main()
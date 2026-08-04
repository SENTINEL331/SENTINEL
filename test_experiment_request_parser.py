import json
import unittest
from datetime import datetime, timezone

from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.parser import parse_experiment_requests


class ExperimentRequestParserTests(unittest.TestCase):
    def test_parser_returns_experiment_request_objects(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc).isoformat()
        updated_at = datetime(2026, 8, 3, 0, 15, tzinfo=timezone.utc).isoformat()

        response = json.dumps(
            {
                "experiment_requests": [
                    {
                        "experiment_request_id": "expreq-001",
                        "hypothesis_id": "hyp-001",
                        "hypothesis_version_id": "hyp-001:v1",
                        "symbol": "NVDA",
                        "title": "Validate momentum continuation",
                        "objective": "Test whether breakout continuation persists over the next five sessions.",
                        "test_type": "initial_backtest",
                        "entry_conditions": "Enter after breakout close above prior 20-day high.",
                        "machine_readable_entry_conditions": [
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
                        ],
                        "exit_conditions": "Exit on stop breach or five-session horizon.",
                        "time_horizon": "5D",
                        "forward_horizon": 5,
                        "status": "accepted",
                        "source_observation_ids": ["obs-1", "obs-2"],
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }
                ]
            }
        )

        requests = parse_experiment_requests("NVDA", response)

        self.assertEqual(1, len(requests))
        self.assertIsInstance(requests[0], ExperimentRequest)
        self.assertEqual("expreq-001", requests[0].experiment_request_id)
        self.assertEqual("hyp-001", requests[0].hypothesis_id)
        self.assertEqual("hyp-001:v1", requests[0].hypothesis_version_id)
        self.assertEqual("NVDA", requests[0].symbol)
        self.assertEqual("Validate momentum continuation", requests[0].title)
        self.assertEqual(
            "Test whether breakout continuation persists over the next five sessions.",
            requests[0].objective,
        )
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, requests[0].test_type)
        self.assertEqual(
            "Enter after breakout close above prior 20-day high.",
            requests[0].entry_conditions,
        )
        self.assertEqual(2, len(requests[0].machine_readable_entry_conditions))
        self.assertEqual(5, requests[0].forward_horizon)
        self.assertEqual(
            "Exit on stop breach or five-session horizon.",
            requests[0].exit_conditions,
        )
        self.assertEqual("5D", requests[0].time_horizon)
        self.assertEqual(ExperimentRequestStatus.ACCEPTED, requests[0].status)
        self.assertEqual(("obs-1", "obs-2"), requests[0].source_observation_ids)
        self.assertEqual(created_at, requests[0].created_at.isoformat())
        self.assertEqual(updated_at, requests[0].updated_at.isoformat())

    def test_parser_rejects_malformed_input(self):
        with self.assertRaisesRegex(
            ValueError,
            "experiment_requests\\[0\\]\\.test_type is required",
        ):
            parse_experiment_requests(
                "NVDA",
                {
                    "experiment_requests": [
                        {
                            "experiment_request_id": "expreq-001",
                            "hypothesis_id": "hyp-001",
                            "hypothesis_version_id": "hyp-001:v1",
                            "symbol": "NVDA",
                            "title": "Validate momentum continuation",
                            "objective": "Objective",
                            "entry_conditions": "Entry",
                            "exit_conditions": "Exit",
                            "time_horizon": "5D",
                            "created_at": "2026-08-03T00:00:00+00:00",
                            "updated_at": "2026-08-03T00:00:00+00:00",
                        }
                    ]
                },
            )

        with self.assertRaisesRegex(
            ValueError,
            "experiment request response must be valid JSON",
        ):
            parse_experiment_requests("NVDA", "not-json")

        with self.assertRaisesRegex(
            ValueError,
            r"experiment_requests\[0\]\.machine_readable_entry_conditions\[0\]\.operator is required",
        ):
            parse_experiment_requests(
                "NVDA",
                {
                    "experiment_requests": [
                        {
                            "experiment_request_id": "expreq-001",
                            "hypothesis_id": "hyp-001",
                            "hypothesis_version_id": "hyp-001:v1",
                            "symbol": "NVDA",
                            "title": "Validate momentum continuation",
                            "objective": "Objective",
                            "test_type": "initial_backtest",
                            "entry_conditions": "Entry",
                            "machine_readable_entry_conditions": [
                                {
                                    "field": "Close",
                                    "value": 100,
                                }
                            ],
                            "exit_conditions": "Exit",
                            "time_horizon": "5D",
                            "forward_horizon": 5,
                        }
                    ]
                },
            )

        with self.assertRaisesRegex(
            ValueError,
            r"experiment_requests\[0\]\.forward_horizon is required when machine_readable_entry_conditions are provided",
        ):
            parse_experiment_requests(
                "NVDA",
                {
                    "experiment_requests": [
                        {
                            "experiment_request_id": "expreq-001",
                            "hypothesis_id": "hyp-001",
                            "hypothesis_version_id": "hyp-001:v1",
                            "symbol": "NVDA",
                            "title": "Validate momentum continuation",
                            "objective": "Objective",
                            "test_type": "initial_backtest",
                            "entry_conditions": "Entry",
                            "machine_readable_entry_conditions": [
                                {
                                    "field": "Close",
                                    "operator": ">",
                                    "value": 100,
                                }
                            ],
                            "exit_conditions": "Exit",
                            "time_horizon": "5D",
                        }
                    ]
                },
            )

    def test_parser_populates_missing_timestamps(self):
        response = json.dumps(
            {
                "experiment_requests": [
                    {
                        "experiment_request_id": "expreq-002",
                        "hypothesis_id": "hyp-002",
                        "hypothesis_version_id": "hyp-002:v1",
                        "symbol": "NVDA",
                        "title": "Validate pullback continuation",
                        "objective": "Test whether pullbacks within trend recover within three sessions.",
                        "test_type": "initial_backtest",
                        "entry_conditions": "Enter after pullback close above trend support.",
                        "exit_conditions": "Exit on invalidation or three-session horizon.",
                        "time_horizon": "3D",
                        "status": "proposed",
                        "source_observation_ids": ["obs-3"],
                    }
                ]
            }
        )

        requests = parse_experiment_requests("NVDA", response)

        self.assertEqual(1, len(requests))
        self.assertIsNotNone(requests[0].created_at)
        self.assertIsNotNone(requests[0].updated_at)
        self.assertIsNone(requests[0].forward_horizon)
        self.assertEqual((), requests[0].machine_readable_entry_conditions)
        self.assertEqual(timezone.utc, requests[0].created_at.tzinfo)
        self.assertEqual(timezone.utc, requests[0].updated_at.tzinfo)
        self.assertGreaterEqual(requests[0].updated_at, requests[0].created_at)

    def test_parser_uses_provided_timestamp_when_other_is_missing(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc).isoformat()

        response = {
            "experiment_requests": [
                {
                    "experiment_request_id": "expreq-003",
                    "hypothesis_id": "hyp-003",
                    "hypothesis_version_id": "hyp-003:v1",
                    "symbol": "NVDA",
                    "title": "Validate gap follow-through",
                    "objective": "Test whether opening gap strength persists intraday.",
                    "test_type": "exploratory",
                    "entry_conditions": "Enter after gap confirmation.",
                    "exit_conditions": "Exit on invalidation.",
                    "time_horizon": "1D",
                    "created_at": created_at,
                }
            ]
        }

        requests = parse_experiment_requests("NVDA", response)

        self.assertEqual(created_at, requests[0].created_at.isoformat())
        self.assertEqual(created_at, requests[0].updated_at.isoformat())

    def test_parser_generates_missing_experiment_request_id(self):
        response = {
            "experiment_requests": [
                {
                    "hypothesis_id": "hyp-004",
                    "hypothesis_version_id": "hyp-004:v1",
                    "symbol": "NVDA",
                    "title": "Validate opening strength",
                    "objective": "Test whether opening strength leads to follow-through.",
                    "test_type": "exploratory",
                    "entry_conditions": "Enter after opening strength confirmation.",
                    "exit_conditions": "Exit on invalidation or end of day.",
                    "time_horizon": "1D",
                }
            ]
        }

        first_parse = parse_experiment_requests("NVDA", response)
        second_parse = parse_experiment_requests("NVDA", response)

        generated_id = first_parse[0].experiment_request_id

        self.assertTrue(generated_id.startswith("expreq-NVDA-"))
        self.assertEqual(generated_id, second_parse[0].experiment_request_id)


if __name__ == "__main__":
    unittest.main()
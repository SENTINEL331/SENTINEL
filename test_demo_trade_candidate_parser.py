import json
import unittest

from research.parser import parse_demo_trade_candidate_proposals


class DemoTradeCandidateParserTests(unittest.TestCase):
    def test_parser_returns_normalized_demo_trade_candidate_payloads(self):
        response = json.dumps(
            {
                "demo_trade_candidates": [
                    {
                        "symbol": "NVDA",
                        "source_hypothesis_id": "hyp-001",
                        "source_research_candidate_decision": "candidate",
                        "status": "proposed",
                        "entry_logic": "Enter on breakout close above prior range.",
                        "exit_logic": "Exit on trailing stop or target.",
                        "invalidation_logic": "Invalidate on range breakdown.",
                        "maximum_holding_period": "5D",
                        "position_sizing_rule": "Risk 50 bps of equity.",
                        "max_loss_per_trade": 0.01,
                        "max_portfolio_exposure": 0.05,
                        "demo_only": True,
                        "monitoring_frequency": "15m",
                        "pause_conditions": ["halted_market"],
                        "source_evidence_summary": {"completed_experiments": 2},
                        "source_review_action": "keep",
                        "source_review_confidence": 0.72,
                        "risk_flags": ["limited_experiment_count"],
                        "created_by": "ai"
                    }
                ]
            }
        )

        proposals = parse_demo_trade_candidate_proposals("NVDA", response)

        self.assertEqual(1, len(proposals))
        self.assertEqual("NVDA", proposals[0]["symbol"])
        self.assertEqual("hyp-001", proposals[0]["source_hypothesis_id"])
        self.assertEqual("candidate", proposals[0]["source_research_candidate_decision"])
        self.assertEqual("proposed", proposals[0]["status"])
        self.assertEqual(True, proposals[0]["demo_only"])
        self.assertEqual(("halted_market",), proposals[0]["pause_conditions"])
        self.assertEqual(("limited_experiment_count",), proposals[0]["risk_flags"])

    def test_parser_rejects_invalid_status(self):
        with self.assertRaisesRegex(
            ValueError,
            "demo_trade_candidates\\[0\\]\\.status must be 'proposed'",
        ):
            parse_demo_trade_candidate_proposals(
                "NVDA",
                {
                    "demo_trade_candidates": [
                        {
                            "symbol": "NVDA",
                            "source_hypothesis_id": "hyp-001",
                            "source_research_candidate_decision": "candidate",
                            "status": "gate_passed",
                            "entry_logic": "Entry",
                            "exit_logic": "Exit",
                            "invalidation_logic": "Invalidate",
                            "maximum_holding_period": "5D",
                            "position_sizing_rule": "Rule",
                            "max_loss_per_trade": 0.01,
                            "max_portfolio_exposure": 0.05,
                            "demo_only": True,
                            "monitoring_frequency": "15m",
                            "pause_conditions": [],
                            "source_evidence_summary": {},
                            "source_review_action": "keep",
                            "source_review_confidence": 0.5,
                            "risk_flags": [],
                            "created_by": "ai"
                        }
                    ]
                },
            )


if __name__ == "__main__":
    unittest.main()
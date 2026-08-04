import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus


class HypothesisRevisionApplicationStorageTests(unittest.TestCase):
    def test_save_and_load_hypothesis_revision_applications_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
            application = HypothesisRevisionApplication(
                application_id="hypreva-001",
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                status=HypothesisRevisionApplicationStatus.DRY_RUN,
                apply_mode=False,
                child_hypothesis_id="hyp-002",
                message="dry run preview",
                created_at=created_at,
            )

            storage.save_hypothesis_revision_applications("NVDA", [application])

            loaded = storage.load_hypothesis_revision_applications("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], HypothesisRevisionApplication)
            self.assertEqual("hypreva-001", loaded[0].application_id)
            self.assertEqual(HypothesisRevisionApplicationStatus.DRY_RUN, loaded[0].status)
            self.assertEqual(False, loaded[0].apply_mode)
            self.assertEqual("hyp-002", loaded[0].child_hypothesis_id)
            self.assertEqual(created_at, loaded[0].created_at)

            applications_file = Path(tmp_dir) / "hypotheses" / "revision_applications" / "NVDA.json"
            self.assertTrue(applications_file.exists())

    def test_save_hypothesis_revision_applications_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
            first = HypothesisRevisionApplication(
                application_id="hypreva-001",
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                status=HypothesisRevisionApplicationStatus.DRY_RUN,
                apply_mode=False,
                child_hypothesis_id=None,
                message="first",
                created_at=created_at,
            )
            duplicate = HypothesisRevisionApplication(
                application_id="hypreva-001",
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                status=HypothesisRevisionApplicationStatus.REJECTED,
                apply_mode=True,
                child_hypothesis_id=None,
                message="duplicate",
                created_at=created_at,
            )

            storage.save_hypothesis_revision_applications("NVDA", [first])
            storage.save_hypothesis_revision_applications("NVDA", [duplicate])

            loaded = storage.load_hypothesis_revision_applications("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual(HypothesisRevisionApplicationStatus.DRY_RUN, loaded[0].status)


if __name__ == "__main__":
    unittest.main()

"""Manual append-only application of hypothesis revision proposals."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from ai.storage import Storage
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType


class HypothesisRevisionApplicationService:
    """Apply revision proposals explicitly and append-only."""

    def __init__(self, storage=None):
        self.storage = storage or Storage()

    def _now(self):
        return datetime.now(timezone.utc)

    def _new_application_id(self, symbol, proposal_id, now):
        digest = sha256(f"{symbol}|{proposal_id}|{now.isoformat()}".encode("utf-8")).hexdigest()[:12]
        return f"hypreva-{symbol}-{digest}"

    def _build_application(
        self,
        *,
        proposal,
        status,
        apply_mode,
        message,
        child_hypothesis_id=None,
        now=None,
    ):
        created_at = now or self._now()

        return HypothesisRevisionApplication(
            application_id=self._new_application_id(
                proposal.symbol,
                proposal.proposal_id,
                created_at,
            ),
            proposal_id=proposal.proposal_id,
            symbol=proposal.symbol,
            parent_hypothesis_id=proposal.parent_hypothesis_id,
            status=status,
            apply_mode=apply_mode,
            child_hypothesis_id=child_hypothesis_id,
            message=message,
            created_at=created_at,
        )

    def _find_proposal(self, symbol, proposal_id):
        proposals = self.storage.load_hypothesis_revision_proposals(symbol)

        for proposal in proposals:
            if proposal.proposal_id == proposal_id:
                return proposal

        return None

    def _find_hypothesis(self, hypotheses, hypothesis_id):
        for hypothesis in hypotheses:
            if hypothesis.hypothesis_id == hypothesis_id:
                return hypothesis

        return None

    def _find_child_for_proposal(self, hypotheses, proposal_id):
        for hypothesis in hypotheses:
            if hypothesis.source_revision_proposal_id == proposal_id:
                return hypothesis

        return None

    def _new_child_hypothesis_id(self, symbol, proposal, hypotheses):
        digest = sha256(
            "|".join(
                [
                    symbol,
                    proposal.proposal_id,
                    proposal.parent_hypothesis_id,
                    proposal.proposed_title,
                    proposal.proposed_description,
                ]
            ).encode("utf-8")
        ).hexdigest()[:12]
        base_id = f"hyp-{symbol}-{digest}"

        existing_ids = {hypothesis.hypothesis_id for hypothesis in hypotheses}
        if base_id not in existing_ids:
            return base_id

        suffix = 2
        while True:
            candidate = f"{base_id}-{suffix}"
            if candidate not in existing_ids:
                return candidate

            suffix += 1

    def _build_child_hypothesis(self, proposal, parent, hypotheses, now):
        child_id = self._new_child_hypothesis_id(proposal.symbol, proposal, hypotheses)

        return Hypothesis(
            hypothesis_id=child_id,
            symbol=proposal.symbol,
            title=proposal.proposed_title,
            description=proposal.proposed_description,
            status=HypothesisStatus.PROPOSED,
            confidence=proposal.confidence,
            source_observation_ids=(),
            parent_hypothesis_id=parent.hypothesis_id,
            lineage_hypothesis_ids=parent.lineage_hypothesis_ids + (parent.hypothesis_id,),
            source_revision_proposal_id=proposal.proposal_id,
            experiment_refs=(),
            created_at=now,
            updated_at=now,
        )

    def _reject(self, proposal, apply_mode, reason, now):
        application = self._build_application(
            proposal=proposal,
            status=HypothesisRevisionApplicationStatus.REJECTED,
            apply_mode=apply_mode,
            message=reason,
            now=now,
        )
        self.storage.save_hypothesis_revision_applications(proposal.symbol, [application])
        return application

    def apply_proposal(self, symbol, proposal_id, apply_mode=False):
        """Apply one proposal in dry-run or apply mode and append an event."""

        if not symbol:
            raise ValueError("symbol is required")

        if not proposal_id:
            raise ValueError("proposal_id is required")

        proposal = self._find_proposal(symbol, proposal_id)
        if proposal is None:
            # Proposal metadata is unavailable, so emit a synthetic rejected record under
            # the requested symbol.
            now = self._now()
            application = HypothesisRevisionApplication(
                application_id=self._new_application_id(symbol, proposal_id, now),
                proposal_id=proposal_id,
                symbol=symbol,
                parent_hypothesis_id="unknown",
                status=HypothesisRevisionApplicationStatus.REJECTED,
                apply_mode=apply_mode,
                child_hypothesis_id=None,
                message="proposal not found",
                created_at=now,
            )
            self.storage.save_hypothesis_revision_applications(symbol, [application])
            return application

        now = self._now()

        if proposal.symbol != symbol:
            return self._reject(
                proposal,
                apply_mode,
                "symbol mismatch between command symbol and proposal",
                now,
            )

        hypotheses = self.storage.load_hypotheses(symbol)
        parent = self._find_hypothesis(hypotheses, proposal.parent_hypothesis_id)

        if parent is None:
            return self._reject(
                proposal,
                apply_mode,
                "parent hypothesis not found",
                now,
            )

        if parent.symbol != symbol:
            return self._reject(
                proposal,
                apply_mode,
                "parent hypothesis symbol mismatch",
                now,
            )

        if proposal.proposal_type != HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS:
            return self._reject(
                proposal,
                apply_mode,
                "unsupported proposal_type for manual apply",
                now,
            )

        existing_child = self._find_child_for_proposal(hypotheses, proposal.proposal_id)

        if existing_child is not None:
            status = (
                HypothesisRevisionApplicationStatus.DRY_RUN
                if not apply_mode
                else HypothesisRevisionApplicationStatus.SKIPPED_DUPLICATE
            )
            message = (
                "dry run preview: child already exists"
                if not apply_mode
                else "duplicate apply skipped: child already exists"
            )
            application = self._build_application(
                proposal=proposal,
                status=status,
                apply_mode=apply_mode,
                message=message,
                child_hypothesis_id=existing_child.hypothesis_id,
                now=now,
            )
            self.storage.save_hypothesis_revision_applications(symbol, [application])
            return application

        if not apply_mode:
            preview_child_id = self._new_child_hypothesis_id(symbol, proposal, hypotheses)
            application = self._build_application(
                proposal=proposal,
                status=HypothesisRevisionApplicationStatus.DRY_RUN,
                apply_mode=False,
                message="dry run preview: proposal can create a child hypothesis",
                child_hypothesis_id=preview_child_id,
                now=now,
            )
            self.storage.save_hypothesis_revision_applications(symbol, [application])
            return application

        child = self._build_child_hypothesis(proposal, parent, hypotheses, now)
        self.storage.save_hypotheses(symbol, [child])

        application = self._build_application(
            proposal=proposal,
            status=HypothesisRevisionApplicationStatus.APPLIED,
            apply_mode=True,
            message="proposal applied: child hypothesis created",
            child_hypothesis_id=child.hypothesis_id,
            now=now,
        )
        self.storage.save_hypothesis_revision_applications(symbol, [application])
        return application

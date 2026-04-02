"""Backfill superseded_by_id for existing VTEC event chains.

The superseded_by_id column was added in 20260401_add_superseded_by_to_cap_alerts,
but alerts that arrived before that migration was applied (or before the poller
gained the chain-linking logic) were never linked.  This migration performs a
one-time backfill using a window function:

  Within each VTEC event key group (office + phenomenon + significance + etn +
  year), alerts are ordered by their sent timestamp.  Every alert that has a
  newer sibling in the same group gets its superseded_by_id set to that sibling's
  id — only if it is not already set, so re-running is safe.

  Additionally, alerts superseded by a terminal VTEC action (CAN or EXP) are
  immediately expired so they surface in the expired-alerts view rather than
  lingering as phantom active alerts.

Revision ID: 20260402_backfill_vtec_superseded_alerts
Revises: 20260402_add_max_activation_seconds_to_eas_settings
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op

revision = "20260402_backfill_vtec_superseded_alerts"
down_revision = "20260402_add_max_activation_seconds_to_eas_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: For each VTEC event chain, link each alert to the next-newer
    # alert in the same chain using a LEAD window function.  Only rows with
    # all five VTEC key fields populated and no existing superseded_by_id are
    # touched.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                LEAD(id) OVER (
                    PARTITION BY vtec_office,
                                 vtec_phenomenon,
                                 vtec_significance,
                                 vtec_etn,
                                 vtec_year
                    ORDER BY sent ASC NULLS LAST
                ) AS next_id
            FROM cap_alerts
            WHERE vtec_office       IS NOT NULL
              AND vtec_phenomenon   IS NOT NULL
              AND vtec_significance IS NOT NULL
              AND vtec_etn          IS NOT NULL
              AND vtec_year         IS NOT NULL
        )
        UPDATE cap_alerts
        SET    superseded_by_id = ranked.next_id
        FROM   ranked
        WHERE  cap_alerts.id               = ranked.id
          AND  ranked.next_id              IS NOT NULL
          AND  cap_alerts.superseded_by_id IS NULL
        """
    )

    # Step 2: Alerts superseded by a terminal action (CAN / EXP) are over.
    # Expire them immediately so they leave the active-alerts count.
    op.execute(
        """
        UPDATE cap_alerts
        SET    expires = NOW(),
               status  = 'Expired'
        WHERE  superseded_by_id IS NOT NULL
          AND  status           != 'Expired'
          AND  (expires IS NULL OR expires > NOW())
          AND  EXISTS (
                   SELECT 1
                   FROM   cap_alerts superseder
                   WHERE  superseder.id          = cap_alerts.superseded_by_id
                     AND  superseder.vtec_action IN ('CAN', 'EXP')
               )
        """
    )


def downgrade() -> None:
    # The backfill is not reversible in a meaningful way; a full downgrade
    # would require knowing which superseded_by_id values were set by this
    # migration versus the live poller.  Clear only the column — the
    # 20260401 migration's downgrade will drop it entirely if needed.
    pass

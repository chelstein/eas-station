"""Add IPAWS enrichment columns for certificate details and audio storage.

Revision ID: 20260210_add_ipaws_enrichment
Revises: 20260210_add_local_authorities
Create Date: 2026-02-10

Adds certificate_info (JSON) to store full X.509 certificate details extracted
from IPAWS XML digital signatures, and ipaws_audio_url (String) to store the
path to the original IPAWS audio file saved to disk.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260210_add_ipaws_enrichment"
down_revision = "20260210_add_local_authorities"
branch_labels = None
depends_on = None

TABLE = "cap_alerts"


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    try:
        columns = [c["name"] for c in insp.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade() -> None:
    if not _column_exists(TABLE, "signature_verified"):
        op.add_column(TABLE, sa.Column("signature_verified", sa.Boolean(), nullable=True))

    if not _column_exists(TABLE, "signature_status"):
        op.add_column(TABLE, sa.Column("signature_status", sa.String(255), nullable=True))

    if not _column_exists(TABLE, "certificate_info"):
        op.add_column(TABLE, sa.Column("certificate_info", sa.JSON(), nullable=True))

    if not _column_exists(TABLE, "ipaws_audio_url"):
        op.add_column(TABLE, sa.Column("ipaws_audio_url", sa.String(512), nullable=True))


def downgrade() -> None:
    if _column_exists(TABLE, "ipaws_audio_url"):
        op.drop_column(TABLE, "ipaws_audio_url")
    if _column_exists(TABLE, "certificate_info"):
        op.drop_column(TABLE, "certificate_info")
    if _column_exists(TABLE, "signature_status"):
        op.drop_column(TABLE, "signature_status")
    if _column_exists(TABLE, "signature_verified"):
        op.drop_column(TABLE, "signature_verified")

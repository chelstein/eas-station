"""Add audio_sample_rate column to radio_receivers table.

This migration separates IQ sample rate (sample_rate) from audio output rate (audio_sample_rate).

- sample_rate: IQ sample rate from SDR hardware (e.g., 2.4 MHz for RTL-SDR)
- audio_sample_rate: Demodulated audio output rate (e.g., 48 kHz for FM stereo)

This fixes the root cause of:
1. No Icecast mount points (broken demodulation)
2. Wrong waterfall frequency scale (kHz instead of MHz)
3. High-pitched audio squeal (wrong demodulator configuration)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20251205_audio_sample_rate"
down_revision = "20251203_add_mfa_last_totp_timestamp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audio_sample_rate column and populate with intelligent defaults."""

    conn = op.get_bind()
    inspector = inspect(conn)

    # Only proceed if radio_receivers table exists
    if "radio_receivers" not in inspector.get_table_names():
        return

    # Check if column already exists
    columns = {col["name"] for col in inspector.get_columns("radio_receivers")}
    if "audio_sample_rate" in columns:
        return

    # Add the new column (nullable initially for data migration)
    op.add_column(
        "radio_receivers",
        sa.Column("audio_sample_rate", sa.Integer(), nullable=True),
    )

    # Populate audio_sample_rate with intelligent defaults based on modulation type
    conn.execute(
        text("""
            UPDATE radio_receivers
            SET audio_sample_rate = CASE
                -- Wide FM (broadcast): high quality stereo
                WHEN modulation_type IN ('FM', 'WFM', 'WBFM') AND stereo_enabled = true THEN 48000
                -- Wide FM (broadcast): mono
                WHEN modulation_type IN ('FM', 'WFM', 'WBFM') THEN 32000
                -- Narrowband FM or AM: lower rate acceptable
                WHEN modulation_type IN ('NFM', 'AM') THEN 24000
                -- IQ or unknown: safe default
                ELSE 44100
            END
        """)
    )

    # Fix any sample_rate values that are clearly audio rates (< 1 MHz)
    # These should be IQ rates (MHz range) not audio rates (kHz range)
    conn.execute(
        text("""
            UPDATE radio_receivers
            SET sample_rate = CASE
                -- RTL-SDR: 2.4 MHz is standard
                WHEN driver = 'rtlsdr' AND sample_rate < 1000000 THEN 2400000
                -- Airspy: 10 MHz is a common rate
                WHEN driver = 'airspy' AND sample_rate < 1000000 THEN 10000000
                -- Other SDRs: 2.4 MHz is a safe default
                WHEN sample_rate < 1000000 THEN 2400000
                -- Already correct (>= 1 MHz)
                ELSE sample_rate
            END
        """)
    )

    # Log the migration for debugging
    result = conn.execute(text("SELECT COUNT(*) FROM radio_receivers"))
    count = result.scalar()
    print(f"✅ Migrated {count} radio receiver(s) to use separate IQ and audio sample rates")

    # Print summary of changes
    result = conn.execute(
        text("""
            SELECT
                identifier,
                driver,
                sample_rate as iq_rate,
                audio_sample_rate,
                modulation_type,
                stereo_enabled
            FROM radio_receivers
            ORDER BY identifier
        """)
    )
    print("\nRadio Receiver Sample Rate Configuration:")
    print("=" * 100)
    print(f"{'Identifier':<20} {'Driver':<10} {'IQ Rate':<12} {'Audio Rate':<12} {'Modulation':<12} {'Stereo':<8}")
    print("-" * 100)
    for row in result:
        iq_hz = row[2]
        audio_hz = row[3]
        iq_display = f"{iq_hz / 1_000_000:.2f} MHz" if iq_hz >= 1_000_000 else f"{iq_hz} Hz"
        audio_display = f"{audio_hz / 1_000:.1f} kHz" if audio_hz >= 1_000 else f"{audio_hz} Hz"
        print(f"{row[0]:<20} {row[1]:<10} {iq_display:<12} {audio_display:<12} {row[4]:<12} {str(row[5]):<8}")
    print("=" * 100)


def downgrade() -> None:
    """Remove audio_sample_rate column."""

    conn = op.get_bind()
    inspector = inspect(conn)

    if "radio_receivers" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("radio_receivers")}
    if "audio_sample_rate" not in columns:
        return

    op.drop_column("radio_receivers", "audio_sample_rate")

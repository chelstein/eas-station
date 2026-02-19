"""Replace mail_url with individual SMTP connection fields.

Replaces the single mail_url string with separate structured fields:
- smtp_host: SMTP server hostname
- smtp_port: SMTP server port
- smtp_username: SMTP authentication username
- smtp_password: SMTP authentication password
- smtp_security: Connection security mode ("none", "starttls", "ssl")

Existing mail_url values are parsed and migrated to the new fields automatically.

Revision ID: 20260219_refactor_smtp_to_fields
Revises: 20260219_add_sms_email_notifications
Create Date: 2026-02-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from urllib.parse import urlparse, parse_qs


revision = "20260219_refactor_smtp_to_fields"
down_revision = "20260219_add_sms_email_notifications"
branch_labels = None
depends_on = None


def _parse_url(mail_url: str) -> dict:
    """Parse an existing mail_url into individual field values."""
    if not mail_url:
        return {"host": "", "port": 587, "username": "", "password": "", "security": "starttls"}

    try:
        parsed = urlparse(mail_url)
        qs = parse_qs(parsed.query)

        ssl_raw = qs.get("ssl", ["false"])[0]
        use_ssl = parsed.scheme == "smtps" or ssl_raw.lower() in ("true", "1", "yes")

        tls_raw = qs.get("tls", ["false"])[0]
        use_tls = tls_raw.lower() in ("true", "1", "yes")

        if use_ssl:
            security = "ssl"
            default_port = 465
        elif use_tls:
            security = "starttls"
            default_port = 587
        else:
            security = "none"
            default_port = 587

        return {
            "host": parsed.hostname or "",
            "port": int(parsed.port) if parsed.port else default_port,
            "username": (parsed.username or "").strip(),
            "password": (parsed.password or "").strip(),
            "security": security,
        }
    except Exception:
        return {"host": "", "port": 587, "username": "", "password": "", "security": "starttls"}


def upgrade() -> None:
    """Add individual SMTP fields and migrate data from mail_url."""
    conn = op.get_bind()
    from sqlalchemy import inspect, text
    inspector = inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns("notification_settings")}

    # Add new columns
    if "smtp_host" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("smtp_host", sa.String(255), nullable=False, server_default=""),
        )
    if "smtp_port" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        )
    if "smtp_username" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("smtp_username", sa.String(255), nullable=False, server_default=""),
        )
    if "smtp_password" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("smtp_password", sa.String(255), nullable=False, server_default=""),
        )
    if "smtp_security" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("smtp_security", sa.String(10), nullable=False, server_default="starttls"),
        )

    # Migrate existing mail_url values to the new fields
    if "mail_url" in existing_cols:
        rows = conn.execute(text("SELECT id, mail_url FROM notification_settings")).fetchall()
        for row in rows:
            parsed = _parse_url(row[1] or "")
            conn.execute(
                text(
                    "UPDATE notification_settings SET "
                    "smtp_host = :host, smtp_port = :port, "
                    "smtp_username = :username, smtp_password = :password, "
                    "smtp_security = :security "
                    "WHERE id = :id"
                ),
                {
                    "host": parsed["host"],
                    "port": parsed["port"],
                    "username": parsed["username"],
                    "password": parsed["password"],
                    "security": parsed["security"],
                    "id": row[0],
                },
            )

        # Drop the old mail_url column
        op.drop_column("notification_settings", "mail_url")


def downgrade() -> None:
    """Re-add mail_url and reconstruct from individual fields."""
    conn = op.get_bind()
    from sqlalchemy import inspect, text
    inspector = inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns("notification_settings")}

    if "mail_url" not in existing_cols:
        op.add_column(
            "notification_settings",
            sa.Column("mail_url", sa.String(500), nullable=False, server_default=""),
        )

    # Reconstruct mail_url from individual fields
    rows = conn.execute(
        text("SELECT id, smtp_host, smtp_port, smtp_username, smtp_password, smtp_security "
             "FROM notification_settings")
    ).fetchall()
    for row in rows:
        row_id, host, port, username, password, security = row
        if host:
            scheme = "smtps" if security == "ssl" else "smtp"
            tls_param = "?tls=true" if security == "starttls" else ""
            if username and password:
                url = f"{scheme}://{username}:{password}@{host}:{port}{tls_param}"
            else:
                url = f"{scheme}://{host}:{port}{tls_param}"
            conn.execute(
                text("UPDATE notification_settings SET mail_url = :url WHERE id = :id"),
                {"url": url, "id": row_id},
            )

    # Drop the new columns
    for col in ("smtp_security", "smtp_password", "smtp_username", "smtp_port", "smtp_host"):
        if col in existing_cols:
            op.drop_column("notification_settings", col)

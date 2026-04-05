"""Add auth verification fields and oauth_accounts table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-21
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN name TEXT")
    op.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN verification_token_hash TEXT")
    op.execute("ALTER TABLE users ADD COLUMN verification_token_expires_at TIMESTAMPTZ")
    op.execute("CREATE INDEX idx_users_verification_token_hash ON users (verification_token_hash)")

    # Existing accounts are treated as verified to avoid breaking current workflows.
    op.execute("UPDATE users SET is_verified = TRUE")

    op.execute("""
        CREATE TABLE oauth_accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            provider_account_id TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_oauth_provider_account UNIQUE (provider, provider_account_id),
            CONSTRAINT uq_oauth_user_provider UNIQUE (user_id, provider)
        )
    """)
    op.execute("CREATE INDEX idx_oauth_user_id ON oauth_accounts (user_id)")
    op.execute("""
        CREATE TRIGGER trg_oauth_accounts_updated_at
            BEFORE UPDATE ON oauth_accounts FOR EACH ROW EXECUTE FUNCTION touch_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_oauth_accounts_updated_at ON oauth_accounts")
    op.execute("DROP TABLE IF EXISTS oauth_accounts")

    op.execute("DROP INDEX IF EXISTS idx_users_verification_token_hash")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_token_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_token_hash")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_verified")
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS name")

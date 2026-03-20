"""Initial schema: enums, tables, indexes, triggers.

Revision ID: 0001
Revises:
Create Date: 2026-03-13
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # asyncpg requires one statement per execute call — no multi-statement strings

    # Enums
    op.execute("CREATE TYPE language_enum AS ENUM ('python', 'cpp', 'java', 'nodejs')")
    op.execute("CREATE TYPE submission_status AS ENUM ('pending', 'running', 'completed')")
    op.execute("CREATE TYPE verdict_enum AS ENUM ('ACC', 'WA', 'TLE', 'MLE', 'RE', 'CE', 'IE')")

    # users
    op.execute("""
        CREATE TABLE users (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            email         TEXT        NOT NULL UNIQUE,
            password_hash TEXT        NOT NULL,
            role          TEXT        NOT NULL DEFAULT 'user'
                                      CHECK (role IN ('user', 'admin', 'problem_setter')),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_users_email ON users (email)")

    # problems
    op.execute("""
        CREATE TABLE problems (
            id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            title                TEXT        NOT NULL,
            description          TEXT        NOT NULL,
            base_time_limit_ms   INTEGER     NOT NULL CHECK (base_time_limit_ms   > 0),
            base_memory_limit_mb INTEGER     NOT NULL CHECK (base_memory_limit_mb > 0),
            created_by           UUID        NOT NULL REFERENCES users(id),
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # test_cases
    op.execute("""
        CREATE TABLE test_cases (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            problem_id      UUID        NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
            input_data      TEXT        NOT NULL,
            expected_output TEXT        NOT NULL,
            is_sample       BOOLEAN     NOT NULL DEFAULT FALSE,
            ordering        INTEGER     NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_input_size    CHECK (octet_length(input_data)      <= 1048576),
            CONSTRAINT chk_expected_size CHECK (octet_length(expected_output) <= 1048576)
        )
    """)
    op.execute("CREATE INDEX idx_test_cases_problem ON test_cases (problem_id, ordering ASC)")

    # submissions
    op.execute("""
        CREATE TABLE submissions (
            id                UUID              PRIMARY KEY,
            user_id           UUID              NOT NULL REFERENCES users(id),
            problem_id        UUID              NOT NULL REFERENCES problems(id),
            language          language_enum     NOT NULL,
            code              TEXT              NOT NULL CHECK (octet_length(code) <= 65536),
            status            submission_status NOT NULL DEFAULT 'pending',
            verdict           verdict_enum,
            execution_time_ms INTEGER,
            memory_used_mb    NUMERIC(8, 2),
            stdout_snippet    TEXT,
            stderr_snippet    TEXT,
            created_at        TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ       NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_submissions_user ON submissions (user_id, created_at DESC)")
    op.execute("CREATE INDEX idx_submissions_problem ON submissions (problem_id, created_at DESC)")
    op.execute(
        "CREATE INDEX idx_submissions_status ON submissions (status) WHERE status != 'completed'"
    )

    # updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION touch_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $fn$
    """)
    op.execute("""
        CREATE TRIGGER trg_submissions_updated_at
            BEFORE UPDATE ON submissions FOR EACH ROW EXECUTE FUNCTION touch_updated_at()
    """)
    op.execute("""
        CREATE TRIGGER trg_problems_updated_at
            BEFORE UPDATE ON problems FOR EACH ROW EXECUTE FUNCTION touch_updated_at()
    """)
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION touch_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_submissions_updated_at ON submissions")
    op.execute("DROP TRIGGER IF EXISTS trg_problems_updated_at ON problems")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS touch_updated_at()")
    op.execute("DROP TABLE IF EXISTS submissions")
    op.execute("DROP TABLE IF EXISTS test_cases")
    op.execute("DROP TABLE IF EXISTS problems")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS verdict_enum")
    op.execute("DROP TYPE IF EXISTS submission_status")
    op.execute("DROP TYPE IF EXISTS language_enum")

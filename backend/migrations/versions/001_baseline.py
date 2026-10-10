"""Baseline v11; adopt existing v10 tables without dropping customer data."""
from alembic import op
from app.db import Base
import app.db_models
revision = "001_v11"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(op.get_bind(), checkfirst=True)
    # Indexes are safe to add on both existing and new databases.
    op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_owner_updated ON chat_sessions (owner_id, updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_session_created ON chat_messages (session_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_logs_owner_created ON inspection_logs (owner_id, created_at)")

def downgrade():
    raise RuntimeError("Destructive baseline downgrade disabled. Restore a verified backup instead.")

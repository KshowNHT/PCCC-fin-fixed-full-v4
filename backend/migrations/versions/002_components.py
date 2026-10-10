"""Add independent buildings; preserve existing customer rows."""
from alembic import op
import sqlalchemy as sa
revision = "002_components"
down_revision = "001_v11"
branch_labels = None
depends_on = None

def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("project_data")}
    for name, kind in (("components", sa.JSON()), ("components_complete", sa.Boolean()),
                       ("shared_systems", sa.Boolean()), ("concurrent_design", sa.Boolean()),
                       ("volume", sa.Float()), ("hazard_class", sa.String(8)),
                       ("industrial_subtype", sa.String(32))):
        if name not in existing:
            op.add_column("project_data", sa.Column(name, kind, nullable=True))

def downgrade():
    raise RuntimeError("Restore a verified backup; destructive downgrade disabled")

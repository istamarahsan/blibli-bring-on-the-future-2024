"""create fetch retry table

Revision ID: bba97d497360
Revises: 679eb2f498b9
Create Date: 2024-12-14 20:15:51.210793+07:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bba97d497360"
down_revision: Union[str, None] = "679eb2f498b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fetch_retry",
        sa.Column("componentPurl", sa.Text, nullable=False, primary_key=True),
        sa.Column("source", sa.Text, nullable=False, primary_key=True),
        sa.Column("lastAttemptAt", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fetch_retry")

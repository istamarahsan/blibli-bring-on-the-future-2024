"""empty message

Revision ID: 679eb2f498b9
Revises: 
Create Date: 2024-12-10 08:45:46.684504+07:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "679eb2f498b9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component",
        sa.Column("purl", sa.Text, nullable=False, primary_key=True),
        sa.Column("updatedAt", sa.DateTime, nullable=False),
    )

    op.create_table(
        "component_license_expression",
        sa.Column(
            "componentPurl",
            sa.Text,
            sa.ForeignKey("component.purl"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("expression", sa.Text, nullable=False, primary_key=True),
        sa.Column("source", sa.Text, nullable=False, primary_key=True),
    )

    op.create_table(
        "component_attribution",
        sa.Column(
            "componentPurl",
            sa.Text,
            sa.ForeignKey("component.purl"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("attribution", sa.Text, nullable=False, primary_key=True),
        sa.Column("source", sa.Text, nullable=False, primary_key=True),
    )

    op.create_table(
        "component_source_code_url",
        sa.Column(
            "componentPurl",
            sa.Text,
            sa.ForeignKey("component.purl"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("sourceCodeUrl", sa.Text, nullable=False, primary_key=True),
        sa.Column("source", sa.Text, nullable=False, primary_key=True),
    )

    op.create_table(
        "component_clearly_defined_full",
        sa.Column(
            "componentPurl",
            sa.Text,
            sa.ForeignKey("component.purl"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("jsonContent", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("component_clearly_defined_full")
    op.drop_table("component_source_code_url")
    op.drop_table("component_attribution")
    op.drop_table("component_license_expression")
    op.drop_table("component")

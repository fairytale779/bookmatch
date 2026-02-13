"""create books table

Revision ID: 3a9f1bf03bfa
Revises: 
Create Date: 2026-02-14 02:09:03.885534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a9f1bf03bfa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        "books",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("contents", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("isbn", sa.Text, nullable=False),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authors", postgresql.JSONB, nullable=True),
        sa.Column("publisher", sa.Text, nullable=True),
        sa.Column("translators", postgresql.JSONB, nullable=True),
        sa.Column("price", sa.Integer, nullable=True),
        sa.Column("sale_price", sa.Integer, nullable=True),
        sa.Column("thumbnail", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("raw_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("uq_books_isbn", "books", ["isbn"], unique=True)

def downgrade():
    op.drop_index("uq_books_isbn", table_name="books")
    op.drop_table("books")

"""empty message

Revision ID: 3d7b863226e
Revises: 18d86936565
Create Date: 2015-09-21 21:13:19.322865

"""

# revision identifiers, used by Alembic.
revision = '3d7b863226e'
down_revision = '18d86936565'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('items', 'searchable')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('items', sa.Column('searchable', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False))
    ### end Alembic commands ###

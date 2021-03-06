"""empty message

Revision ID: 2f7c7f1d6ad
Revises: 3551e90bff4
Create Date: 2015-10-16 12:17:57.879649

"""

# revision identifiers, used by Alembic.
revision = '2f7c7f1d6ad'
down_revision = '3551e90bff4'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('items', sa.Column('style_id', sa.Integer(), nullable=False))
    op.drop_column('styles', 'style_id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('styles', sa.Column('style_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False))
    op.drop_column('items', 'style_id')
    ### end Alembic commands ###

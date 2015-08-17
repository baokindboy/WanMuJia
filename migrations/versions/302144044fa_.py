"""empty message

Revision ID: 302144044fa
Revises: 1c29d5476ba
Create Date: 2015-08-11 20:20:54.858343

"""

# revision identifiers, used by Alembic.
revision = '302144044fa'
down_revision = '1c29d5476ba'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vendors', sa.Column('initialized', sa.Boolean(), nullable=False))
    op.add_column('vendors', sa.Column('item_permission', sa.Boolean(), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('vendors', 'item_permission')
    op.drop_column('vendors', 'initialized')
    ### end Alembic commands ###
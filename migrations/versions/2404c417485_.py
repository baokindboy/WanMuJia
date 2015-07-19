"""empty message

Revision ID: 2404c417485
Revises: 581aad2a947
Create Date: 2015-07-19 16:33:09.850711

"""

# revision identifiers, used by Alembic.
revision = '2404c417485'
down_revision = '581aad2a947'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('items', sa.Column('is_deleted', sa.Boolean(), nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('items', 'is_deleted')
    ### end Alembic commands ###

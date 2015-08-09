"""empty message

Revision ID: 1c29d5476ba
Revises: aa3ccaf776
Create Date: 2015-08-09 22:44:56.899356

"""

# revision identifiers, used by Alembic.
revision = '1c29d5476ba'
down_revision = 'aa3ccaf776'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('distributor_revocations', sa.Column('contract', sa.String(length=255), nullable=False))
    op.drop_column('distributor_revocations', 'image')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('distributor_revocations', sa.Column('image', mysql.VARCHAR(length=255), nullable=False))
    op.drop_column('distributor_revocations', 'contract')
    ### end Alembic commands ###

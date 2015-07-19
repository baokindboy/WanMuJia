"""empty message

Revision ID: 3136e86872b
Revises: 2972fe1b853
Create Date: 2015-07-18 18:51:44.362601

"""

# revision identifiers, used by Alembic.
revision = '3136e86872b'
down_revision = '2972fe1b853'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('distributors', sa.Column('telephone', sa.String(length=30), nullable=False))
    op.drop_column('distributors', 'contact_mobile')
    op.drop_column('distributors', 'contact_telephone')
    op.add_column('vendors', sa.Column('telephone', sa.CHAR(length=15), nullable=False))
    op.drop_column('vendors', 'contact_mobile')
    op.drop_column('vendors', 'contact_telephone')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vendors', sa.Column('contact_telephone', mysql.CHAR(length=15), nullable=False))
    op.add_column('vendors', sa.Column('contact_mobile', mysql.CHAR(length=11), nullable=False))
    op.drop_column('vendors', 'telephone')
    op.add_column('distributors', sa.Column('contact_telephone', mysql.VARCHAR(length=30), nullable=False))
    op.add_column('distributors', sa.Column('contact_mobile', mysql.VARCHAR(length=30), nullable=False))
    op.drop_column('distributors', 'telephone')
    ### end Alembic commands ###
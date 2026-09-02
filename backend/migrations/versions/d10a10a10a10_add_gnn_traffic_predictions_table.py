"""add_gnn_traffic_predictions_table

Revision ID: d10a10a10a10
Revises: 9f9f9f9f9f9f
Create Date: 2026-09-02 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd10a10a10a10'
down_revision = '9f9f9f9f9f9f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create gnn_traffic_predictions table
    op.create_table(
        'gnn_traffic_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('road_id', sa.Integer(), nullable=False),
        sa.Column('prediction_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_horizon_minutes', sa.Integer(), nullable=False),
        sa.Column('predicted_speed', sa.Numeric(), nullable=False),
        sa.Column('predicted_congestion_ratio', sa.Numeric(), nullable=True),
        sa.Column('gnn_architecture', sa.String(length=50), nullable=False, server_default='GraphSAGE'),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('data_provenance_status', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['road_id'], ['roads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    # 2. Add indexes
    op.create_index(op.f('ix_gnn_traffic_predictions_id'), 'gnn_traffic_predictions', ['id'], unique=False)
    op.create_index(op.f('ix_gnn_traffic_predictions_road_id'), 'gnn_traffic_predictions', ['road_id'], unique=False)
    op.create_index(op.f('ix_gnn_traffic_predictions_prediction_time'), 'gnn_traffic_predictions', ['prediction_time'], unique=False)


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index(op.f('ix_gnn_traffic_predictions_prediction_time'), table_name='gnn_traffic_predictions')
    op.drop_index(op.f('ix_gnn_traffic_predictions_road_id'), table_name='gnn_traffic_predictions')
    op.drop_index(op.f('ix_gnn_traffic_predictions_id'), table_name='gnn_traffic_predictions')
    # 2. Drop table
    op.drop_table('gnn_traffic_predictions')

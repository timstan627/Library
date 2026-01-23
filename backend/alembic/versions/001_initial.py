"""Initial migration - Create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='student'),
        sa.Column('mfa_secret', sa.String(32), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('storage_quota_bytes', sa.BigInteger(), nullable=False, server_default='524288000'),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ban_reason', sa.String(500), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_token_hash', 'sessions', ['refresh_token_hash'])

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])

    # Resources table
    op.create_table(
        'resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('course_code', sa.String(20), nullable=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('semester', sa.String(20), nullable=True),
        sa.Column('branch', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('telegram_file_id', sa.String(200), nullable=False),
        sa.Column('telegram_message_id', sa.Integer(), nullable=False),
        sa.Column('telegram_channel_id', sa.BigInteger(), nullable=False),
        sa.Column('backup_telegram_file_id', sa.String(200), nullable=True),
        sa.Column('backup_telegram_message_id', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('file_extension', sa.String(20), nullable=False),
        sa.Column('uploader_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('downloads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating_sum', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('moderation_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('moderation_notes', sa.Text(), nullable=True),
        sa.Column('moderated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('moderated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_resources_slug', 'resources', ['slug'])
    op.create_index('ix_resources_course_code', 'resources', ['course_code'])
    op.create_index('ix_resources_file_hash', 'resources', ['file_hash'])
    op.create_index('ix_resources_uploader_id', 'resources', ['uploader_id'])
    op.create_index('ix_resources_is_deleted', 'resources', ['is_deleted'])
    op.create_index('ix_resources_search_vector', 'resources', ['search_vector'], postgresql_using='gin')

    # Ratings table
    op.create_table(
        'ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('review', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'resource_id', name='uq_user_resource_rating'),
    )
    op.create_index('ix_ratings_resource_id', 'ratings', ['resource_id'])

    # Downloads table
    op.create_table(
        'downloads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_downloads_resource_id', 'downloads', ['resource_id'])
    op.create_index('ix_downloads_created_at', 'downloads', ['created_at'])

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('resources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('moderator_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_reports_resource_id', 'reports', ['resource_id'])
    op.create_index('ix_reports_status', 'reports', ['status'])

    # Create trigger for search vector update
    op.execute("""
        CREATE OR REPLACE FUNCTION update_resource_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.course_code, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.department, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trig_update_search_vector
        BEFORE INSERT OR UPDATE OF title, description, course_code, department
        ON resources
        FOR EACH ROW
        EXECUTE FUNCTION update_resource_search_vector();
    """)


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS trig_update_search_vector ON resources')
    op.execute('DROP FUNCTION IF EXISTS update_resource_search_vector()')
    
    op.drop_table('reports')
    op.drop_table('audit_logs')
    op.drop_table('downloads')
    op.drop_table('ratings')
    op.drop_table('resources')
    op.drop_table('api_keys')
    op.drop_table('sessions')
    op.drop_table('users')

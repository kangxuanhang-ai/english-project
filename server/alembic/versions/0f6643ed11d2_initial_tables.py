"""initial tables

Revision ID: 0f6643ed11d2
Revises:
Create Date: 2026-06-08 22:01:45.302531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0f6643ed11d2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — greenfield：直接建表，不依赖旧 Prisma 表。"""
    op.create_table('user',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('phone', sa.String(), nullable=False),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('password', sa.String(), nullable=False),
    sa.Column('avatar', sa.String(), nullable=True),
    sa.Column('bio', sa.String(), nullable=True),
    sa.Column('is_timing_task', sa.Boolean(), nullable=False),
    sa.Column('timing_task_time', sa.String(), nullable=False),
    sa.Column('word_number', sa.Integer(), nullable=False),
    sa.Column('day_number', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('phone')
    )

    op.create_table('course',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('teacher', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('word_book',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('word', sa.String(), nullable=False),
    sa.Column('phonetic', sa.String(), nullable=True),
    sa.Column('definition', sa.Text(), nullable=True),
    sa.Column('translation', sa.Text(), nullable=True),
    sa.Column('pos', sa.String(), nullable=True),
    sa.Column('collins', sa.String(), nullable=True),
    sa.Column('oxford', sa.String(), nullable=True),
    sa.Column('tag', sa.String(), nullable=True),
    sa.Column('bnc', sa.String(), nullable=True),
    sa.Column('frq', sa.String(), nullable=True),
    sa.Column('exchange', sa.Text(), nullable=True),
    sa.Column('gk', sa.Boolean(), nullable=True),
    sa.Column('zk', sa.Boolean(), nullable=True),
    sa.Column('gre', sa.Boolean(), nullable=True),
    sa.Column('toefl', sa.Boolean(), nullable=True),
    sa.Column('ielts', sa.Boolean(), nullable=True),
    sa.Column('cet6', sa.Boolean(), nullable=True),
    sa.Column('cet4', sa.Boolean(), nullable=True),
    sa.Column('ky', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_word_book_word', 'word_book', ['word'], unique=False)
    op.create_index('idx_word_book_tag', 'word_book', ['tag'], unique=False)
    op.create_index('idx_word_book_word_tag', 'word_book', ['word', 'tag'], unique=False)

    op.create_table('payment_record',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('user_id', sa.String(length=30), nullable=False),
    sa.Column('trade_no', sa.String(), nullable=True),
    sa.Column('out_trade_no', sa.String(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('subject', sa.String(), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('trade_status', sa.Enum('NOT_PAY', 'WAIT_BUYER_PAY', 'TRADE_CLOSED', 'TRADE_SUCCESS', 'TRADE_FINISHED', name='tradestatus'), nullable=False),
    sa.Column('send_pay_time', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('out_trade_no')
    )

    op.create_table('visitor',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('anonymous_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(length=30), nullable=True),
    sa.Column('browser', sa.String(), nullable=True),
    sa.Column('os', sa.String(), nullable=True),
    sa.Column('device', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('anonymous_id')
    )
    op.create_index('idx_visitor_user_id', 'visitor', ['user_id'], unique=False)
    op.create_index('idx_visitor_anonymous_id', 'visitor', ['anonymous_id'], unique=False)

    op.create_table('word_book_record',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('word_id', sa.String(length=30), nullable=False),
    sa.Column('is_master', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_id', sa.String(length=30), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['word_id'], ['word_book.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'word_id', name='uq_word_book_record_user_word')
    )

    op.create_table('course_record',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('user_id', sa.String(length=30), nullable=False),
    sa.Column('course_id', sa.String(length=30), nullable=False),
    sa.Column('is_purchased', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('payment_record_id', sa.String(length=30), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['course.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['payment_record_id'], ['payment_record.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'course_id', name='uq_course_record_user_course')
    )

    op.create_table('page_view',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('visitor_id', sa.String(length=30), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('referrer', sa.String(), nullable=True),
    sa.Column('path', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['visitor_id'], ['visitor.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_page_view_visitor_created', 'page_view', ['visitor_id', 'created_at'], unique=False)
    op.create_index('idx_page_view_path_created', 'page_view', ['path', 'created_at'], unique=False)

    op.create_table('track_event',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('visitor_id', sa.String(length=30), nullable=False),
    sa.Column('event', sa.String(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['visitor_id'], ['visitor.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_track_event_visitor_created', 'track_event', ['visitor_id', 'created_at'], unique=False)
    op.create_index('idx_track_event_event_created', 'track_event', ['event', 'created_at'], unique=False)

    op.create_table('performance_entry',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('visitor_id', sa.String(length=30), nullable=False),
    sa.Column('fp', sa.Float(), nullable=True),
    sa.Column('fcp', sa.Float(), nullable=True),
    sa.Column('lcp', sa.Float(), nullable=True),
    sa.Column('inp', sa.Float(), nullable=True),
    sa.Column('cls', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['visitor_id'], ['visitor.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_performance_entry_fp_created', 'performance_entry', ['fp', 'created_at'], unique=False)
    op.create_index('idx_performance_entry_fcp_created', 'performance_entry', ['fcp', 'created_at'], unique=False)
    op.create_index('idx_performance_entry_lcp_created', 'performance_entry', ['lcp', 'created_at'], unique=False)
    op.create_index('idx_performance_entry_inp_created', 'performance_entry', ['inp', 'created_at'], unique=False)
    op.create_index('idx_performance_entry_cls_created', 'performance_entry', ['cls', 'created_at'], unique=False)
    op.create_index('idx_performance_entry_all_metrics', 'performance_entry', ['fp', 'fcp', 'lcp', 'inp', 'cls', 'created_at'], unique=False)

    op.create_table('error_entry',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('visitor_id', sa.String(length=30), nullable=False),
    sa.Column('error', sa.String(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('stack', sa.Text(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['visitor_id'], ['visitor.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_error_entry_visitor_created', 'error_entry', ['visitor_id', 'created_at'], unique=False)
    op.create_index('idx_error_entry_error_created', 'error_entry', ['error', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new tables (children first)
    op.drop_index('idx_error_entry_error_created', table_name='error_entry')
    op.drop_index('idx_error_entry_visitor_created', table_name='error_entry')
    op.drop_table('error_entry')

    op.drop_index('idx_performance_entry_all_metrics', table_name='performance_entry')
    op.drop_index('idx_performance_entry_cls_created', table_name='performance_entry')
    op.drop_index('idx_performance_entry_inp_created', table_name='performance_entry')
    op.drop_index('idx_performance_entry_lcp_created', table_name='performance_entry')
    op.drop_index('idx_performance_entry_fcp_created', table_name='performance_entry')
    op.drop_index('idx_performance_entry_fp_created', table_name='performance_entry')
    op.drop_table('performance_entry')

    op.drop_index('idx_track_event_event_created', table_name='track_event')
    op.drop_index('idx_track_event_visitor_created', table_name='track_event')
    op.drop_table('track_event')

    op.drop_index('idx_page_view_path_created', table_name='page_view')
    op.drop_index('idx_page_view_visitor_created', table_name='page_view')
    op.drop_table('page_view')

    op.drop_table('course_record')
    op.drop_table('word_book_record')

    op.drop_index('idx_visitor_anonymous_id', table_name='visitor')
    op.drop_index('idx_visitor_user_id', table_name='visitor')
    op.drop_table('visitor')

    op.drop_table('payment_record')

    op.drop_index('idx_word_book_word_tag', table_name='word_book')
    op.drop_index('idx_word_book_tag', table_name='word_book')
    op.drop_index('idx_word_book_word', table_name='word_book')
    op.drop_table('word_book')

    op.drop_table('course')
    op.drop_table('user')

"""
Database initialization script for Korean stock trading system.

This script can be used to:
1. Create all database tables
2. Run Alembic migrations
3. Seed initial data (if needed)
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.connection import engine, init_db
from shared.database.models import Base
from shared.configs.config import get_settings


def create_tables():
    """Create all database tables using SQLAlchemy."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully!")


def drop_tables():
    """Drop all database tables."""
    print("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped!")


def show_tables():
    """Show all tables in the database."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nDatabase tables ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")

    return tables


def verify_schema():
    """Verify that all expected tables exist."""
    expected_tables = [
        'stocks',
        'stock_prices',
        'technical_indicators',
        'fundamental_indicators',
        'trades',
        'portfolios',
        'watchlist'
    ]

    existing_tables = show_tables()

    print("\nSchema verification:")
    all_exist = True
    for table in expected_tables:
        exists = table in existing_tables
        status = "✓" if exists else "✗"
        print(f"  {status} {table}")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n✓ All expected tables exist!")
    else:
        print("\n✗ Some tables are missing!")

    return all_exist


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Database initialization script for Korean stock trading system'
    )
    parser.add_argument(
        'command',
        choices=['create', 'drop', 'recreate', 'show', 'verify'],
        help='Command to execute'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force execution without confirmation'
    )

    args = parser.parse_args()

    settings = get_settings()
    print(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}")
    print()

    if args.command == 'create':
        create_tables()
        verify_schema()

    elif args.command == 'drop':
        if not args.force:
            confirm = input("⚠️  This will drop all tables and data. Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Aborted.")
                return
        drop_tables()

    elif args.command == 'recreate':
        if not args.force:
            confirm = input("⚠️  This will drop and recreate all tables. All data will be lost. Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Aborted.")
                return
        drop_tables()
        create_tables()
        verify_schema()

    elif args.command == 'show':
        show_tables()

    elif args.command == 'verify':
        verify_schema()


if __name__ == '__main__':
    main()

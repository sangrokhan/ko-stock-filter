"""
Database migration script to add PortfolioRiskMetrics table.
Run this script to create the new table for risk management.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import create_engine
from shared.database.models import Base, PortfolioRiskMetrics
from shared.database.connection import get_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create PortfolioRiskMetrics table."""
    try:
        engine = get_engine()

        logger.info("Creating PortfolioRiskMetrics table...")

        # Create only the PortfolioRiskMetrics table
        PortfolioRiskMetrics.__table__.create(engine, checkfirst=True)

        logger.info("✓ PortfolioRiskMetrics table created successfully")
        logger.info("Migration completed successfully")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


def rollback_migration():
    """Drop PortfolioRiskMetrics table (use with caution)."""
    try:
        engine = get_engine()

        logger.warning("Rolling back migration - dropping PortfolioRiskMetrics table...")

        PortfolioRiskMetrics.__table__.drop(engine, checkfirst=True)

        logger.info("✓ PortfolioRiskMetrics table dropped successfully")
        logger.info("Rollback completed successfully")

        return True

    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for PortfolioRiskMetrics")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (drop table)"
    )

    args = parser.parse_args()

    if args.rollback:
        logger.warning("⚠️  WARNING: This will drop the PortfolioRiskMetrics table and all data!")
        confirm = input("Type 'yes' to confirm rollback: ")
        if confirm.lower() == 'yes':
            rollback_migration()
        else:
            logger.info("Rollback cancelled")
    else:
        run_migration()

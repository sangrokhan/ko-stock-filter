"""
Watchlist Manager Service - Main Entry Point

CLI interface for managing stock watchlists with comprehensive tracking features.
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.connection import get_db
from shared.configs.config import settings
from services.watchlist_manager.watchlist_manager import WatchlistManager
from services.stock_screener.screening_engine import ScreeningCriteria
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_watchlist(entries, show_detailed=False):
    """Print watchlist in a formatted table."""
    if not entries:
        print("\nNo stocks in watchlist.")
        return

    if show_detailed:
        # Detailed view with all metrics
        headers = [
            'Ticker', 'Name', 'Price', 'Target', 'Change%',
            'Return%', 'Score', 'Value', 'Growth', 'Quality',
            'Momentum', 'Stability', 'Days'
        ]

        rows = []
        for entry in entries:
            rows.append([
                entry['ticker'],
                entry['name'][:15] if entry['name'] else '',
                f"{entry['current_price']:.0f}" if entry['current_price'] else 'N/A',
                f"{entry['target_price']:.0f}" if entry['target_price'] else '-',
                f"{entry['price_change_pct']:.1f}%" if entry['price_change_pct'] is not None else 'N/A',
                f"{entry['total_return_pct']:.1f}%" if entry['total_return_pct'] is not None else 'N/A',
                f"{entry['composite_score']:.1f}" if entry['composite_score'] else 'N/A',
                f"{entry['value_score']:.0f}" if entry['value_score'] else '-',
                f"{entry['growth_score']:.0f}" if entry['growth_score'] else '-',
                f"{entry['quality_score']:.0f}" if entry['quality_score'] else '-',
                f"{entry['momentum_score']:.0f}" if entry['momentum_score'] else '-',
                f"{entry['stability_score']:.0f}" if entry['stability_score'] else '-',
                entry['days_on_watchlist']
            ])
    else:
        # Simple view
        headers = [
            'Ticker', 'Name', 'Price', 'Change%', 'Return%',
            'Score', 'Days', 'Reason'
        ]

        rows = []
        for entry in entries:
            rows.append([
                entry['ticker'],
                entry['name'][:20] if entry['name'] else '',
                f"{entry['current_price']:.0f}" if entry['current_price'] else 'N/A',
                f"{entry['price_change_pct']:.1f}%" if entry['price_change_pct'] is not None else 'N/A',
                f"{entry['total_return_pct']:.1f}%" if entry['total_return_pct'] is not None else 'N/A',
                f"{entry['composite_score']:.1f}" if entry['composite_score'] else 'N/A',
                entry['days_on_watchlist'],
                entry['reason'][:40] + '...' if entry['reason'] and len(entry['reason']) > 40 else (entry['reason'] or '')
            ])

    print("\n" + tabulate(rows, headers=headers, tablefmt='grid'))


def cmd_add(args, manager: WatchlistManager):
    """Add stock to watchlist."""
    result = manager.add_to_watchlist(
        ticker=args.ticker,
        target_price=args.target_price,
        custom_reason=args.reason,
        tags=args.tags,
        notes=args.notes
    )

    if result:
        print(f"\n✓ Added {args.ticker} to watchlist")
        print(f"  Reason: {result.reason}")
        if result.score:
            print(f"  Current Score: {result.score:.1f}/100")
    else:
        print(f"\n✗ Failed to add {args.ticker} to watchlist")


def cmd_list(args, manager: WatchlistManager):
    """List all watchlist stocks."""
    entries = manager.get_watchlist(
        include_inactive=args.include_inactive,
        sort_by=args.sort_by,
        ascending=args.ascending
    )

    print(f"\n{'='*80}")
    print(f"WATCHLIST - {len(entries)} stocks")
    print(f"{'='*80}")

    print_watchlist(entries, show_detailed=args.detailed)

    if args.show_summary:
        summary = manager.get_performance_summary()
        print(f"\n{'='*80}")
        print("PERFORMANCE SUMMARY")
        print(f"{'='*80}")
        print(f"Total Stocks: {summary['total_stocks']}")
        print(f"Average Return: {summary['average_return_pct']:.2f}%")
        print(f"Best Return: {summary['best_return_pct']:.2f}%")
        print(f"Worst Return: {summary['worst_return_pct']:.2f}%")
        print(f"Average Score: {summary['average_score']:.1f}/100")
        print(f"Stocks with Positive Return: {summary['stocks_with_positive_return']}")
        print(f"Stocks with Negative Return: {summary['stocks_with_negative_return']}")


def cmd_update(args, manager: WatchlistManager):
    """Update watchlist with latest data."""
    print("\nUpdating watchlist with latest scores and prices...")
    stats = manager.update_watchlist_daily()

    print(f"\n{'='*80}")
    print("UPDATE RESULTS")
    print(f"{'='*80}")
    print(f"Total Entries: {stats['total_entries']}")
    print(f"Updated: {stats['updated']}")
    print(f"Failed: {stats['failed']}")
    print(f"Removed: {stats['removed']}")

    if stats['errors']:
        print("\nErrors:")
        for error in stats['errors']:
            print(f"  - {error['ticker']}: {error['error']}")


def cmd_clean(args, manager: WatchlistManager):
    """Remove stocks not meeting criteria."""
    # Build criteria
    criteria = ScreeningCriteria(
        max_volatility_pct=args.max_volatility,
        max_per=args.max_per,
        max_pbr=args.max_pbr,
        max_debt_ratio_pct=args.max_debt_ratio,
        min_avg_volume=args.min_volume
    )

    print("\nChecking watchlist stocks against criteria...")
    print(f"  Max Volatility: {args.max_volatility}%")
    print(f"  Max PER: {args.max_per}")
    print(f"  Max PBR: {args.max_pbr}")
    print(f"  Max Debt Ratio: {args.max_debt_ratio}%")
    print(f"  Min Volume: {args.min_volume:,}")

    stats = manager.remove_stocks_not_meeting_criteria(criteria)

    print(f"\n{'='*80}")
    print("CLEANUP RESULTS")
    print(f"{'='*80}")
    print(f"Total Checked: {stats['total_checked']}")
    print(f"Removed: {stats['removed']}")
    print(f"Kept: {stats['kept']}")

    if stats['details']:
        print("\nRemoved stocks:")
        for detail in stats['details']:
            print(f"  {detail['ticker']}: {'; '.join(detail['reason'])}")


def cmd_history(args, manager: WatchlistManager):
    """Show historical performance for a stock."""
    history = manager.get_historical_performance(
        ticker=args.ticker,
        days=args.days
    )

    if not history:
        print(f"\nNo history found for {args.ticker}")
        return

    print(f"\n{'='*80}")
    print(f"HISTORICAL PERFORMANCE - {args.ticker}")
    print(f"{'='*80}")

    headers = ['Date', 'Price', 'Change%', 'Return%', 'Score', 'Criteria Met']
    rows = []

    for h in history:
        rows.append([
            h['date'][:10],
            f"{h['price']:.0f}" if h['price'] else 'N/A',
            f"{h['price_change_pct']:.1f}%" if h['price_change_pct'] is not None else 'N/A',
            f"{h['total_return_pct']:.1f}%" if h['total_return_pct'] is not None else 'N/A',
            f"{h['composite_score']:.1f}" if h['composite_score'] else 'N/A',
            'Yes' if h['meets_criteria'] else 'No'
        ])

    print("\n" + tabulate(rows, headers=headers, tablefmt='grid'))


def cmd_export(args, manager: WatchlistManager):
    """Export watchlist to file."""
    output_path = args.output or f"watchlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.format}"

    if args.format == 'csv':
        success = manager.export_to_csv(output_path)
    elif args.format == 'json':
        success = manager.export_to_json(output_path, include_history=args.include_history)
    else:
        print(f"Unsupported format: {args.format}")
        return

    if success:
        print(f"\n✓ Watchlist exported to {output_path}")
    else:
        print(f"\n✗ Failed to export watchlist")


def cmd_remove(args, manager: WatchlistManager):
    """Remove stock from watchlist."""
    success = manager.remove_from_watchlist(
        ticker=args.ticker,
        permanently=args.permanently
    )

    if success:
        action = "permanently deleted" if args.permanently else "removed"
        print(f"\n✓ {args.ticker} {action} from watchlist")
    else:
        print(f"\n✗ Failed to remove {args.ticker}")


def main():
    """Main entry point for watchlist manager CLI."""
    parser = argparse.ArgumentParser(
        description='Watchlist Manager - Track and manage stock watchlists'
    )

    parser.add_argument(
        '--user-id',
        default='default',
        help='User ID for watchlist isolation (default: default)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add stock to watchlist')
    add_parser.add_argument('ticker', help='Stock ticker code')
    add_parser.add_argument('--target-price', type=float, help='Target price')
    add_parser.add_argument('--reason', help='Custom reason for adding')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    add_parser.add_argument('--notes', help='Additional notes')

    # List command
    list_parser = subparsers.add_parser('list', help='List watchlist stocks')
    list_parser.add_argument('--include-inactive', action='store_true', help='Include inactive stocks')
    list_parser.add_argument('--sort-by', default='score',
                           choices=['score', 'added_date', 'ticker', 'price_change'],
                           help='Sort by field')
    list_parser.add_argument('--ascending', action='store_true', help='Sort in ascending order')
    list_parser.add_argument('--detailed', action='store_true', help='Show detailed view')
    list_parser.add_argument('--show-summary', action='store_true', help='Show performance summary')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update watchlist with latest data')

    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Remove stocks not meeting criteria')
    clean_parser.add_argument('--max-volatility', type=float, default=40.0,
                            help='Max volatility %% (default: 40)')
    clean_parser.add_argument('--max-per', type=float, default=50.0,
                            help='Max PER (default: 50)')
    clean_parser.add_argument('--max-pbr', type=float, default=5.0,
                            help='Max PBR (default: 5.0)')
    clean_parser.add_argument('--max-debt-ratio', type=float, default=200.0,
                            help='Max debt ratio %% (default: 200)')
    clean_parser.add_argument('--min-volume', type=int, default=100000,
                            help='Min average volume (default: 100,000)')

    # History command
    history_parser = subparsers.add_parser('history', help='Show historical performance')
    history_parser.add_argument('ticker', help='Stock ticker code')
    history_parser.add_argument('--days', type=int, help='Number of days to show')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export watchlist to file')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                             help='Export format (default: csv)')
    export_parser.add_argument('--output', help='Output file path')
    export_parser.add_argument('--include-history', action='store_true',
                             help='Include historical data (JSON only)')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove stock from watchlist')
    remove_parser.add_argument('ticker', help='Stock ticker code')
    remove_parser.add_argument('--permanently', action='store_true',
                             help='Permanently delete (vs mark inactive)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize database and manager
    db = next(get_db())
    manager = WatchlistManager(db, user_id=args.user_id)

    try:
        # Execute command
        if args.command == 'add':
            cmd_add(args, manager)
        elif args.command == 'list':
            cmd_list(args, manager)
        elif args.command == 'update':
            cmd_update(args, manager)
        elif args.command == 'clean':
            cmd_clean(args, manager)
        elif args.command == 'history':
            cmd_history(args, manager)
        elif args.command == 'export':
            cmd_export(args, manager)
        elif args.command == 'remove':
            cmd_remove(args, manager)

    except Exception as e:
        logger.error(f"Error executing command: {str(e)}", exc_info=True)
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == '__main__':
    main()

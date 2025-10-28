"""
Example usage of the Watchlist Manager.

This script demonstrates how to use the WatchlistManager programmatically.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.database.connection import get_db
from services.watchlist_manager.watchlist_manager import WatchlistManager
from services.stock_screener.screening_engine import ScreeningCriteria


def example_add_stocks():
    """Example: Add stocks to watchlist."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Adding Stocks to Watchlist")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    # Add stock with automatic reason generation
    print("\n1. Adding Samsung Electronics with auto-generated reason...")
    entry1 = manager.add_to_watchlist(
        ticker='005930',
        target_price=75000,
        tags='tech,semiconductor,bluechip'
    )

    if entry1:
        print(f"   ✓ Added {entry1.ticker}")
        print(f"   Reason: {entry1.reason}")
        print(f"   Score: {entry1.score}/100")

    # Add stock with custom reason
    print("\n2. Adding SK Hynix with custom reason...")
    entry2 = manager.add_to_watchlist(
        ticker='000660',
        target_price=130000,
        custom_reason="Strong Q4 2024 earnings, HBM3 chip momentum",
        tags='tech,semiconductor',
        notes="Monitor chip cycle recovery"
    )

    if entry2:
        print(f"   ✓ Added {entry2.ticker}")
        print(f"   Reason: {entry2.reason}")

    db.close()


def example_view_watchlist():
    """Example: View watchlist with different sorting options."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Viewing Watchlist")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    # Get watchlist sorted by score
    print("\n1. Watchlist sorted by score (highest first):")
    entries = manager.get_watchlist(sort_by='score', ascending=False)

    for i, entry in enumerate(entries[:5], 1):
        print(f"\n   {i}. {entry['ticker']} - {entry['name']}")
        print(f"      Price: {entry['current_price']:,.0f} KRW")
        print(f"      Score: {entry['composite_score']:.1f}/100")
        print(f"      Return: {entry['total_return_pct']:.2f}%" if entry['total_return_pct'] else "      Return: N/A")
        print(f"      Days on watchlist: {entry['days_on_watchlist']}")

    # Get performance summary
    print("\n2. Performance Summary:")
    summary = manager.get_performance_summary()
    print(f"   Total Stocks: {summary['total_stocks']}")
    print(f"   Average Return: {summary['average_return_pct']:.2f}%")
    print(f"   Best Performer: {summary['best_return_pct']:.2f}%")
    print(f"   Worst Performer: {summary['worst_return_pct']:.2f}%")
    print(f"   Average Score: {summary['average_score']:.1f}/100")

    db.close()


def example_update_watchlist():
    """Example: Update watchlist with latest data."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Updating Watchlist Daily")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    print("\nUpdating all watchlist stocks with latest scores and prices...")
    stats = manager.update_watchlist_daily()

    print(f"\nUpdate Results:")
    print(f"   Total Entries: {stats['total_entries']}")
    print(f"   Successfully Updated: {stats['updated']}")
    print(f"   Failed: {stats['failed']}")

    if stats['errors']:
        print("\n   Errors:")
        for error in stats['errors']:
            print(f"      - {error['ticker']}: {error['error']}")

    db.close()


def example_clean_watchlist():
    """Example: Remove stocks not meeting criteria."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Cleaning Watchlist (Remove Stocks Not Meeting Criteria)")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    # Define screening criteria
    criteria = ScreeningCriteria(
        max_volatility_pct=40.0,    # Max 40% volatility
        max_per=50.0,                # Max PER of 50
        max_pbr=5.0,                 # Max PBR of 5
        max_debt_ratio_pct=200.0,   # Max 200% debt ratio
        min_avg_volume=100000        # Min 100k daily volume
    )

    print("\nCriteria:")
    print(f"   Max Volatility: {criteria.max_volatility_pct}%")
    print(f"   Max PER: {criteria.max_per}")
    print(f"   Max PBR: {criteria.max_pbr}")
    print(f"   Max Debt Ratio: {criteria.max_debt_ratio_pct}%")
    print(f"   Min Volume: {criteria.min_avg_volume:,}")

    stats = manager.remove_stocks_not_meeting_criteria(criteria)

    print(f"\nCleanup Results:")
    print(f"   Total Checked: {stats['total_checked']}")
    print(f"   Removed: {stats['removed']}")
    print(f"   Kept: {stats['kept']}")

    if stats['details']:
        print("\n   Removed Stocks:")
        for detail in stats['details']:
            print(f"      {detail['ticker']}: {'; '.join(detail['reason'])}")

    db.close()


def example_historical_performance():
    """Example: View historical performance of a stock."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Historical Performance Tracking")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    ticker = "005930"  # Samsung Electronics
    print(f"\nHistorical performance for {ticker} (last 30 days):")

    history = manager.get_historical_performance(ticker=ticker, days=30)

    if history:
        print(f"\n   Found {len(history)} historical snapshots:\n")

        for i, snapshot in enumerate(history[:5], 1):  # Show latest 5
            print(f"   {i}. Date: {snapshot['date'][:10]}")
            print(f"      Price: {snapshot['price']:,.0f} KRW")
            if snapshot['price_change_pct'] is not None:
                change_symbol = "↑" if snapshot['price_change_pct'] > 0 else "↓"
                print(f"      Change: {change_symbol} {abs(snapshot['price_change_pct']):.2f}%")
            print(f"      Score: {snapshot['composite_score']:.1f}/100" if snapshot['composite_score'] else "      Score: N/A")
            print(f"      Meets Criteria: {'Yes' if snapshot['meets_criteria'] else 'No'}")
            print()
    else:
        print(f"   No historical data found for {ticker}")

    db.close()


def example_export_watchlist():
    """Example: Export watchlist to CSV and JSON."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Exporting Watchlist")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="example_user")

    # Export to CSV
    csv_path = "my_watchlist.csv"
    print(f"\n1. Exporting to CSV: {csv_path}")
    success = manager.export_to_csv(csv_path)

    if success:
        print(f"   ✓ Successfully exported to {csv_path}")
    else:
        print(f"   ✗ Failed to export to CSV")

    # Export to JSON
    json_path = "my_watchlist.json"
    print(f"\n2. Exporting to JSON: {json_path}")
    success = manager.export_to_json(json_path, include_history=True)

    if success:
        print(f"   ✓ Successfully exported to {json_path}")
        print(f"   (Includes historical snapshots)")
    else:
        print(f"   ✗ Failed to export to JSON")

    db.close()


def example_complete_workflow():
    """Example: Complete workflow demonstration."""
    print("\n" + "="*80)
    print("EXAMPLE 7: Complete Workflow")
    print("="*80)

    db = next(get_db())
    manager = WatchlistManager(db, user_id="workflow_demo")

    print("\nStep 1: Add stocks to watchlist")
    stocks_to_add = [
        ('005930', 75000, 'tech,bluechip'),     # Samsung
        ('000660', 130000, 'tech,semiconductor'), # SK Hynix
        ('035420', 180000, 'tech,ecommerce'),    # Naver
    ]

    for ticker, target, tags in stocks_to_add:
        entry = manager.add_to_watchlist(
            ticker=ticker,
            target_price=target,
            tags=tags
        )
        if entry:
            print(f"   ✓ Added {ticker}")

    print("\nStep 2: View current watchlist")
    entries = manager.get_watchlist()
    print(f"   Current watchlist has {len(entries)} stocks")

    print("\nStep 3: Update with latest data")
    stats = manager.update_watchlist_daily()
    print(f"   Updated {stats['updated']} stocks")

    print("\nStep 4: Export watchlist")
    manager.export_to_json("workflow_watchlist.json")
    print(f"   ✓ Exported to workflow_watchlist.json")

    print("\nStep 5: View performance summary")
    summary = manager.get_performance_summary()
    print(f"   Average Score: {summary['average_score']:.1f}/100")
    print(f"   Average Return: {summary['average_return_pct']:.2f}%")

    db.close()


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("WATCHLIST MANAGER - EXAMPLE USAGE")
    print("="*80)

    examples = [
        ("Add Stocks", example_add_stocks),
        ("View Watchlist", example_view_watchlist),
        ("Update Watchlist", example_update_watchlist),
        ("Clean Watchlist", example_clean_watchlist),
        ("Historical Performance", example_historical_performance),
        ("Export Watchlist", example_export_watchlist),
        ("Complete Workflow", example_complete_workflow),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"   {i}. {name}")

    print("\nRunning all examples...")

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n✗ Error in {name}: {str(e)}")

    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()

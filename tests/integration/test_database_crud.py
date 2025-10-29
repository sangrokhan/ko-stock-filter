"""
Database CRUD operations integration tests.

Tests Create, Read, Update, Delete operations across all database models
with proper transaction handling and constraint validation.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from shared.database.models import (
    Stock, StockPrice, TechnicalIndicator, FundamentalIndicator,
    Trade, Portfolio, Watchlist, WatchlistHistory,
    CompositeScore, StabilityScore, PortfolioRiskMetrics
)


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseCRUD:
    """Database CRUD operation tests."""

    def test_stock_crud_operations(self, integration_db_session):
        """Test CRUD operations on Stock model."""
        session = integration_db_session

        # CREATE
        stock = Stock(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            sector="전기전자",
            market_cap=400000000000000,
        )
        session.add(stock)
        session.commit()

        assert stock.id is not None
        stock_id = stock.id

        # READ
        retrieved_stock = session.query(Stock).filter(Stock.ticker == "005930").first()
        assert retrieved_stock is not None
        assert retrieved_stock.name == "삼성전자"
        assert retrieved_stock.market == "KOSPI"

        # UPDATE
        retrieved_stock.market_cap = 420000000000000
        session.commit()

        updated_stock = session.query(Stock).get(stock_id)
        assert updated_stock.market_cap == 420000000000000

        # DELETE
        session.delete(updated_stock)
        session.commit()

        deleted_stock = session.query(Stock).get(stock_id)
        assert deleted_stock is None

    def test_stock_price_crud_with_foreign_key(self, integration_db_session, sample_stocks):
        """Test StockPrice CRUD with foreign key relationships."""
        session = integration_db_session
        stock = sample_stocks[0]

        # CREATE
        price = StockPrice(
            stock_id=stock.id,
            date=datetime.now().date(),
            open=50000,
            high=51000,
            low=49500,
            close=50500,
            volume=1000000,
        )
        session.add(price)
        session.commit()

        assert price.id is not None

        # READ with relationship
        retrieved_price = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).first()
        assert retrieved_price is not None
        assert retrieved_price.stock.ticker == stock.ticker

        # UPDATE
        retrieved_price.close = 51000
        retrieved_price.volume = 1200000
        session.commit()

        updated_price = session.query(StockPrice).get(retrieved_price.id)
        assert updated_price.close == 51000
        assert updated_price.volume == 1200000

        # DELETE
        session.delete(updated_price)
        session.commit()

    def test_technical_indicator_crud(self, integration_db_session, sample_stocks):
        """Test TechnicalIndicator CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]

        # CREATE
        indicator = TechnicalIndicator(
            stock_id=stock.id,
            date=datetime.now().date(),
            rsi_14=55.5,
            rsi_9=58.2,
            macd=1.5,
            macd_signal=1.2,
            macd_histogram=0.3,
            sma_20=50000,
            sma_50=49500,
            sma_200=48000,
            ema_12=50200,
            ema_26=49800,
            bollinger_upper=52000,
            bollinger_middle=50000,
            bollinger_lower=48000,
        )
        session.add(indicator)
        session.commit()

        # READ
        retrieved = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id
        ).first()
        assert retrieved is not None
        assert retrieved.rsi_14 == 55.5
        assert retrieved.macd == 1.5

        # UPDATE
        retrieved.rsi_14 = 60.0
        retrieved.macd = 2.0
        session.commit()

        updated = session.query(TechnicalIndicator).get(retrieved.id)
        assert updated.rsi_14 == 60.0
        assert updated.macd == 2.0

    def test_fundamental_indicator_crud(self, integration_db_session, sample_stocks):
        """Test FundamentalIndicator CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]

        # CREATE
        indicator = FundamentalIndicator(
            stock_id=stock.id,
            date=datetime.now().date(),
            per=12.5,
            pbr=1.8,
            psr=2.1,
            roe=15.2,
            roa=8.5,
            debt_ratio=45.0,
            current_ratio=1.8,
            operating_margin=12.5,
            net_margin=8.3,
            revenue_growth=8.5,
            earnings_growth=12.0,
            dividend_yield=2.5,
        )
        session.add(indicator)
        session.commit()

        # READ
        retrieved = session.query(FundamentalIndicator).filter(
            FundamentalIndicator.stock_id == stock.id
        ).first()
        assert retrieved is not None
        assert retrieved.per == 12.5
        assert retrieved.roe == 15.2

        # UPDATE
        retrieved.per = 13.0
        retrieved.roe = 16.0
        session.commit()

    def test_trade_crud_operations(self, integration_db_session, sample_stocks):
        """Test Trade CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]
        user_id = "test_user_123"

        # CREATE
        trade = Trade(
            user_id=user_id,
            stock_id=stock.id,
            order_type="buy",
            order_action="market",
            quantity=100,
            price=50000,
            total_amount=5000000,
            commission=5000,
            tax=500,
            status="executed",
        )
        session.add(trade)
        session.commit()

        assert trade.id is not None

        # READ
        retrieved_trade = session.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.stock_id == stock.id
        ).first()
        assert retrieved_trade is not None
        assert retrieved_trade.order_type == "buy"
        assert retrieved_trade.quantity == 100

        # UPDATE
        retrieved_trade.status = "completed"
        session.commit()

        updated_trade = session.query(Trade).get(retrieved_trade.id)
        assert updated_trade.status == "completed"

    def test_portfolio_crud_operations(self, integration_db_session, sample_stocks):
        """Test Portfolio CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]
        user_id = "test_user_123"

        # CREATE
        position = Portfolio(
            user_id=user_id,
            stock_id=stock.id,
            quantity=100,
            average_buy_price=50000,
            current_price=55000,
            stop_loss_price=45000,
            take_profit_price=65000,
        )
        session.add(position)
        session.commit()

        assert position.id is not None

        # READ
        retrieved_position = session.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.stock_id == stock.id
        ).first()
        assert retrieved_position is not None
        assert retrieved_position.quantity == 100

        # UPDATE
        retrieved_position.quantity = 150
        retrieved_position.current_price = 56000
        session.commit()

        updated_position = session.query(Portfolio).get(retrieved_position.id)
        assert updated_position.quantity == 150
        assert updated_position.current_price == 56000

        # DELETE
        session.delete(updated_position)
        session.commit()

        deleted_position = session.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.stock_id == stock.id
        ).first()
        assert deleted_position is None

    def test_watchlist_crud_operations(self, integration_db_session, sample_stocks):
        """Test Watchlist CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]
        user_id = "test_user_123"

        # CREATE
        watchlist_item = Watchlist(
            user_id=user_id,
            stock_id=stock.id,
            target_price=60000,
            current_price=50000,
            price_change_percent=2.5,
            score=75.0,
            notes="Watching for breakout",
        )
        session.add(watchlist_item)
        session.commit()

        assert watchlist_item.id is not None

        # READ
        retrieved_item = session.query(Watchlist).filter(
            Watchlist.user_id == user_id,
            Watchlist.stock_id == stock.id
        ).first()
        assert retrieved_item is not None
        assert retrieved_item.target_price == 60000

        # UPDATE
        retrieved_item.current_price = 52000
        retrieved_item.price_change_percent = 4.0
        session.commit()

        updated_item = session.query(Watchlist).get(retrieved_item.id)
        assert updated_item.current_price == 52000

    def test_composite_score_crud(self, integration_db_session, sample_stocks):
        """Test CompositeScore CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]

        # CREATE
        score = CompositeScore(
            stock_id=stock.id,
            date=datetime.now().date(),
            value_score=75.0,
            growth_score=80.0,
            quality_score=70.0,
            momentum_score=65.0,
            composite_score=72.5,
        )
        session.add(score)
        session.commit()

        # READ
        retrieved = session.query(CompositeScore).filter(
            CompositeScore.stock_id == stock.id
        ).first()
        assert retrieved is not None
        assert retrieved.composite_score == 72.5

        # UPDATE
        retrieved.composite_score = 75.0
        session.commit()

    def test_stability_score_crud(self, integration_db_session, sample_stocks):
        """Test StabilityScore CRUD operations."""
        session = integration_db_session
        stock = sample_stocks[0]

        # CREATE
        stability = StabilityScore(
            stock_id=stock.id,
            date=datetime.now().date(),
            price_volatility=15.5,
            beta=1.2,
            volume_stability=85.0,
            earnings_consistency=75.0,
            stability_score=78.0,
        )
        session.add(stability)
        session.commit()

        # READ
        retrieved = session.query(StabilityScore).filter(
            StabilityScore.stock_id == stock.id
        ).first()
        assert retrieved is not None
        assert retrieved.stability_score == 78.0

    def test_cascade_delete(self, integration_db_session):
        """Test that deleting a stock cascades to related records."""
        session = integration_db_session

        # Create stock
        stock = Stock(
            ticker="999999",
            name="Test Stock",
            market="KOSPI",
            sector="테스트",
        )
        session.add(stock)
        session.commit()
        stock_id = stock.id

        # Create related records
        price = StockPrice(
            stock_id=stock_id,
            date=datetime.now().date(),
            open=10000,
            high=11000,
            low=9500,
            close=10500,
            volume=100000,
        )
        session.add(price)

        indicator = TechnicalIndicator(
            stock_id=stock_id,
            date=datetime.now().date(),
            rsi_14=50.0,
        )
        session.add(indicator)
        session.commit()

        # Delete stock
        session.delete(stock)
        session.commit()

        # Verify cascade delete
        price_count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock_id
        ).count()
        assert price_count == 0

        indicator_count = session.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock_id
        ).count()
        assert indicator_count == 0

    def test_unique_constraints(self, integration_db_session, sample_stocks):
        """Test unique constraint violations."""
        session = integration_db_session
        stock = sample_stocks[0]
        date = datetime.now().date()

        # Create first record
        price1 = StockPrice(
            stock_id=stock.id,
            date=date,
            open=50000,
            high=51000,
            low=49000,
            close=50500,
            volume=1000000,
        )
        session.add(price1)
        session.commit()

        # Try to create duplicate (same stock_id and date)
        price2 = StockPrice(
            stock_id=stock.id,
            date=date,
            open=51000,
            high=52000,
            low=50000,
            close=51500,
            volume=1100000,
        )
        session.add(price2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    def test_bulk_insert_operations(self, integration_db_session, sample_stocks):
        """Test bulk insert operations for performance."""
        session = integration_db_session
        stock = sample_stocks[0]

        # Bulk insert price data
        prices = []
        base_date = datetime.now().date() - timedelta(days=100)

        for day in range(100):
            price = StockPrice(
                stock_id=stock.id,
                date=base_date + timedelta(days=day),
                open=50000 + day * 100,
                high=51000 + day * 100,
                low=49000 + day * 100,
                close=50500 + day * 100,
                volume=1000000 + day * 1000,
            )
            prices.append(price)

        session.bulk_save_objects(prices)
        session.commit()

        # Verify all records were inserted
        count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).count()
        assert count >= 100

    def test_transaction_rollback(self, integration_db_session, sample_stocks):
        """Test transaction rollback on error."""
        session = integration_db_session
        stock = sample_stocks[0]

        try:
            # Create valid record
            price1 = StockPrice(
                stock_id=stock.id,
                date=datetime.now().date(),
                open=50000,
                high=51000,
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(price1)

            # Create invalid record (foreign key violation)
            price2 = StockPrice(
                stock_id=99999,  # Non-existent stock
                date=datetime.now().date(),
                open=50000,
                high=51000,
                low=49000,
                close=50500,
                volume=1000000,
            )
            session.add(price2)

            session.commit()
        except IntegrityError:
            session.rollback()

        # Verify first record was also rolled back
        count = session.query(StockPrice).filter(
            StockPrice.stock_id == stock.id,
            StockPrice.date == datetime.now().date()
        ).count()
        assert count == 0

    def test_complex_query_operations(self, integration_db_session, sample_stocks, sample_stock_prices):
        """Test complex queries with joins and aggregations."""
        session = integration_db_session

        # Query with join
        results = session.query(Stock, StockPrice).join(
            StockPrice, Stock.id == StockPrice.stock_id
        ).filter(
            Stock.market == "KOSPI"
        ).limit(10).all()

        assert len(results) > 0

        # Aggregation query
        from sqlalchemy import func

        avg_volume = session.query(func.avg(StockPrice.volume)).filter(
            StockPrice.stock_id == sample_stocks[0].id
        ).scalar()

        assert avg_volume is not None
        assert avg_volume > 0

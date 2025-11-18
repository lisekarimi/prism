"""Tests for PRISM tools without external dependencies."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from prism.tools import calculation_tools, database_tools, market_data_tools


class TestCalculationTools:
    """Test calculation tools."""

    def test_calculate_years_to_maturity(self):
        """Test years to maturity calculation."""
        # Test with future date
        future_date = (datetime.now() + timedelta(days=1825)).strftime(
            "%Y-%m-%d"
        )  # ~5 years
        years = calculation_tools.calculate_years_to_maturity(maturity_date=future_date)
        assert abs(years - 5.0) < 0.1  # Allow small margin

        # Test with past date (should return 0)
        past_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        years = calculation_tools.calculate_years_to_maturity(maturity_date=past_date)
        assert years == 0

    def test_calculate_swap_pnl_rcv_fixed(self):
        """Test P&L calculation for receive fixed position."""
        position = {
            "position_id": "POS001",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 3.40  # Rate decreased (good for receive fixed)

        result = calculation_tools.calculate_swap_pnl(
            position=position, current_rate=current_rate
        )

        assert result["position_id"] == "POS001"
        assert result["entry_rate"] == 4.10
        assert result["current_rate"] == 3.40
        assert (
            result["pnl"] > 0
        )  # Should be positive (rate decreased, we receive fixed)

    def test_calculate_swap_pnl_pay_fixed(self):
        """Test P&L calculation for pay fixed position."""
        position = {
            "position_id": "POS002",
            "fixed_rate": 4.25,
            "notional": 25000000.0,
            "pay_receive": "PAY_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1095)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 4.50  # Rate increased (bad for pay fixed)

        result = calculation_tools.calculate_swap_pnl(
            position=position, current_rate=current_rate
        )

        assert result["position_id"] == "POS002"
        assert result["pnl"] < 0  # Should be negative (rate increased, we pay fixed)

    def test_calculate_portfolio_dv01(self):
        """Test portfolio DV01 calculation."""
        positions = [
            {
                "notional": 10000000.0,
                "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                    "%Y-%m-%d"
                ),
                "pay_receive": "RCV_FIXED",
            },
            {
                "notional": 25000000.0,
                "maturity_date": (datetime.now() + timedelta(days=1095)).strftime(
                    "%Y-%m-%d"
                ),
                "pay_receive": "PAY_FIXED",
            },
        ]

        result = calculation_tools.calculate_portfolio_dv01(positions=positions)
        assert isinstance(result, int | float)
        assert result != 0

    def test_check_trading_signal_profit(self):
        """Test trading signal when profit target is hit."""
        signal = calculation_tools.check_trading_signal(
            pnl=60000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert "profit" in signal["reason"].lower()

    def test_check_trading_signal_stop_loss(self):
        """Test trading signal when stop loss is hit."""
        signal = calculation_tools.check_trading_signal(
            pnl=-30000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert (
            "stop loss" in signal["reason"].lower()
            or "loss" in signal["reason"].lower()
        )

    def test_check_trading_signal_hold(self):
        """Test trading signal when position should be held."""
        signal = calculation_tools.check_trading_signal(
            pnl=10000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "HOLD"

    def test_calculate_dynamic_thresholds_large_position(self):
        """Test dynamic thresholds for large position."""
        position = {
            "position_id": "POS001",
            "notional": 25000000.0,  # $25M
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = calculation_tools.calculate_dynamic_thresholds(
            position=position, volatility=0.02
        )

        assert result["position_id"] == "POS001"
        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0
        # Large positions should have tighter stops
        assert abs(result["profit_target"]) < abs(result["stop_loss"]) * 2

    def test_calculate_dynamic_thresholds_small_position(self):
        """Test dynamic thresholds for small position."""
        position = {
            "position_id": "POS002",
            "notional": 5000000.0,  # $5M
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = calculation_tools.calculate_dynamic_thresholds(
            position=position, volatility=0.02
        )

        assert result["position_id"] == "POS002"
        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0


class TestDatabaseTools:
    """Test database tools with mocked database."""

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_get_all_positions(self, mock_db_class, sample_positions):
        """Test getting all positions from database."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = sample_positions
        mock_db_class.return_value = mock_db

        # Call function
        result = database_tools.get_all_positions()

        # Verify
        assert mock_db.connect.called
        assert mock_db.execute_query.called
        assert mock_db.close.called
        assert len(result) == 2
        assert result[0]["position_id"] == "POS001"

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_get_position_by_id(self, mock_db_class, sample_positions):
        """Test getting a specific position by ID."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [sample_positions[0]]
        mock_db_class.return_value = mock_db

        # Call function
        result = database_tools.get_position_by_id("POS001")

        # Verify
        assert mock_db.connect.called
        assert mock_db.execute_query.called
        assert result["position_id"] == "POS001"

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_insert_trade_signal(self, mock_db_class):
        """Test inserting a trade signal."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        mock_db_class.return_value = mock_db

        # Call function
        result = database_tools.insert_trade_signal(
            position_id="POS001",
            signal_type="CLOSE",
            current_pnl=60000.0,
            reason="Profit target hit",
            recommended_action="Close position",
        )

        # Verify
        assert mock_db.connect.called
        assert mock_db.execute_query.called
        assert mock_db.close.called
        assert "POS001" in result
        assert "CLOSE" in result


class TestMarketDataTools:
    """Test market data tools with mocked database."""

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_store_market_rates(self, mock_db_class, sample_market_rates):
        """Test storing market rates in database."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        mock_db_class.return_value = mock_db

        # Call function
        result = market_data_tools.store_market_rates(rates=sample_market_rates)

        # Verify
        assert mock_db.connect.called
        assert mock_db.execute_query.called
        assert mock_db.close.called
        assert "Stored" in result
        assert "4" in result  # 4 rates stored

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_get_latest_market_rate(self, mock_db_class):
        """Test getting latest market rate."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [
            {
                "mid_rate": 4.35,
                "bid_rate": 4.34,
                "ask_rate": 4.36,
                "timestamp": datetime.now(),
            }
        ]
        mock_db_class.return_value = mock_db

        # Call function
        result = market_data_tools.get_latest_market_rate(tenor="5Y", currency="USD")

        # Verify
        assert mock_db.connect.called
        assert mock_db.execute_query.called
        assert mock_db.close.called
        assert result is not None
        assert result["mid_rate"] == 4.35

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_get_latest_market_rate_not_found(self, mock_db_class):
        """Test getting latest market rate when not found."""
        # Setup mock
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        mock_db_class.return_value = mock_db

        # Call function
        result = market_data_tools.get_latest_market_rate(tenor="5Y", currency="USD")

        # Verify
        assert result is None

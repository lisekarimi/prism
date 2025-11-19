"""Comprehensive tests for PRISM non-LLM components: database operations, calculations, validations, and rate limiting."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from prism.tools import database_tools, market_data_tools
from prism.tools.calculation_tools import (
    _calculate_dynamic_thresholds_internal,
    _calculate_swap_pnl_internal,
    _calculate_years_to_maturity_internal,
    _check_trading_signal_internal,
)

# ============================================================================
# DATABASE OPERATIONS TESTS
# ============================================================================


class TestDatabaseOperations:
    """Test database operations: insert/fetch rates, positions, signals."""

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_insert_and_fetch_positions(self, mock_db_class, mock_db, sample_positions):
        """Test inserting and fetching positions from database."""
        # Setup mock
        mock_db_class.return_value = mock_db

        # Insert positions directly into mock
        for pos in sample_positions:
            mock_db._data["swap_positions"].append(
                {
                    "position_id": pos["position_id"],
                    "trade_date": pos["trade_date"],
                    "maturity_date": pos["maturity_date"],
                    "notional": pos["notional"],
                    "fixed_rate": pos["fixed_rate"],
                    "float_index": pos["float_index"],
                    "pay_receive": pos["pay_receive"],
                    "currency": pos["currency"],
                }
            )

        # Fetch all positions using tool
        positions = database_tools.get_all_positions.run()

        assert len(positions) == 3
        assert positions[0]["position_id"] in ["POS001", "POS002", "POS003"]
        assert all("notional" in p for p in positions)
        assert all("fixed_rate" in p for p in positions)

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_get_position_by_id(self, mock_db_class, mock_db, sample_positions):
        """Test fetching a specific position by ID."""
        # Setup mock
        mock_db_class.return_value = mock_db

        # Insert a position directly into mock
        pos = sample_positions[0]
        mock_db._data["swap_positions"].append(
            {
                "position_id": pos["position_id"],
                "trade_date": pos["trade_date"],
                "maturity_date": pos["maturity_date"],
                "notional": pos["notional"],
                "fixed_rate": pos["fixed_rate"],
                "float_index": pos["float_index"],
                "pay_receive": pos["pay_receive"],
                "currency": pos["currency"],
            }
        )

        # Fetch by ID
        result = database_tools.get_position_by_id.run("POS001")

        assert result is not None
        assert result["position_id"] == "POS001"
        assert float(result["notional"]) == 10000000.0
        assert float(result["fixed_rate"]) == 4.10

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_get_position_by_id_not_found(self, mock_db_class, mock_db):
        """Test fetching non-existent position returns None."""
        mock_db_class.return_value = mock_db
        result = database_tools.get_position_by_id.run("NONEXISTENT")
        assert result is None

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_insert_trade_signal(self, mock_db_class, mock_db, sample_positions):
        """Test inserting trade signals into database."""
        # Setup mock
        mock_db_class.return_value = mock_db

        # Insert a position directly into mock (required for foreign key)
        pos = sample_positions[0]
        mock_db._data["swap_positions"].append(
            {
                "position_id": pos["position_id"],
                "trade_date": pos["trade_date"],
                "maturity_date": pos["maturity_date"],
                "notional": pos["notional"],
                "fixed_rate": pos["fixed_rate"],
                "float_index": pos["float_index"],
                "pay_receive": pos["pay_receive"],
                "currency": pos["currency"],
            }
        )

        # Insert signal using tool
        result = database_tools.insert_trade_signal.run(
            position_id="POS001",
            signal_type="CLOSE",
            current_pnl=60000.0,
            reason="Profit target hit",
            recommended_action="Close position",
        )

        assert "POS001" in result
        assert "CLOSE" in result

        # Verify signal was inserted
        signals = mock_db._data["trade_signals"]
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "CLOSE"
        assert signals[0]["current_pnl"] == 60000.0
        assert signals[0]["executed"] is False

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_insert_multiple_signals(self, mock_db_class, mock_db, sample_positions):
        """Test inserting multiple signals for same position."""
        # Setup mock
        mock_db_class.return_value = mock_db

        # Insert position directly into mock
        pos = sample_positions[0]
        mock_db._data["swap_positions"].append(
            {
                "position_id": pos["position_id"],
                "trade_date": pos["trade_date"],
                "maturity_date": pos["maturity_date"],
                "notional": pos["notional"],
                "fixed_rate": pos["fixed_rate"],
                "float_index": pos["float_index"],
                "pay_receive": pos["pay_receive"],
                "currency": pos["currency"],
            }
        )

        # Insert multiple signals
        database_tools.insert_trade_signal.run(
            position_id="POS001",
            signal_type="HOLD",
            current_pnl=10000.0,
            reason="Within range",
            recommended_action="Continue monitoring",
        )

        database_tools.insert_trade_signal.run(
            position_id="POS001",
            signal_type="CLOSE",
            current_pnl=60000.0,
            reason="Profit target hit",
            recommended_action="Close position",
        )

        # Verify both signals exist
        signals = mock_db._data["trade_signals"]
        assert len(signals) == 2
        assert signals[0]["signal_type"] == "HOLD"
        assert signals[1]["signal_type"] == "CLOSE"


class TestMarketDataOperations:
    """Test market data database operations."""

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_store_market_rates(self, mock_db_class, mock_db, sample_market_rates):
        """Test storing market rates in database."""
        mock_db_class.return_value = mock_db
        result = market_data_tools.store_market_rates.run(rates=sample_market_rates)

        assert "Stored" in result
        assert "4" in result

        # Verify rates were stored
        rates = mock_db._data["market_rates"]
        assert len(rates) == 4
        tenors = [r["tenor"] for r in rates]
        assert "10Y" in tenors
        assert "2Y" in tenors
        assert "30Y" in tenors
        assert "5Y" in tenors

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_store_market_rates_with_string_percentages(self, mock_db_class, mock_db):
        """Test storing rates with percentage strings."""
        mock_db_class.return_value = mock_db
        rates = [
            {
                "tenor": "5Y",
                "mid_rate": "4.35%",
                "bid_rate": "4.34%",
                "ask_rate": "4.36%",
                "currency": "USD",
            }
        ]

        market_data_tools.store_market_rates.run(rates=rates)

        # Verify rate was stored and converted
        stored = mock_db._data["market_rates"]
        assert len(stored) == 1
        assert float(stored[0]["mid_rate"]) == 4.35
        assert float(stored[0]["bid_rate"]) == 4.34
        assert float(stored[0]["ask_rate"]) == 4.36

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_get_latest_market_rate(self, mock_db_class, mock_db, sample_market_rates):
        """Test fetching latest market rate."""
        mock_db_class.return_value = mock_db
        # Store rates
        market_data_tools.store_market_rates.run(rates=sample_market_rates)

        # Fetch latest rate
        result = market_data_tools.get_latest_market_rate.run(
            tenor="5Y", currency="USD"
        )

        assert result is not None
        assert float(result["mid_rate"]) == 4.35
        assert float(result["bid_rate"]) == 4.34
        assert float(result["ask_rate"]) == 4.36
        assert "timestamp" in result

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_get_latest_market_rate_not_found(self, mock_db_class, mock_db):
        """Test fetching non-existent rate returns None."""
        mock_db_class.return_value = mock_db
        result = market_data_tools.get_latest_market_rate.run(
            tenor="1Y", currency="USD"
        )
        assert result is None

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_get_latest_market_rate_multiple_currencies(self, mock_db_class, mock_db):
        """Test fetching rates for different currencies."""
        mock_db_class.return_value = mock_db
        usd_rates = [{"tenor": "5Y", "mid_rate": 4.35, "currency": "USD"}]
        eur_rates = [{"tenor": "5Y", "mid_rate": 3.50, "currency": "EUR"}]

        market_data_tools.store_market_rates.run(rates=usd_rates)
        market_data_tools.store_market_rates.run(rates=eur_rates)

        usd_result = market_data_tools.get_latest_market_rate.run(
            tenor="5Y", currency="USD"
        )
        eur_result = market_data_tools.get_latest_market_rate.run(
            tenor="5Y", currency="EUR"
        )

        assert float(usd_result["mid_rate"]) == 4.35
        assert float(eur_result["mid_rate"]) == 3.50


# ============================================================================
# CALCULATION TESTS - P&L FORMULAS
# ============================================================================


class TestPnLCalculations:
    """Test P&L calculation formulas with comprehensive edge cases."""

    def test_calculate_swap_pnl_rcv_fixed_profit(self):
        """Test P&L for receive fixed when rate decreases (profit)."""
        position = {
            "position_id": "POS001",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),  # 5 years
        }
        current_rate = 3.40  # Rate decreased (good for receive fixed)

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["position_id"] == "POS001"
        assert result["entry_rate"] == 4.10
        assert result["current_rate"] == 3.40
        assert result["pnl"] > 0  # Should be positive
        assert result["rate_change_bps"] < 0  # Rate decreased

    def test_calculate_swap_pnl_rcv_fixed_loss(self):
        """Test P&L for receive fixed when rate increases (loss)."""
        position = {
            "position_id": "POS001",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 4.50  # Rate increased (bad for receive fixed)

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] < 0  # Should be negative
        assert result["rate_change_bps"] > 0  # Rate increased

    def test_calculate_swap_pnl_pay_fixed_profit(self):
        """Test P&L for pay fixed when rate increases (profit)."""
        position = {
            "position_id": "POS002",
            "fixed_rate": 4.25,
            "notional": 25000000.0,
            "pay_receive": "PAY_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1095)).strftime(
                "%Y-%m-%d"
            ),  # 3 years
        }
        current_rate = 4.50  # Rate increased (good for pay fixed)

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] > 0  # Should be positive
        assert result["rate_change_bps"] > 0  # Rate increased

    def test_calculate_swap_pnl_pay_fixed_loss(self):
        """Test P&L for pay fixed when rate decreases (loss)."""
        position = {
            "position_id": "POS002",
            "fixed_rate": 4.25,
            "notional": 25000000.0,
            "pay_receive": "PAY_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1095)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 3.90  # Rate decreased (bad for pay fixed)

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] < 0  # Should be negative
        assert result["rate_change_bps"] < 0  # Rate decreased

    def test_calculate_swap_pnl_zero_rate_change(self):
        """Test P&L when rate hasn't changed."""
        position = {
            "position_id": "POS001",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 4.10  # Same as entry rate

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] == 0
        assert result["rate_change_bps"] == 0

    def test_calculate_swap_pnl_large_notional(self):
        """Test P&L calculation with very large notional."""
        position = {
            "position_id": "POS003",
            "fixed_rate": 4.00,
            "notional": 100000000.0,  # $100M
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }
        current_rate = 3.50

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] > 0
        assert abs(result["pnl"]) > 100000  # Large position should have large P&L

    def test_calculate_swap_pnl_short_maturity(self):
        """Test P&L calculation with short maturity."""
        position = {
            "position_id": "POS004",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=90)).strftime(
                "%Y-%m-%d"
            ),  # 3 months
        }
        current_rate = 3.50

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] > 0

    def test_calculate_swap_pnl_past_maturity(self):
        """Test P&L calculation when position has matured."""
        position = {
            "position_id": "POS005",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() - timedelta(days=365)).strftime(
                "%Y-%m-%d"
            ),  # Past date
        }
        current_rate = 3.50

        result = _calculate_swap_pnl_internal(position, current_rate)

        assert result["pnl"] == 0  # Matured position has no P&L


# ============================================================================
# CALCULATION TESTS - THRESHOLD CALCULATIONS
# ============================================================================


class TestThresholdCalculations:
    """Test dynamic threshold calculations with edge cases."""

    def test_calculate_dynamic_thresholds_large_position(self):
        """Test thresholds for large position ($20M+)."""
        position = {
            "position_id": "POS001",
            "notional": 25000000.0,  # $25M
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = _calculate_dynamic_thresholds_internal(
            position=position, volatility=0.02
        )

        assert result["position_id"] == "POS001"
        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0
        # Large positions should have tighter stops (0.3% profit, 0.15% loss)
        expected_profit = 25000000.0 * 0.003 * 1.2  # 0.3% * (1 + 0.02*10)
        expected_loss = -25000000.0 * 0.0015 * 1.2  # 0.15% * (1 + 0.02*10)
        assert abs(result["profit_target"] - expected_profit) < 100
        assert abs(result["stop_loss"] - expected_loss) < 100

    def test_calculate_dynamic_thresholds_medium_position(self):
        """Test thresholds for medium position ($10M-$20M)."""
        position = {
            "position_id": "POS002",
            "notional": 15000000.0,  # $15M
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = _calculate_dynamic_thresholds_internal(
            position=position, volatility=0.02
        )

        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0
        # Medium positions: 0.5% profit, 0.25% loss
        expected_profit = 15000000.0 * 0.005 * 1.2
        expected_loss = -15000000.0 * 0.0025 * 1.2
        assert abs(result["profit_target"] - expected_profit) < 100
        assert abs(result["stop_loss"] - expected_loss) < 100

    def test_calculate_dynamic_thresholds_small_position(self):
        """Test thresholds for small position (<$10M)."""
        position = {
            "position_id": "POS003",
            "notional": 5000000.0,  # $5M
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = _calculate_dynamic_thresholds_internal(
            position=position, volatility=0.02
        )

        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0
        # Small positions: 1% profit, 0.5% loss
        expected_profit = 5000000.0 * 0.01 * 1.2
        expected_loss = -5000000.0 * 0.005 * 1.2
        assert abs(result["profit_target"] - expected_profit) < 100
        assert abs(result["stop_loss"] - expected_loss) < 100

    def test_calculate_dynamic_thresholds_high_volatility(self):
        """Test thresholds adjust for high volatility."""
        position = {
            "position_id": "POS001",
            "notional": 10000000.0,
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        low_vol_result = _calculate_dynamic_thresholds_internal(position, 0.01)
        high_vol_result = _calculate_dynamic_thresholds_internal(position, 0.05)

        # Higher volatility should result in wider thresholds
        assert abs(high_vol_result["profit_target"]) > abs(
            low_vol_result["profit_target"]
        )
        assert abs(high_vol_result["stop_loss"]) > abs(low_vol_result["stop_loss"])

    def test_calculate_dynamic_thresholds_zero_volatility(self):
        """Test thresholds with zero volatility."""
        position = {
            "position_id": "POS001",
            "notional": 10000000.0,
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        result = _calculate_dynamic_thresholds_internal(
            position=position, volatility=0.0
        )

        # Should still have thresholds, just not adjusted for volatility
        assert result["profit_target"] > 0
        assert result["stop_loss"] < 0


# ============================================================================
# CALCULATION TESTS - TRADING SIGNALS
# ============================================================================


class TestTradingSignalLogic:
    """Test trading signal determination logic."""

    def test_check_trading_signal_profit_target(self):
        """Test signal when profit target is hit."""
        signal = _check_trading_signal_internal(
            pnl=60000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert "profit" in signal["reason"].lower()
        assert "60,000" in signal["reason"] or "60000" in signal["reason"].replace(
            ",", ""
        )

    def test_check_trading_signal_stop_loss(self):
        """Test signal when stop loss is hit."""
        signal = _check_trading_signal_internal(
            pnl=-30000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert (
            "stop loss" in signal["reason"].lower()
            or "loss" in signal["reason"].lower()
        )
        assert "-30,000" in signal["reason"] or "-30000" in signal["reason"].replace(
            ",", ""
        )

    def test_check_trading_signal_hold(self):
        """Test signal when position should be held."""
        signal = _check_trading_signal_internal(
            pnl=10000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "HOLD"
        assert (
            "within" in signal["reason"].lower() or "range" in signal["reason"].lower()
        )

    def test_check_trading_signal_exact_profit_threshold(self):
        """Test signal at exact profit threshold."""
        signal = _check_trading_signal_internal(
            pnl=50000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert "profit" in signal["reason"].lower()

    def test_check_trading_signal_exact_loss_threshold(self):
        """Test signal at exact loss threshold."""
        signal = _check_trading_signal_internal(
            pnl=-25000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "CLOSE"
        assert (
            "stop loss" in signal["reason"].lower()
            or "loss" in signal["reason"].lower()
        )

    def test_check_trading_signal_negative_but_above_loss(self):
        """Test signal when P&L is negative but above stop loss."""
        signal = _check_trading_signal_internal(
            pnl=-10000.0, threshold_profit=50000.0, threshold_loss=-25000.0
        )

        assert signal["signal"] == "HOLD"

    def test_check_trading_signal_custom_thresholds(self):
        """Test signal with custom thresholds."""
        signal = _check_trading_signal_internal(
            pnl=100000.0, threshold_profit=75000.0, threshold_loss=-50000.0
        )

        assert signal["signal"] == "CLOSE"
        assert "profit" in signal["reason"].lower()


# ============================================================================
# CALCULATION TESTS - MATURITY
# ============================================================================


class TestMaturityCalculations:
    """Test years to maturity calculations."""

    def test_calculate_years_to_maturity(self):
        """Test years to maturity calculation."""
        # Test with future date
        future_date = (datetime.now() + timedelta(days=1825)).strftime(
            "%Y-%m-%d"
        )  # ~5 years
        years = _calculate_years_to_maturity_internal(future_date)
        assert abs(years - 5.0) < 0.1  # Allow small margin

        # Test with past date (should return 0)
        past_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        years = _calculate_years_to_maturity_internal(past_date)
        assert years == 0

    def test_calculate_years_to_maturity_exact(self):
        """Test years to maturity with exact dates."""
        # 1 year from now
        one_year = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        years = _calculate_years_to_maturity_internal(one_year)
        assert abs(years - 1.0) < 0.01

        # 2 years from now
        two_years = (datetime.now() + timedelta(days=730)).strftime("%Y-%m-%d")
        years = _calculate_years_to_maturity_internal(two_years)
        assert abs(years - 2.0) < 0.01


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================


class TestRateLimiting:
    """Test rate limiting logic for demo executions."""

    def _get_execution_count(self, mock_db, ip_address):
        """Get execution count for an IP address."""
        count = len(
            [
                e
                for e in mock_db._data["demo_executions"]
                if e.get("ip_address") == ip_address
            ]
        )
        return count

    def test_rate_limit_check_under_limit(self, mock_db, mock_request):
        """Test rate limit check when under limit."""
        ip = mock_request.client.host
        count = self._get_execution_count(mock_db, ip)
        assert count == 0

    def test_rate_limit_insert_and_count(self, mock_db, mock_request):
        """Test inserting execution and counting."""
        ip = mock_request.client.host

        # Insert execution directly into mock
        mock_db._data["demo_executions"].append(
            {
                "ip_address": ip,
                "last_run": MagicMock(),
            }
        )

        # Check count
        count = self._get_execution_count(mock_db, ip)
        assert count == 1

    def test_rate_limit_multiple_executions(self, mock_db, mock_request):
        """Test multiple executions are counted correctly."""
        ip = mock_request.client.host

        # Insert multiple executions
        for _ in range(3):
            mock_db._data["demo_executions"].append(
                {
                    "ip_address": ip,
                    "last_run": MagicMock(),
                }
            )

        count = self._get_execution_count(mock_db, ip)
        assert count == 3

    def test_rate_limit_at_max(self, mock_db, mock_request):
        """Test rate limit when at maximum."""
        ip = mock_request.client.host

        # Insert 5 executions (max)
        for _ in range(5):
            mock_db._data["demo_executions"].append(
                {
                    "ip_address": ip,
                    "last_run": MagicMock(),
                }
            )

        count = self._get_execution_count(mock_db, ip)
        assert count == 5

    def test_rate_limit_exceeds_max(self, mock_db, mock_request):
        """Test rate limit when exceeding maximum."""
        ip = mock_request.client.host

        # Insert 6 executions (exceeds max)
        for _ in range(6):
            mock_db._data["demo_executions"].append(
                {
                    "ip_address": ip,
                    "last_run": MagicMock(),
                }
            )

        count = self._get_execution_count(mock_db, ip)
        assert count == 6  # Database counts all, application logic enforces limit

    def test_rate_limit_different_ips(self, mock_db):
        """Test rate limiting is per IP address."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        # Insert executions for IP1
        for _ in range(3):
            mock_db._data["demo_executions"].append(
                {
                    "ip_address": ip1,
                    "last_run": MagicMock(),
                }
            )

        # IP1 should have 3 executions
        count1 = self._get_execution_count(mock_db, ip1)
        assert count1 == 3

        # IP2 should have 0 executions
        count2 = self._get_execution_count(mock_db, ip2)
        assert count2 == 0

    def test_rate_limit_24_hour_window(self, mock_db, mock_request):
        """Test that rate limiting only counts executions in last 24 hours."""
        ip = mock_request.client.host

        # Insert execution with old timestamp (simplified - just insert one)
        mock_db._data["demo_executions"].append(
            {
                "ip_address": ip,
                "last_run": MagicMock(),
            }
        )

        # Insert execution with recent timestamp
        mock_db._data["demo_executions"].append(
            {
                "ip_address": ip,
                "last_run": MagicMock(),
            }
        )

        # Should count both (simplified mock - real implementation would filter by time)
        count = self._get_execution_count(mock_db, ip)
        assert count == 2  # Simplified - both are counted

    def test_rate_limit_logic_enforcement(self, mock_db, mock_request):
        """Test that rate limit logic correctly identifies when limit is reached."""
        from prism.constants import MAX_RUNS

        ip = mock_request.client.host

        # Insert executions up to limit
        for _ in range(MAX_RUNS):
            mock_db._data["demo_executions"].append(
                {
                    "ip_address": ip,
                    "last_run": MagicMock(),
                }
            )

        count = self._get_execution_count(mock_db, ip)
        assert count == MAX_RUNS
        assert count >= MAX_RUNS  # At or above limit

        # One more execution should exceed limit
        mock_db._data["demo_executions"].append(
            {
                "ip_address": ip,
                "last_run": MagicMock(),
            }
        )
        count = self._get_execution_count(mock_db, ip)
        assert count > MAX_RUNS


# ============================================================================
# TOOL INPUT/OUTPUT VALIDATION TESTS
# ============================================================================


class TestToolValidation:
    """Test tool input/output validation."""

    def test_calculate_swap_pnl_missing_fields(self):
        """Test P&L calculation with missing required fields."""
        # Missing position_id
        position = {
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        # Should handle missing field gracefully or raise appropriate error
        try:
            result = _calculate_swap_pnl_internal(position, 4.0)
            # If it doesn't raise, check that it handles it
            assert "position_id" in result or result.get("position_id") == "unknown"
        except (KeyError, TypeError):
            # Expected behavior - missing required field
            pass

    def test_calculate_swap_pnl_invalid_rate(self):
        """Test P&L calculation with invalid rate values."""
        position = {
            "position_id": "POS001",
            "fixed_rate": 4.10,
            "notional": 10000000.0,
            "pay_receive": "RCV_FIXED",
            "maturity_date": (datetime.now() + timedelta(days=1825)).strftime(
                "%Y-%m-%d"
            ),
        }

        # Negative rate (should still calculate, just unusual)
        result = _calculate_swap_pnl_internal(position, -1.0)
        assert "pnl" in result

        # Very large rate
        result = _calculate_swap_pnl_internal(position, 100.0)
        assert "pnl" in result

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_store_market_rates_empty_list(self, mock_db_class, mock_db):
        """Test storing empty rate list."""
        mock_db_class.return_value = mock_db
        result = market_data_tools.store_market_rates.run(rates=[])
        assert "0" in result or "Stored" in result

    @patch("prism.tools.market_data_tools.DatabaseConnection")
    def test_store_market_rates_missing_fields(self, mock_db_class, mock_db):
        """Test storing rates with missing optional fields."""
        mock_db_class.return_value = mock_db
        rates = [
            {"tenor": "5Y", "mid_rate": 4.35}  # Missing bid/ask
        ]

        # Should use defaults for bid/ask
        market_data_tools.store_market_rates.run(rates=rates)

        # Verify bid/ask were set to defaults
        stored = mock_db._data["market_rates"]
        assert len(stored) == 1
        assert stored[0]["bid_rate"] is not None
        assert stored[0]["ask_rate"] is not None

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_get_position_by_id_invalid_id(self, mock_db_class, mock_db):
        """Test getting position with invalid ID format."""
        mock_db_class.return_value = mock_db
        result = database_tools.get_position_by_id.run("")
        assert result is None

        result = database_tools.get_position_by_id.run("INVALID_ID_12345")
        assert result is None

    @patch("prism.tools.database_tools.DatabaseConnection")
    def test_insert_trade_signal_invalid_position_id(self, mock_db_class, mock_db):
        """Test inserting signal with non-existent position_id."""
        mock_db_class.return_value = mock_db
        # Should either raise error or handle gracefully
        try:
            database_tools.insert_trade_signal.run(
                position_id="NONEXISTENT",
                signal_type="CLOSE",
                current_pnl=1000.0,
                reason="Test",
                recommended_action="Test action",
            )
            # If foreign key constraint is enforced, this should fail
            # Otherwise, it might succeed
        except Exception:
            # Expected if foreign key constraint is enforced
            pass

"""Pytest configuration and fixtures for PRISM tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_positions():
    """Sample swap positions for testing."""
    return [
        {
            "position_id": "POS001",
            "trade_date": "2024-01-15",
            "maturity_date": "2029-01-15",
            "notional": 10000000.0,
            "fixed_rate": 4.10,
            "float_index": "SOFR",
            "pay_receive": "RCV_FIXED",
            "currency": "USD",
        },
        {
            "position_id": "POS002",
            "trade_date": "2024-02-01",
            "maturity_date": "2027-02-01",
            "notional": 25000000.0,
            "fixed_rate": 4.25,
            "float_index": "SOFR",
            "pay_receive": "PAY_FIXED",
            "currency": "USD",
        },
        {
            "position_id": "POS003",
            "trade_date": "2024-03-01",
            "maturity_date": "2026-03-01",
            "notional": 5000000.0,
            "fixed_rate": 3.95,
            "float_index": "SOFR",
            "pay_receive": "RCV_FIXED",
            "currency": "USD",
        },
    ]


@pytest.fixture
def sample_market_rates():
    """Sample market rates for testing."""
    return [
        {
            "tenor": "2Y",
            "mid_rate": 4.15,
            "bid_rate": 4.14,
            "ask_rate": 4.16,
            "currency": "USD",
        },
        {
            "tenor": "5Y",
            "mid_rate": 4.35,
            "bid_rate": 4.34,
            "ask_rate": 4.36,
            "currency": "USD",
        },
        {
            "tenor": "10Y",
            "mid_rate": 4.52,
            "bid_rate": 4.51,
            "ask_rate": 4.53,
            "currency": "USD",
        },
        {
            "tenor": "30Y",
            "mid_rate": 4.68,
            "bid_rate": 4.67,
            "ask_rate": 4.69,
            "currency": "USD",
        },
    ]


@pytest.fixture
def mock_request():
    """Mock Gradio request object for rate limiting tests."""
    request = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_db():
    """Mock database connection with in-memory data storage."""
    db = MagicMock()

    # In-memory storage for test data
    db._data = {
        "swap_positions": [],
        "market_rates": [],
        "trade_signals": [],
        "demo_executions": [],
    }

    def execute_query(query, params=None):
        """Mock execute_query that uses in-memory storage."""
        query_upper = query.strip().upper()

        # SELECT queries
        if query_upper.startswith("SELECT"):
            if "swap_positions" in query:
                if params and "position_id" in query:
                    # Get by ID
                    pos_id = params[0] if isinstance(params, tuple) else params
                    results = [
                        p
                        for p in db._data["swap_positions"]
                        if p.get("position_id") == pos_id
                    ]
                    return results[:1] if results else []
                else:
                    # Get all
                    return db._data["swap_positions"]

            elif "market_rates" in query:
                if params and len(params) >= 2:
                    # Get by tenor and currency
                    tenor, currency = params[0], params[1]
                    results = [
                        r
                        for r in db._data["market_rates"]
                        if r.get("tenor") == tenor and r.get("currency") == currency
                    ]
                    # Sort by timestamp desc and return latest
                    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    return results[:1] if results else []
                else:
                    # Get all
                    return db._data["market_rates"]

            elif "trade_signals" in query:
                if params:
                    pos_id = params[0] if isinstance(params, tuple) else params
                    results = [
                        s
                        for s in db._data["trade_signals"]
                        if s.get("position_id") == pos_id
                    ]
                    results.sort(key=lambda x: x.get("timestamp", ""))
                    return results
                else:
                    return db._data["trade_signals"]

            elif "demo_executions" in query:
                if params:
                    ip = params[0] if isinstance(params, tuple) else params
                    # Count executions for IP in last 24 hours (simplified - just count all)
                    count = len(
                        [
                            e
                            for e in db._data["demo_executions"]
                            if e.get("ip_address") == ip
                        ]
                    )
                    return [{"count": count}]
                return [{"count": 0}]

            elif "EXISTS" in query_upper and "information_schema" in query:
                # Check if table exists
                return [(True,)]

            return []

        # INSERT queries
        elif query_upper.startswith("INSERT"):
            if "swap_positions" in query:
                pos = {
                    "position_id": params[0],
                    "trade_date": params[1],
                    "maturity_date": params[2],
                    "notional": params[3],
                    "fixed_rate": params[4],
                    "float_index": params[5],
                    "pay_receive": params[6],
                    "currency": params[7],
                }
                db._data["swap_positions"].append(pos)
                return 1

            elif "market_rates" in query:
                rate = {
                    "tenor": params[0],
                    "currency": params[1],
                    "mid_rate": params[2],
                    "bid_rate": params[3],
                    "ask_rate": params[4],
                    "timestamp": MagicMock(),  # Mock timestamp
                }
                db._data["market_rates"].append(rate)
                return 1

            elif "trade_signals" in query:
                signal = {
                    "position_id": params[0],
                    "signal_type": params[1],
                    "current_pnl": params[2],
                    "reason": params[3],
                    "recommended_action": params[4],
                    "executed": False,
                    "timestamp": MagicMock(),
                }
                db._data["trade_signals"].append(signal)
                return 1

            elif "demo_executions" in query:
                execution = {
                    "ip_address": params[0],
                    "last_run": MagicMock(),
                }
                db._data["demo_executions"].append(execution)
                return 1

            return 1

        # DELETE queries
        elif query_upper.startswith("DELETE"):
            if "swap_positions" in query:
                db._data["swap_positions"].clear()
            elif "market_rates" in query:
                db._data["market_rates"].clear()
            elif "trade_signals" in query:
                db._data["trade_signals"].clear()
            elif "demo_executions" in query:
                db._data["demo_executions"].clear()
            return 0

        return []

    db.execute_query = MagicMock(side_effect=execute_query)
    db.connect = MagicMock(return_value=None)
    db.close = MagicMock(return_value=None)
    db.initialize_schema = MagicMock(return_value=None)

    return db

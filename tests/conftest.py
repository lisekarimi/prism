"""Pytest configuration and fixtures for PRISM tests."""

from unittest.mock import MagicMock

import pytest
from crewai import Agent, Crew, Task
from crewai_tools import SerperDevTool


@pytest.fixture
def mock_serper_tool():
    """Mock SerperDevTool to avoid actual API calls."""
    mock_tool = MagicMock(spec=SerperDevTool)
    mock_tool.run.return_value = {
        "organic": [
            {
                "title": "USD SOFR Swap Rates",
                "snippet": "2Y: 4.15%, 5Y: 4.35%, 10Y: 4.52%, 30Y: 4.68%",
            }
        ]
    }
    return mock_tool


@pytest.fixture
def mock_agent():
    """Mock CrewAI Agent to avoid LLM calls."""
    agent = MagicMock(spec=Agent)
    agent.execute.return_value = "Mocked agent execution result"
    agent.role = "Mock Agent"
    agent.goal = "Mock Goal"
    agent.backstory = "Mock Backstory"
    return agent


@pytest.fixture
def mock_crew():
    """Mock CrewAI Crew to avoid actual execution."""
    crew = MagicMock(spec=Crew)
    crew.kickoff.return_value = "Mocked crew execution result"
    crew.agents = []
    crew.tasks = []
    return crew


@pytest.fixture
def mock_task():
    """Mock CrewAI Task."""
    task = MagicMock(spec=Task)
    task.execute.return_value = "Mocked task execution result"
    task.description = "Mock Task Description"
    task.expected_output = "Mock Expected Output"
    return task


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_db = MagicMock()
    mock_db.connect.return_value = None
    mock_db.close.return_value = None
    mock_db.execute_query.return_value = []
    return mock_db


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
    ]


@pytest.fixture
def sample_market_rates():
    """Sample market rates for testing."""
    return [
        {"tenor": "2Y", "mid_rate": 4.15, "bid_rate": 4.14, "ask_rate": 4.16},
        {"tenor": "5Y", "mid_rate": 4.35, "bid_rate": 4.34, "ask_rate": 4.36},
        {"tenor": "10Y", "mid_rate": 4.52, "bid_rate": 4.51, "ask_rate": 4.53},
        {"tenor": "30Y", "mid_rate": 4.68, "bid_rate": 4.67, "ask_rate": 4.69},
    ]

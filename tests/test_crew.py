"""Tests for PrismCrew initialization and structure."""

from unittest.mock import MagicMock, patch

from prism.crew import PrismCrew


class TestPrismCrew:
    """Test PrismCrew class initialization and structure."""

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    def test_crew_initialization(self, mock_agent_class, mock_serper_tool):
        """Test that PrismCrew can be initialized without errors."""
        # Mock SerperDevTool
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        # Mock Agent class
        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        # Initialize crew
        crew = PrismCrew()
        assert crew is not None

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    def test_market_data_agent_has_tools(self, mock_agent_class, mock_serper_tool):
        """Test that market_data_agent is configured with correct tools."""
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        crew = PrismCrew()

        # Call the agent method
        agent = crew.market_data_agent()

        # Verify agent was created
        assert agent is not None

        # Verify Agent was called
        assert mock_agent_class.called

        # Verify SerperDevTool was instantiated
        assert mock_serper_tool.called

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    def test_all_agents_initialized(self, mock_agent_class, mock_serper_tool):
        """Test that all 5 agents can be initialized."""
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        crew = PrismCrew()

        # Initialize all agents
        market_agent = crew.market_data_agent()
        position_agent = crew.position_manager_agent()
        risk_calc_agent = crew.risk_calculator_agent()
        risk_mgr_agent = crew.risk_manager_agent()
        trading_agent = crew.trading_decision_agent()

        # Verify all agents were created
        assert market_agent is not None
        assert position_agent is not None
        assert risk_calc_agent is not None
        assert risk_mgr_agent is not None
        assert trading_agent is not None

        # Verify Agent class was called 5 times
        assert mock_agent_class.call_count == 5

    @patch("prism.crew.Task")
    def test_all_tasks_initialized(self, mock_task_class):
        """Test that all tasks can be initialized."""
        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        crew = PrismCrew()

        # Initialize all tasks
        fetch_task = crew.fetch_market_data_task()
        load_task = crew.load_positions_task()
        thresholds_task = crew.set_thresholds_task()
        risk_task = crew.calculate_risk_task()
        decision_task = crew.make_trading_decision_task()

        # Verify all tasks were created
        assert fetch_task is not None
        assert load_task is not None
        assert thresholds_task is not None
        assert risk_task is not None
        assert decision_task is not None

        # Verify Task class was called 5 times
        assert mock_task_class.call_count == 5

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_crew_assembly(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test that crew can be assembled with all agents and tasks."""
        # Setup mocks
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        crew = PrismCrew()

        # Assemble the crew
        assembled_crew = crew.crew()

        # Verify Crew was instantiated
        assert mock_crew_class.called
        assert assembled_crew is not None

        # Verify Crew was called with correct parameters
        call_kwargs = mock_crew_class.call_args[1]
        assert "agents" in call_kwargs
        assert "tasks" in call_kwargs
        assert "process" in call_kwargs

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_crew_kickoff_mocked(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test that crew.kickoff() can be called with mocked execution."""
        # Setup mocks
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        # Mock crew instance with kickoff method
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "Mocked execution result"
        mock_crew_class.return_value = mock_crew_instance

        crew = PrismCrew()
        assembled_crew = crew.crew()

        # Test kickoff with mocked execution (no actual LLM calls)
        inputs = {"cycle": 1, "tenors": "2Y, 5Y, 10Y, 30Y", "currency": "USD"}

        result = assembled_crew.kickoff(inputs=inputs)

        # Verify kickoff was called
        assert mock_crew_instance.kickoff.called
        assert result == "Mocked execution result"

        # Verify no actual LLM calls were made (SerperDevTool.run should not be called)
        assert not mock_serper_instance.run.called

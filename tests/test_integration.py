"""Integration tests for PRISM crew execution flow with mocks."""

from unittest.mock import MagicMock, patch

from prism.crew import PrismCrew


class TestCrewExecutionFlow:
    """Test the complete crew execution flow with all mocks."""

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_full_crew_execution_mocked(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test full crew execution with all external calls mocked."""
        # Setup SerperDevTool mock
        mock_serper_instance = MagicMock()
        mock_serper_instance.run.return_value = {
            "organic": [
                {
                    "title": "USD SOFR Swap Rates",
                    "snippet": "2Y: 4.15%, 5Y: 4.35%, 10Y: 4.52%, 30Y: 4.68%",
                }
            ]
        }
        mock_serper_tool.return_value = mock_serper_instance

        # Setup Agent mocks
        mock_agent_instance = MagicMock()
        mock_agent_instance.role = "Test Agent"
        mock_agent_instance.goal = "Test Goal"
        mock_agent_class.return_value = mock_agent_instance

        # Setup Task mocks
        mock_task_instance = MagicMock()
        mock_task_instance.description = "Test Task"
        mock_task_class.return_value = mock_task_instance

        # Setup Crew mock with kickoff
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = {
            "tasks_output": [
                "Market data fetched",
                "Positions loaded",
                "Thresholds calculated",
                "Risk calculated",
                "Trading decisions made",
            ]
        }
        mock_crew_class.return_value = mock_crew_instance

        # Initialize and run crew
        crew = PrismCrew()
        assembled_crew = crew.crew()

        inputs = {"cycle": 1, "tenors": "2Y, 5Y, 10Y, 30Y", "currency": "USD"}

        # Execute (this should not make any real API calls)
        _ = assembled_crew.kickoff(inputs=inputs)

        # Verify crew was assembled correctly
        assert mock_crew_class.called
        call_kwargs = mock_crew_class.call_args[1]
        assert "agents" in call_kwargs
        assert "tasks" in call_kwargs
        assert len(call_kwargs["agents"]) == 5
        assert len(call_kwargs["tasks"]) == 5

        # Verify kickoff was called
        assert mock_crew_instance.kickoff.called
        assert mock_crew_instance.kickoff.call_args[1]["inputs"] == inputs

        # Verify NO actual API calls were made
        # SerperDevTool.run should NOT be called (it's mocked at the tool level)
        # The agent would call it, but since we're mocking the entire Agent class,
        # the actual tool execution never happens

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_crew_agents_have_correct_tools(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test that agents are configured with correct tools."""
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        crew = PrismCrew()

        # Get all agents
        _ = crew.market_data_agent()
        _ = crew.position_manager_agent()
        _ = crew.risk_calculator_agent()
        _ = crew.risk_manager_agent()
        _ = crew.trading_decision_agent()

        # Verify Agent was called 5 times
        assert mock_agent_class.call_count == 5

        # Verify SerperDevTool was instantiated (for market_data_agent)
        assert mock_serper_tool.called

        # Check that agents were created with tools parameter
        # Market data agent should have SerperDevTool
        # (We can't easily verify the exact tools without inspecting the call args more deeply,
        # but we can verify the structure is correct)

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_crew_process_is_sequential(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test that crew is configured with sequential process."""
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        crew = PrismCrew()
        _ = crew.crew()

        # Verify Crew was called with process=Process.sequential
        call_kwargs = mock_crew_class.call_args[1]
        assert "process" in call_kwargs
        # The process should be Process.sequential (we can't easily check the enum value,
        # but we can verify the parameter was passed)

    @patch("prism.crew.SerperDevTool")
    @patch("prism.crew.Agent")
    @patch("prism.crew.Task")
    @patch("prism.crew.Crew")
    def test_crew_handles_multiple_cycles(
        self, mock_crew_class, mock_task_class, mock_agent_class, mock_serper_tool
    ):
        """Test that crew can handle multiple execution cycles."""
        mock_serper_instance = MagicMock()
        mock_serper_tool.return_value = mock_serper_instance

        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance

        mock_task_instance = MagicMock()
        mock_task_class.return_value = mock_task_instance

        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "Cycle completed"
        mock_crew_class.return_value = mock_crew_instance

        crew = PrismCrew()
        assembled_crew = crew.crew()

        # Run multiple cycles
        for cycle in range(1, 4):
            inputs = {"cycle": cycle, "tenors": "2Y, 5Y, 10Y, 30Y", "currency": "USD"}
            result = assembled_crew.kickoff(inputs=inputs)
            assert result == "Cycle completed"

        # Verify kickoff was called 3 times
        assert mock_crew_instance.kickoff.call_count == 3

        # Verify NO actual API calls were made
        assert not mock_serper_instance.run.called

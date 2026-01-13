# src/prism/app.py
from datetime import datetime

import gradio as gr

from prism.database.connection import DatabaseConnection
from prism.database.init_db import initialize_database
from prism.utils.gradio_helpers import (
    get_latest_rates,
    get_latest_signals,
    get_positions,
    load_log,
    run_once_with_limit,
)
from prism.utils.logging import logger

# Initialize database before starting the app
logger.info("🔧 Checking database...")
initialize_database()


def load_all_positions():
    """Load all positions."""
    return get_positions()


def load_all_signals():
    """Load all signals."""
    return get_latest_signals()


def handle_run_dashboard(request: gr.Request):
    """Handle Dashboard button click and return compact status with immediate feedback."""
    # Show immediate "running" state
    yield (
        gr.update(value="🔄 Running...", interactive=False),
        "**🔄 Running analysis cycle...** Please wait while agents process your positions.",
    )

    # Run the actual cycle
    result_dict = run_once_with_limit(request)

    # Create a compact status message for Dashboard
    if "✅" in result_dict["output"]:
        status_msg = "**✅ Cycle completed!** Data refreshed. See results below."
    elif "⚠️" in result_dict["output"]:
        status_msg = result_dict["output"]
    else:
        status_msg = "**✅ Cycle completed!** Data refreshed. See results below."

    # Return final state
    yield (
        gr.update(
            value=result_dict["button_text"], interactive=result_dict["interactive"]
        ),
        status_msg,
    )


def get_current_usage(request: gr.Request = None):
    """Get current usage count for this IP."""
    # Handle case when request might not be available (e.g., during initial load)
    if request is None or not hasattr(request, "client") or request.client is None:
        return "🔄 Run Cycle (0/5 used)"

    ip = request.client.host
    db = DatabaseConnection()
    db.connect()

    check_query = """
        SELECT COUNT(*) as count FROM demo_executions
        WHERE ip_address = %s
        AND last_run > NOW() - INTERVAL '24 hours'
    """
    result = db.execute_query(check_query, (ip,))
    count = result[0]["count"] if result else 0
    db.close()

    return f"🔄 Run Cycle ({count}/5 used)"


# Build Gradio interface
with gr.Blocks(
    title="PRISM - Swap Trading AI",
    theme=gr.themes.Soft(),
    head="""
    <script>
    (function() {
        var script = document.createElement("script");
        script.src = "https://pagebotai.lisekarimi.com/static/embed.js";
        script.onload = function() {
            initializePageBotAI({
                chatbotName: 'PrismBot',
                primaryColor: '#7c3aed',
                instructions: 'You are a helpful AI assistant that answers questions based on the content of the websites you can access. Be friendly, concise, and accurate in your responses.',
                targetUrls: ['https://prism.lisekarimi.com'],
                wsUrl: 'https://pagebotai.lisekarimi.com/ws/chat'
            });
        };
        document.head.appendChild(script);
    })();
    </script>
    """,
) as demo:
    gr.Markdown("# 🎯 PRISM - Position Risk Intelligence & Swap Monitor")
    gr.Markdown(
        "Real-time monitoring for **USD SOFR interest rate swaps** with AI agents (2Y, 5Y, 10Y, 30Y)"
    )

    def get_server_time():
        """Get current server time formatted."""
        return f"🕐 **Server Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    server_time = gr.Markdown(value=get_server_time, every=1)  # Update every second

    gr.Markdown("<br>")

    with gr.Tab("📊 Dashboard"):
        # Run button at the top - primary action where results are visible
        with gr.Row():
            run_once_btn = gr.Button(
                "🔄 Run Cycle (0/5 used)", variant="primary", size="lg"
            )
            status_output = gr.Markdown("", visible=True)

        gr.Markdown(
            "⚠️ **Demo Mode**: Limited to **5 executions per 24 hours** to control API costs"
        )
        gr.Markdown("<br>")

        # Connect Dashboard button
        run_once_btn.click(
            fn=handle_run_dashboard, outputs=[run_once_btn, status_output]
        )

        # Latest Market Rates - full width
        gr.Markdown("### Latest Market Rates (USD SOFR)")
        rates_table = gr.Dataframe(
            value=get_latest_rates,
            wrap=True,
            max_height=300,
            every=10,  # Auto-refresh every 10 seconds
        )

        gr.Markdown("<br>")

        # Current Positions - full width
        gr.Markdown("### Current Positions")
        positions_table = gr.Dataframe(
            value=load_all_positions, wrap=True, max_height=300, every=10
        )

        gr.Markdown("<br>")

        # Trade Signals full width below (can be many)
        gr.Markdown("### 🚨 Recent Trade Signals")
        signals_table = gr.Dataframe(
            value=load_all_signals, wrap=True, max_height=400, every=10
        )

    with gr.Tab("🧠 Agent Reasoning"):
        gr.Markdown("### View Agent Decision-Making Process")

        log_selector = gr.Dropdown(
            choices=[
                "market_data_output.txt",
                "positions_output.txt",
                "thresholds_output.txt",
                "risk_calculation_output.txt",
                "trading_decisions_output.txt",
            ],
            label="Select Log File",
            value="trading_decisions_output.txt",
        )

        log_viewer = gr.Textbox(
            label="Agent Reasoning & Output", lines=20, max_lines=30, interactive=False
        )

        refresh_logs_btn = gr.Button("🔄 Refresh Logs")
        refresh_logs_btn.click(fn=load_log, inputs=log_selector, outputs=log_viewer)
        log_selector.change(fn=load_log, inputs=log_selector, outputs=log_viewer)

    with gr.Tab("📈 About PRISM"):
        gr.Markdown("""
        ## 🎯 PRISM - AI-Powered Swap Trading Monitor

        **Monitors USD SOFR interest rate swap positions and alerts you when to close them**

        ---

        ### 🤖 How It Works

        PRISM uses **5 AI agents** that work sequentially to analyze your positions:

        1. **Market Data Agent** 📡
        2. **Portfolio Agent** 📊
        3. **Risk Manager Agent** ⚖️
        4. **Risk Calculator Agent** 💰
        5. **Trading Decision Agent** 🎯

        ![Workflow](https://github.com/lisekarimi/prism/blob/main/assets/workflow.png?raw=true)

        ---

        ### 📊 What You See

        - **Market Rates**: Live USD SOFR swap rates with trend indicators
            - 🟢↗ = Rate increased vs last check (good if you receive fixed)
            - 🔴↘ = Rate decreased vs last check (good if you pay fixed)
            - Auto-refreshes every 10 seconds

        - **Positions**: All your open swap positions
            - Shows: Position ID, entry rate, notional, maturity date, pay/receive direction
            - Track when you entered each trade and at what rate

        - **Trade Signals**: Color-coded action alerts
            - 🔴 CLOSE = Profit target hit or stop loss triggered → exit position now
            - 🟢 HOLD = Position within acceptable range → keep holding
            - Shows current P&L and reasoning for each signal

        - **Agent Reasoning**: Transparent decision-making logs
            - See exactly why agents recommended each action
            - View calculations, thresholds used, and step-by-step analysis
            - Full audit trail of every agent's thought process
        ---

        **Built with:** CrewAI Multi-Agent Framework | SerperDevTool | PostgreSQL | Gradio
        """)

    # Load actual count on startup to show correct usage
    demo.load(fn=get_current_usage, outputs=run_once_btn)

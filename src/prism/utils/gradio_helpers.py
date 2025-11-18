# src/prism/utils/gradio_helpers.py
"""Helper functions for Gradio interface."""

import os
import threading
import time
from datetime import datetime

import pandas as pd

from ..constants import DEFAULT_CURRENCY, MAX_RUNS, TENORS
from ..crew import PrismCrew
from ..database.connection import DatabaseConnection
from ..utils import logger

# Global state
crew_running = False
crew_thread = None


def get_positions():
    """Fetch all current positions."""
    db = DatabaseConnection()
    db.connect()
    query = """
        SELECT * FROM swap_positions
        ORDER BY trade_date DESC
    """
    positions = db.execute_query(query)
    db.close()
    return pd.DataFrame(positions) if positions else pd.DataFrame()


def get_latest_signals():
    """Fetch the 10 most recent trade signals with color indicators."""
    db = DatabaseConnection()
    db.connect()
    query = """
        SELECT signal_id, position_id, signal_type, current_pnl,
               reason, recommended_action, timestamp, executed
        FROM trade_signals
        ORDER BY timestamp DESC
        LIMIT 10
    """
    signals = db.execute_query(query)
    db.close()

    df = pd.DataFrame(signals) if signals else pd.DataFrame()

    # Add color emoji to signal_type
    if not df.empty and "signal_type" in df.columns:
        df["signal_type"] = df["signal_type"].apply(
            lambda x: f"🔴 {x}"
            if x == "CLOSE"
            else f"🟢 {x}"
            if x == "HOLD"
            else f"🟡 {x}"  # HEDGE
        )

    return df


def get_latest_rates():
    """Fetch latest market rates with trend indicators."""
    db = DatabaseConnection()
    db.connect()

    # Get current rates
    query = """
        SELECT DISTINCT ON (tenor) tenor, mid_rate, bid_rate, ask_rate, timestamp
        FROM market_rates
        ORDER BY tenor, timestamp DESC
    """
    current_rates = db.execute_query(query)

    # Get previous rates
    prev_query = """
        SELECT DISTINCT ON (tenor) tenor, mid_rate
        FROM market_rates
        WHERE timestamp < (SELECT MAX(timestamp) FROM market_rates)
        ORDER BY tenor, timestamp DESC
    """
    prev_rates = db.execute_query(prev_query)

    db.close()

    df = pd.DataFrame(current_rates) if current_rates else pd.DataFrame()

    if not df.empty and prev_rates:
        prev_dict = {r["tenor"]: r["mid_rate"] for r in prev_rates}

        def get_trend(row):
            current = row["mid_rate"]
            prev = prev_dict.get(row["tenor"])

            if prev is None:
                return "⚪ --"
            elif current > prev:
                return "🟢 ↗"
            elif current < prev:
                return "🔴 ↘"
            else:
                return "⚪ →"

        df["trend"] = df.apply(get_trend, axis=1)

        # Reorder columns: tenor, trend, mid_rate, bid_rate, ask_rate, timestamp
        df = df[["tenor", "trend", "mid_rate", "bid_rate", "ask_rate", "timestamp"]]

    return df


def load_log(filename):
    """Load log file content."""
    try:
        with open(f"logs/{filename}") as f:
            return f.read()
    except FileNotFoundError:
        return "Log file not found - run a cycle first"


def update_log_timestamps():
    """Add or update timestamp header at the top of each log file."""
    log_files = [
        "market_data_output.txt",
        "positions_output.txt",
        "thresholds_output.txt",
        "risk_calculation_output.txt",
        "trading_decisions_output.txt",
    ]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_line = f"Last run: {timestamp}\n"

    for log_file in log_files:
        log_path = f"logs/{log_file}"
        try:
            # Read existing content if file exists
            if os.path.exists(log_path):
                with open(log_path, encoding="utf-8") as f:
                    content = f.read()

                # Check if file already has a timestamp header
                if content.startswith("Last run:"):
                    # Replace the first line with new timestamp
                    lines = content.split("\n", 1)
                    new_content = timestamp_line + (lines[1] if len(lines) > 1 else "")
                else:
                    # Prepend timestamp to existing content
                    new_content = timestamp_line + content
            else:
                # File doesn't exist yet, just create with timestamp
                new_content = timestamp_line

            # Write back to file
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            logger.warning(f"Failed to update timestamp for {log_file}: {e}")


def run_crew_cycle():
    """Run one cycle of the crew."""
    inputs = {"cycle": 1, "tenors": ", ".join(TENORS), "currency": DEFAULT_CURRENCY}
    result = PrismCrew().crew().kickoff(inputs=inputs)
    # Update timestamps in all log files after crew completes
    update_log_timestamps()
    return f"✅ Cycle completed at {datetime.now().strftime('%H:%M:%S')}\n{result}"


def start_crew_monitoring():
    """Start continuous crew monitoring."""
    global crew_running, crew_thread

    def monitor_loop():
        global crew_running
        cycle = 1
        while crew_running:
            logger.info(f"🔄 Running cycle {cycle}")
            inputs = {
                "cycle": cycle,
                "tenors": ", ".join(TENORS),
                "currency": DEFAULT_CURRENCY,
            }
            PrismCrew().crew().kickoff(inputs=inputs)
            # Update timestamps in all log files after crew completes
            update_log_timestamps()
            cycle += 1
            time.sleep(60)

    if not crew_running:
        crew_running = True
        crew_thread = threading.Thread(target=monitor_loop, daemon=True)
        crew_thread.start()
        return "✅ Started continuous monitoring (60s intervals)"
    return "⚠️ Monitoring already running"


def stop_crew_monitoring():
    """Stop continuous monitoring."""
    global crew_running
    crew_running = False
    return "🛑 Stopped continuous monitoring"


def run_once_with_limit(request):
    """Run crew with IP-based rate limiting."""
    ip = request.client.host

    db = DatabaseConnection()
    db.connect()

    # Check execution count in last 24 hours
    check_query = """
        SELECT COUNT(*) as count FROM demo_executions
        WHERE ip_address = %s
        AND last_run > NOW() - INTERVAL '24 hours'
    """
    result = db.execute_query(check_query, (ip,))
    count = result[0]["count"] if result else 0

    if count >= MAX_RUNS:
        db.close()
        return {
            "output": f"⚠️ Demo limit reached: {MAX_RUNS} executions per 24 hours. Try again tomorrow!",
            "button_text": f"✓ Limit Reached ({count}/{MAX_RUNS})",
            "interactive": False,
        }

    # Record new execution
    insert_query = """
        INSERT INTO demo_executions (ip_address, last_run)
        VALUES (%s, NOW())
    """
    db.execute_query(insert_query, (ip,))
    db.close()

    # Run the crew
    result = run_crew_cycle()
    new_count = count + 1

    return {
        "output": result,
        "button_text": f"🔄 Run Cycle ({new_count}/{MAX_RUNS} used)"
        if new_count < MAX_RUNS
        else f"✓ Limit Reached ({new_count}/{MAX_RUNS})",
        "interactive": new_count < MAX_RUNS,
    }

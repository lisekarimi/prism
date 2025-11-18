# src/prism/tools/calculation_tools.py
from datetime import datetime

from crewai.tools import tool
from pydantic import Field

from ..utils import logger


def _calculate_years_to_maturity_internal(maturity_date):
    """Calculate years to maturity."""
    if isinstance(maturity_date, str):
        maturity = datetime.strptime(maturity_date, "%Y-%m-%d")
    else:
        maturity = maturity_date

    today = datetime.now()
    days_remaining = (maturity - today).days
    years = days_remaining / 365.25
    return max(years, 0)


@tool("Calculate Swap PnL")
def calculate_swap_pnl(
    position: dict = Field(  # noqa: B008
        ...,
        description="Position dictionary with keys: position_id, fixed_rate, notional, pay_receive, maturity_date",
    ),
    current_rate: float = Field(  # noqa: B008
        ..., description="Current market swap rate as decimal (e.g., 0.0435 for 4.35%)"
    ),
):
    """Calculate the P&L for a swap position.

    Formula: (Current_Rate - Entry_Rate) × DV01 × Notional × Direction
    """
    position_id = position.get("position_id", "unknown")
    logger.info(f"💰 Calculating P&L for position {position_id}")

    entry_rate = float(position["fixed_rate"])
    notional = float(position["notional"])

    # Determine direction: PAY_FIXED = short rates (lose if rates rise), RCV_FIXED = long rates
    direction = -1 if position["pay_receive"] == "PAY_FIXED" else 1
    logger.debug(
        f"  Entry rate: {entry_rate}%, Current rate: {current_rate}%, Direction: {position['pay_receive']} ({direction})"
    )

    # Use internal helper function instead of tool
    years_to_maturity = _calculate_years_to_maturity_internal(position["maturity_date"])
    dv01 = notional * 0.0001 * years_to_maturity  # 1bp move impact

    # P&L = rate change in bps × DV01 × direction
    rate_change_bps = (current_rate - entry_rate) * 10000  # convert to basis points
    pnl = rate_change_bps * dv01 * direction

    logger.info(
        f"  P&L: ${pnl:,.2f} | Rate change: {round(rate_change_bps, 2)} bps | DV01: ${round(dv01, 2)}"
    )

    return {
        "position_id": position["position_id"],
        "entry_rate": entry_rate,
        "current_rate": current_rate,
        "rate_change_bps": round(rate_change_bps, 2),
        "dv01": round(dv01, 2),
        "pnl": round(pnl, 2),
        "notional": notional,
    }


@tool("Calculate Years to Maturity")
def calculate_years_to_maturity(
    maturity_date: str = Field(
        ..., description="Maturity date in YYYY-MM-DD format (e.g., '2029-01-15')"
    ),
):
    """Calculate years remaining until swap maturity."""
    years = _calculate_years_to_maturity_internal(maturity_date)
    logger.debug(f"  Years to maturity: {years:.2f} (maturity: {maturity_date})")
    return years


@tool("Calculate Portfolio DV01")
def calculate_portfolio_dv01(
    positions: list = Field(  # noqa: B008
        ...,
        description="List of position dictionaries, each containing notional, maturity_date, and pay_receive",
    ),
):
    """Calculate total DV01 (interest rate risk) across all positions."""
    logger.info(f"📊 Calculating portfolio DV01 for {len(positions)} positions")
    total_dv01 = 0

    for position in positions:
        notional = float(position["notional"])
        years = _calculate_years_to_maturity_internal(position["maturity_date"])
        dv01 = notional * 0.0001 * years

        # Account for direction
        direction = -1 if position["pay_receive"] == "PAY_FIXED" else 1
        total_dv01 += dv01 * direction

    result = round(total_dv01, 2)
    logger.info(f"  Total portfolio DV01: ${result:,.2f}")
    return result


@tool("Check Trading Signal")
def check_trading_signal(
    pnl: float = Field(..., description="Current P&L in dollars"),
    threshold_profit: float = Field(
        default=50000, description="Profit target in dollars"
    ),
    threshold_loss: float = Field(default=-25000, description="Stop loss in dollars"),
):
    """Determine if a trading signal should be triggered based on P&L thresholds."""
    logger.debug(
        f"🔍 Checking trading signal: P&L=${pnl:,.2f}, Profit threshold=${threshold_profit:,.2f}, Loss threshold=${threshold_loss:,.2f}"
    )

    if pnl >= threshold_profit:
        signal = {
            "signal": "CLOSE",
            "reason": f"Profit target hit: ${pnl:,.2f} >= ${threshold_profit:,.2f}",
            "action": "Close position to lock in profit",
        }
        logger.warning(f"🚨 PROFIT TARGET HIT: {signal['reason']}")
        return signal
    elif pnl <= threshold_loss:
        signal = {
            "signal": "CLOSE",
            "reason": f"Stop loss hit: ${pnl:,.2f} <= ${threshold_loss:,.2f}",
            "action": "Close position to limit loss",
        }
        logger.warning(f"🚨 STOP LOSS HIT: {signal['reason']}")
        return signal
    else:
        signal = {
            "signal": "HOLD",
            "reason": f"P&L ${pnl:,.2f} within acceptable range",
            "action": "Continue monitoring",
        }
        logger.debug(f"  Signal: HOLD - {signal['reason']}")
        return signal


@tool("Calculate Dynamic Thresholds")
def calculate_dynamic_thresholds(
    position: dict = Field(..., description="Position with notional and maturity"),  # noqa: B008
    volatility: float = Field(default=0.02, description="Recent rate volatility"),  # noqa: B008
):
    """Calculate dynamic profit/loss thresholds based on position size and volatility."""
    notional = float(position["notional"])

    # Larger positions = tighter stops (as % of notional)
    if notional >= 20000000:  # $20M+
        profit_pct = 0.003  # 0.3%
        loss_pct = 0.0015  # 0.15%
    elif notional >= 10000000:  # $10M+
        profit_pct = 0.005
        loss_pct = 0.0025
    else:
        profit_pct = 0.01
        loss_pct = 0.005

    # Adjust for volatility
    profit_target = notional * profit_pct * (1 + volatility * 10)
    stop_loss = -notional * loss_pct * (1 + volatility * 10)

    return {
        "position_id": position["position_id"],
        "profit_target": round(profit_target, 2),
        "stop_loss": round(stop_loss, 2),
    }

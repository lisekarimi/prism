# 🎯 PRISM - Position Risk Intelligence & Swap Monitor

AI-powered swap trading monitoring system using CrewAI multi-agent framework.

## What It Does

PRISM monitors swap trading positions in real-time and automatically generates trading signals when profit/loss thresholds are hit.

## Architecture

**4 AI Agents working together:**

1. **Market Data Agent** - Fetches current swap rates (2Y, 5Y, 10Y, 30Y)
2. **Position Manager Agent** - Loads trader's swap positions from database
3. **Risk Calculator Agent** - Calculates P&L and DV01 for each position
4. **Trading Decision Agent** - Generates CLOSE/HOLD signals based on thresholds

**Thresholds:**
- Close position when profit ≥ $50K
- Close position when loss ≤ -$25K
- Otherwise HOLD

## Tech Stack

- **CrewAI** - Multi-agent orchestration
- **PostgreSQL** - Position & rate storage (Neon)
- **Gradio** - Web dashboard
- **Python 3.11** - Runtime



## Configuration

Edit `.env`:
```
OPENAI_API_KEY=your_key
DATABASE_URL=postgresql://...
```

Edit `src/prism/utils/constants.py` for thresholds and settings.

## Quick Start


## Database Schema

- `swap_positions` - Trader's swap portfolio
- `market_rates` - Historical rate data
- `trade_signals` - AI-generated trading decisions



---

**Status:** MVP with mock data - Ready for real API integration

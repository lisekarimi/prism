---
title: PRISM
emoji: 💹
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: PRISM - Position Risk Intelligence & Swap Monitor
---

# 💹 PRISM - Position Risk Intelligence & Swap Monitor

AI-powered swap trading monitoring system using CrewAI multi-agent framework.

**🌐 Live Demo:** [prism.lisekarimi.com](https://prism.lisekarimi.com)

![PRISM Dashboard](https://github.com/lisekarimi/prism/blob/main/assets/screenshot.png?raw=true)

## 📊 What It Does

PRISM monitors USD SOFR swap trading positions in real-time and automatically generates trading signals when profit/loss thresholds are hit.

**Note:** This demo is specifically configured for USD SOFR (Secured Overnight Financing Rate) swaps only.

## 🏗️ Architecture

![PRISM Workflow](https://github.com/lisekarimi/prism/blob/main/assets/workflow.png?raw=true)

**5 AI Agents working together:**

1. **Market Data Agent** - Fetches current USD SOFR swap rates (2Y, 5Y, 10Y, 30Y)
2. **Position Manager Agent** - Loads trader's swap positions from database
3. **Risk Manager Agent** - Analyzes market conditions and sets dynamic profit/loss thresholds
4. **Risk Calculator Agent** - Calculates P&L for each position
5. **Trading Decision Agent** - Generates CLOSE/HOLD signals based on thresholds

**Thresholds:**
- Close position when profit ≥ $50K
- Close position when loss ≤ -$25K
- Otherwise HOLD

## 🛠️ Tech Stack

- **CrewAI** - Multi-agent orchestration
- **PostgreSQL** - Position & rate storage (Neon)
- **Gradio** - Web dashboard
- **Python 3.11** - Runtime

## 🚀 Deploy on Hugging Face Spaces

This app is built to run as a Docker Space on Hugging Face.

### 1. Fork & create a Space

- Fork this repo on GitHub
- Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Docker** as the SDK
- Link it to your forked GitHub repo

### 2. Set Space secrets

In your Space settings → **Variables and Secrets**, add:

| Secret | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (e.g. from [Neon](https://neon.tech)) |
| `OPENAI_API_KEY` | OpenAI API key for the LLM agents |
| `SERPER_API_KEY` | Serper API key for Google Search ([serper.dev](https://serper.dev)) |

### 3. Deploy

Push to your linked branch — HF Spaces will build and deploy automatically.

## 📋 Local Development

**Prerequisites:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- PostgreSQL database (free tier at [neon.tech](https://neon.tech))
- OpenAI API key
- Serper API key

**Setup:**

```bash
git clone https://github.com/lisekarimi/prism.git
cd prism
cp .env.example .env  # fill in your credentials
make dev
```

## 🗄️ Database Schema

- `swap_positions` - Trader's swap portfolio
- `market_rates` - Historical rate data
- `trade_signals` - AI-generated trading decisions

# src/prism/constants.py
"""Constants for PRISM trading system."""

import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ============================================================================
# PROJECT METADATA
# ============================================================================

root = Path(__file__).resolve().parent.parent.parent
with open(root / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

PROJECT_NAME = pyproject["project"]["name"]
VERSION = pyproject["project"]["version"]
DESCRIPTION = pyproject["project"]["description"]

# ============================================================================
# AI/MODEL CONFIGURATION
# ============================================================================

MODEL = "gpt-4o-mini"

# ============================================================================
# TRADING CONFIGURATION
# ============================================================================

# Core trading thresholds
# PROFIT_TARGET = 50000
# STOP_LOSS = -25000

# Market data
TENORS = ["2Y", "5Y", "10Y", "30Y"]
DEFAULT_CURRENCY = "USD"

# System settings
GRADIO_PORT = 7860

# Demo/Rate limiting
MAX_RUNS = 5

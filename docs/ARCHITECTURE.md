# Sentinel Architecture

## Data Layer

MarketDataManager
    ↓
HistoryManager
    ↓
Historical Market Database

Responsibilities:
- Download market data
- Store historical data
- Manage history
- Synchronise updates

---

## Analytics Layer

FeatureEngine
    ↓
Feature Registry
    ↓
Feature Modules

Responsibilities:
- Register available features
- Calculate requested features
- Produce reusable market measurements

Current Features

- SMA

Future Features

- EMA
- RSI
- ATR
- MACD
- Bollinger Bands
- Statistical Features
- Fundamental Features

---

## Research Layer (Planned)

Research Memory
Hypothesis Generator
Backtesting Engine
Validation Engine

Responsibilities

- Generate hypotheses
- Test hypotheses
- Rank hypotheses
- Learn from previous research

---

## Decision Layer (Planned)

Risk Assessment
Trade Ranking
Recommendation Engine

Responsibilities

- Rank opportunities
- Recommend Buy / Sell / Hold
- Explain reasoning

---

## Execution Layer (Optional)

Paper Trading
Live Trading

Responsibilities

- Execute validated strategies
- Record execution performance
# AI Coding Agent Instructions for Stock Recommendation System

## Project Overview
This is a quantitative stock recommendation system that combines multiple analysis methods to score stocks on a 100-point scale. The system generates daily reports hosted on GitHub Pages and sends Telegram notifications for market alerts.

## Core Architecture
- **Modular Analyzer System**: Located in `quant_trading/` directory with separate analyzers for different scoring components
- **Scoring Framework**: Valuation (35%) + Technical (25%) + Automation/AI (20%) + Policy (20%) = 100 points
- **Data Pipeline**: yfinance for price data, Yahoo Finance for news sentiment analysis

## Key Components & Patterns

### Scoring System (`quant_trading/`)
- `valuation_analyzer.py`: Fundamental analysis (ROE, margins, growth) - 35 points
- `technical_analyzer_v3.py`: Momentum and trend analysis - 25 points (scaled from 65-point system)
- `automation_analyzer.py`: AI/infrastructure automation benefits - 20 points
- `policy_analyzer.py`: Government policy benefits (CHIPS, IRA, defense) - 20 points
- `news_sentiment_analyzer.py`: TextBlob-based sentiment from recent Yahoo Finance news

### Report Generation (`generate_daily_report_v2.py`)
- Processes NASDAQ 100, S&P 500, and value stock tickers
- Uses concurrent.futures for parallel processing
- Generates HTML reports with sector-based tabs and responsive design
- Top 5 stocks highlighted with detailed buy/sell recommendations

### Configuration Patterns
- **API Keys**: Store in `config.py` (FMP API optional, Telegram required for alerts)
- **Telegram Integration**: Bot token and chat ID required for notifications
- **Ticker Lists**: Separate modules (`sp500_tickers.py`, `nasdaq100_tickers.py`) for different market segments

### Deployment & Automation
- **GitHub Actions**: Daily updates (UTC 9AM-9PM, KST 6PM-4AM) via `.github/workflows/daily-update.yml`
- **Hosting**: GitHub Pages deployment with automatic report publishing
- **Notifications**: Telegram alerts for 14-day rebalancing results and market volatility (±3%)

### Testing & Validation
- **Backtesting**: Use `backtest_strategy.py` for strategy validation
- **Performance Metrics**: Sharpe ratio, win rate, excess returns vs S&P 500
- **Rebalancing**: Weekly portfolio rebalancing with equal weight allocation

## Development Workflow
1. **Local Testing**: Run `python generate_daily_report_v2.py` for report generation
2. **Backtesting**: Execute `python backtest_strategy.py` to validate strategies
3. **Web Server**: Use `python run_web_server.py` for local preview
4. **Configuration**: Copy `config.example.py` to `config.py` and add API keys

## Code Conventions
- **Korean Comments**: Mix of Korean and English documentation
- **Data Period**: Default 2-year history for analysis (`period='2y'`)
- **Error Handling**: Graceful skipping of tickers with insufficient data
- **Scoring Scale**: Individual analyzers return component scores, main script combines them

## Common Patterns
- **Data Validation**: Check `len(df) >= 180` for sufficient historical data
- **Parallel Processing**: Use `concurrent.futures.ThreadPoolExecutor` for ticker analysis
- **HTML Generation**: Direct string concatenation for report templates
- **Telegram Formatting**: HTML parse mode for rich text notifications

## Key Files to Reference
- `quant_trading/stock_recommender.py`: Core scoring logic
- `generate_daily_report_v2.py`: Main report generation pipeline
- `backtest_strategy.py`: Strategy validation framework
- `telegram_notifier.py`: Alert system implementation
- `config.py`: API configuration template
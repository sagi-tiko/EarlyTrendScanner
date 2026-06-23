# Early Trend Detector

Automated EMA200-reclaim scanner across 80 ETFs, with holdings drill-down,
momentum scoring, and EMA overlay charts. Runs hourly via GitHub Actions and
publishes to GitHub Pages.

## Live page

Once GitHub Pages is enabled (Settings → Pages → Source: `main` branch,
folder: `/docs`), the dashboard will be live at:

```
https://<your-username>.github.io/<repo-name>/
```

## How it works

- `ema_scan_v6.py` — the scanner. Pulls price data from Yahoo Finance via
  `yfinance`, evaluates the 6-condition early-trend signal across the ETF
  universe, drills into holdings for any flagged ETF, scores momentum, and
  writes a single self-contained `docs/index.html`.
- `.github/workflows/scan.yml` — GitHub Action that runs the scanner every
  hour, and only commits the new HTML if the flagged ETF list or holdings
  data actually changed (a pure timestamp change is ignored).
- `requirements.txt` — Python dependencies for the Action's runner.

## Manual run

From the Actions tab in GitHub, select **Early Trend Scanner — Hourly Scan &
Publish** → **Run workflow** to trigger an off-schedule run at any time.

## Local run

```bash
pip install -r requirements.txt
python ema_scan_v6.py
```

Output is written to `docs/index.html`. Open it directly in a browser to
preview before pushing.

## Editing the ETF universe

Add new tickers to the `TICKERS` dict (grouped by category) and their top
holdings to the `HOLDINGS` dict, both near the top of `ema_scan_v6.py`. The
ETF Universe tab on the dashboard will pick up new entries automatically on
the next run.

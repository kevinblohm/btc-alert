# BTC Price Drop Alert

Monitors Bitcoin price and sends a Twilio SMS when it drops **10%** from its rolling 24-hour high.

## How It Works

1. Polls CoinGecko every 5 minutes (free, no API key)
2. Tracks a rolling 24-hour high from collected samples
3. When current price is ≥10% below that high → sends SMS via Twilio
4. 1-hour cooldown between alerts to avoid spam

## Quick Start (Local)

```bash
cd btc-alert
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # fill in your real values
python monitor.py
```

## Twilio Setup

1. Sign up at https://www.twilio.com/try-twilio (free trial gives you SMS credits)
2. Get your **Account SID** and **Auth Token** from the console dashboard
3. Get a Twilio phone number (free trial includes one)
4. If on free trial, verify the phone number you want to receive alerts on
5. Put all values in `.env`

## Deploy to Railway

```bash
# Install Railway CLI: npm i -g @railway/cli
railway login
railway init
# Set env vars in Railway dashboard or CLI:
railway variables set TWILIO_ACCOUNT_SID=ACxxx
railway variables set TWILIO_AUTH_TOKEN=xxx
railway variables set TWILIO_FROM_NUMBER=+1xxx
railway variables set ALERT_TO_NUMBER=+1xxx
railway up
```

Railway will build from the Dockerfile and run the worker process.

## Deploy to Oracle Cloud VPS

1. Create a free-tier compute instance (Ubuntu, ARM or AMD)
2. SSH in and run the setup script:
   ```bash
   ssh ubuntu@<your-vps-ip> 'bash -s' < setup-oracle.sh
   ```
3. Copy your files:
   ```bash
   scp monitor.py .env ubuntu@<your-vps-ip>:~/btc-alert/
   ```
4. Start the service:
   ```bash
   ssh ubuntu@<your-vps-ip> 'sudo systemctl start btc-alert'
   ```
5. Check logs:
   ```bash
   ssh ubuntu@<your-vps-ip> 'journalctl -u btc-alert -f'
   ```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | — | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `TWILIO_FROM_NUMBER` | — | Your Twilio phone number |
| `ALERT_TO_NUMBER` | — | Phone number to receive alerts |
| `CHECK_INTERVAL_SECONDS` | 300 | How often to check price (seconds) |
| `DECLINE_THRESHOLD_PERCENT` | 10 | Drop % to trigger alert |
| `ALERT_COOLDOWN_SECONDS` | 3600 | Min time between alerts (seconds) |

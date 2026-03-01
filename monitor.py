"""
Bitcoin Price Drop Alert
Monitors BTC/USD and sends Twilio SMS when price drops 10% from rolling 24h high.
"""

import os
import time
import logging
from datetime import datetime, timezone
from collections import deque

import requests
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TWILIO_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM = os.environ["TWILIO_FROM_NUMBER"]
ALERT_TO = os.environ["ALERT_TO_NUMBER"]

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", 300))  # default 5 min
DECLINE_PCT = float(os.getenv("DECLINE_THRESHOLD_PERCENT", 10))

# How many price samples to keep for rolling high (24h at 5-min intervals = 288)
WINDOW_SIZE = max(1, (24 * 3600) // CHECK_INTERVAL)

# Cooldown between alerts so you don't get spammed (seconds)
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN_SECONDS", 3600))  # 1 hour

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("btc-alert")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_btc_price() -> float | None:
    """Fetch current BTC/USD price from CoinGecko (free, no key needed)."""
    try:
        resp = requests.get(
            COINGECKO_URL,
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["bitcoin"]["usd"]
    except Exception as e:
        log.error("Price fetch failed: %s", e)
        return None


def send_sms(body: str) -> None:
    """Send an SMS via Twilio."""
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=ALERT_TO,
        )
        log.info("SMS sent: sid=%s", msg.sid)
    except Exception as e:
        log.error("SMS send failed: %s", e)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    log.info(
        "Starting BTC monitor  |  threshold=-%s%%  |  interval=%ss  |  window=%s samples",
        DECLINE_PCT, CHECK_INTERVAL, WINDOW_SIZE,
    )

    prices: deque[float] = deque(maxlen=WINDOW_SIZE)
    last_alert_time: float = 0

    while True:
        price = get_btc_price()

        if price is not None:
            prices.append(price)
            rolling_high = max(prices)
            drop_pct = ((rolling_high - price) / rolling_high) * 100

            log.info(
                "BTC $%,.2f  |  24h-high $%,.2f  |  drop %.2f%%",
                price, rolling_high, drop_pct,
            )

            now = time.time()
            if drop_pct >= DECLINE_PCT and (now - last_alert_time) > ALERT_COOLDOWN:
                body = (
                    f"BTC ALERT: Price dropped {drop_pct:.1f}% from 24h high!\n"
                    f"Current: ${price:,.2f}\n"
                    f"24h High: ${rolling_high:,.2f}\n"
                    f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                )
                log.warning("ALERT TRIGGERED — sending SMS")
                send_sms(body)
                last_alert_time = now

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

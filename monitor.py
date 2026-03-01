"""
Bitcoin Price Drop Alert
Monitors BTC/USD and sends Twilio SMS + phone calls when price drops 10%
from rolling 24h high. Sends a daily heartbeat SMS so you know it's alive.
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

# How many phone calls to make on alert (to wake you up)
CALL_COUNT = int(os.getenv("ALERT_CALL_COUNT", 3))
CALL_GAP_SECONDS = int(os.getenv("ALERT_CALL_GAP_SECONDS", 30))

# Daily heartbeat hour in UTC (default 15 = 7am PST / 8am PDT)
HEARTBEAT_HOUR_UTC = int(os.getenv("HEARTBEAT_HOUR_UTC", 15))

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# TwiML for phone call — speaks the alert message
CALL_TWIML_TEMPLATE = (
    '<Response><Say voice="alice" loop="2">'
    "Bitcoin alert! The price has dropped {drop_pct} percent. "
    "Current price is {price} dollars. "
    "The 24 hour high was {high} dollars."
    "</Say></Response>"
)

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


def make_calls(drop_pct: float, price: float, high: float) -> None:
    """Make multiple phone calls via Twilio to wake you up."""
    twiml = CALL_TWIML_TEMPLATE.format(
        drop_pct=f"{drop_pct:.1f}",
        price=f"{price:,.0f}",
        high=f"{high:,.0f}",
    )
    client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

    for i in range(CALL_COUNT):
        try:
            call = client.calls.create(
                twiml=twiml,
                from_=TWILIO_FROM,
                to=ALERT_TO,
            )
            log.info("Call %d/%d initiated: sid=%s", i + 1, CALL_COUNT, call.sid)
        except Exception as e:
            log.error("Call %d/%d failed: %s", i + 1, CALL_COUNT, e)

        if i < CALL_COUNT - 1:
            time.sleep(CALL_GAP_SECONDS)


def send_heartbeat(price: float) -> None:
    """Send daily heartbeat SMS so you know the monitor is alive."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        f"BTC Monitor heartbeat - still running!\n"
        f"BTC: ${price:,.2f}\n"
        f"Threshold: -{DECLINE_PCT}%\n"
        f"Time: {now_utc}"
    )
    send_sms(body)
    log.info("Heartbeat SMS sent")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    log.info(
        "Starting BTC monitor  |  threshold=-%s%%  |  interval=%ss  |  "
        "window=%s samples  |  calls=%d  |  heartbeat=%02d:00 UTC",
        DECLINE_PCT, CHECK_INTERVAL, WINDOW_SIZE, CALL_COUNT, HEARTBEAT_HOUR_UTC,
    )

    prices: deque[float] = deque(maxlen=WINDOW_SIZE)
    last_alert_time: float = 0
    last_heartbeat_date: str = ""

    while True:
        price = get_btc_price()

        if price is not None:
            prices.append(price)
            rolling_high = max(prices)
            drop_pct = ((rolling_high - price) / rolling_high) * 100

            log.info(
                "BTC $%s  |  24h-high $%s  |  drop %.2f%%",
                f"{price:,.2f}", f"{rolling_high:,.2f}", drop_pct,
            )

            now = time.time()
            now_utc = datetime.now(timezone.utc)

            # --- Daily heartbeat ---
            today = now_utc.strftime("%Y-%m-%d")
            if now_utc.hour == HEARTBEAT_HOUR_UTC and today != last_heartbeat_date:
                send_heartbeat(price)
                last_heartbeat_date = today

            # --- Price drop alert ---
            if drop_pct >= DECLINE_PCT and (now - last_alert_time) > ALERT_COOLDOWN:
                body = (
                    f"BTC ALERT: Price dropped {drop_pct:.1f}% from 24h high!\n"
                    f"Current: ${price:,.2f}\n"
                    f"24h High: ${rolling_high:,.2f}\n"
                    f"Time: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}"
                )
                log.warning("ALERT TRIGGERED — sending SMS + %d calls", CALL_COUNT)
                send_sms(body)
                make_calls(drop_pct, price, rolling_high)
                last_alert_time = now

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

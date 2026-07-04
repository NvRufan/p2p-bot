import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

import requests

# --------------------------------------------------------------------------
# Konfiqurasiya
# --------------------------------------------------------------------------

# Token və chat ID artıq kodun içində DEYİL — environment variable-lardan oxunur.
# Render/Railway və s. platformalarda "Environment Variables" bölməsində təyin edin:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ASSET = os.environ.get("P2P_ASSET", "USDT")
FIAT = os.environ.get("P2P_FIAT", "AZN")

BUY_THRESHOLD = float(os.environ.get("BUY_THRESHOLD", "1.71"))   # bundan aşağı -> ucuz alış
SELL_THRESHOLD = float(os.environ.get("SELL_THRESHOLD", "1.75"))  # bundan yuxarı -> satış vaxtı

CHECK_INTERVAL_SEC = int(os.environ.get("CHECK_INTERVAL_SEC", "30"))
REQUEST_TIMEOUT_SEC = 10
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5

HEALTH_CHECK_PORT = int(os.environ.get("PORT", "10000"))

P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

# --------------------------------------------------------------------------
# Loglama
# --------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("p2p_bot")


# --------------------------------------------------------------------------
# Telegram bildirişi
# --------------------------------------------------------------------------

def mesaj_gonder(metn: str) -> None:
    if not TOKEN or not CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN və ya TELEGRAM_CHAT_ID təyin olunmayıb, mesaj göndərilmədi.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": metn},
            timeout=REQUEST_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        logger.info("Telegram bildirişi göndərildi: %s", metn.splitlines()[0])
    except requests.RequestException as e:
        logger.error("Telegram mesajı göndərilə bilmədi: %s", e)


# --------------------------------------------------------------------------
# P2P qiymət sorğusu (retry ilə)
# --------------------------------------------------------------------------

def qiymet_al(trade_type: str) -> Optional[float]:
    """Verilmiş əməliyyat növü (BUY/SELL) üçün ən yaxşı P2P qiymətini qaytarır.
    Uğursuz olarsa None qaytarır."""
    payload = {"asset": ASSET, "fiat": FIAT, "tradeType": trade_type, "rows": 1}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.post(
                P2P_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT_SEC,
            )
            res.raise_for_status()
            body = res.json()
            ads = body.get("data") or []
            if not ads:
                logger.warning("%s üçün heç bir elan tapılmadı.", trade_type)
                return None
            return float(ads[0]["adv"]["price"])

        except requests.RequestException as e:
            logger.warning(
                "%s qiymət sorğusu uğursuz oldu (cəhd %d/%d): %s",
                trade_type, attempt, MAX_RETRIES, e,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error("%s cavabı gözlənilməz formatdadır: %s", trade_type, e)
            return None

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SEC)

    logger.error("%s qiyməti %d cəhddən sonra alına bilmədi.", trade_type, MAX_RETRIES)
    return None


# --------------------------------------------------------------------------
# Əsas monitorinq dövrü
# --------------------------------------------------------------------------

@dataclass
class Veziyyet:
    son_bildirish: Optional[str] = None  # "alis" | "satis" | None


def yoxla(veziyyet: Veziyyet) -> None:
    qiymet_alis = qiymet_al("BUY")
    qiymet_satis = qiymet_al("SELL")

    if qiymet_alis is None or qiymet_satis is None:
        # Bu dövrdə etibarlı məlumat yoxdur, sonrakı dövrü gözlə.
        return

    logger.info("Alış: %.4f %s | Satış: %.4f %s", qiymet_alis, FIAT, qiymet_satis, FIAT)

    if qiymet_alis <= BUY_THRESHOLD and veziyyet.son_bildirish != "alis":
        mesaj_gonder(f"🚨 UCUZ USDT!\nQiymət: {qiymet_alis} {FIAT}")
        veziyyet.son_bildirish = "alis"

    if qiymet_satis >= SELL_THRESHOLD and veziyyet.son_bildirish != "satis":
        mesaj_gonder(f"💰 USDT SATMAQ VAXTIDIR!\nQiymət: {qiymet_satis} {FIAT}")
        veziyyet.son_bildirish = "satis"

    # Qiymətlər normal aralığa qayıdıbsa, yaddaşı sıfırla ki, yenidən bildiriş gələ bilsin.
    if qiymet_alis > BUY_THRESHOLD and qiymet_satis < SELL_THRESHOLD:
        veziyyet.son_bildirish = None


def monitor_dovru() -> None:
    veziyyet = Veziyyet()
    logger.info(
        "Monitorinq başladı: %s/%s | Alış eşiyi <= %.2f | Satış eşiyi >= %.2f | Interval: %ds",
        ASSET, FIAT, BUY_THRESHOLD, SELL_THRESHOLD, CHECK_INTERVAL_SEC,
    )
    while True:
        try:
            yoxla(veziyyet)
        except Exception:
            # Gözlənilməz xətaları da tam log edirik (əvvəlki kimi səssizcə udmuruq),
            # amma bot bu xəta ilə dayanmır, növbəti dövrdə davam edir.
            logger.exception("Yoxlama dövründə gözlənilməz xəta baş verdi.")
        time.sleep(CHECK_INTERVAL_SEC)


# --------------------------------------------------------------------------
# Health-check HTTP serveri (Render və s. üçün)
# --------------------------------------------------------------------------

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format: str, *args) -> None:
        # Health-check sorğularını console-a spam etməsin.
        pass


def run_server() -> None:
    server = HTTPServer(("0.0.0.0", HEALTH_CHECK_PORT), HealthCheckHandler)
    logger.info("Health-check serveri %d portunda işə düşdü.", HEALTH_CHECK_PORT)
    server.serve_forever()


# --------------------------------------------------------------------------
# Giriş nöqtəsi
# --------------------------------------------------------------------------

if __name__ == "__main__":
    if not TOKEN or not CHAT_ID:
        logger.warning(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID environment variable-ları təyin olunmayıb. "
            "Bot işləyəcək, amma Telegram bildirişləri göndərilməyəcək."
        )

    threading.Thread(target=monitor_dovru, daemon=True).start()
    run_server()

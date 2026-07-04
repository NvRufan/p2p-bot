import logging
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
import requests

# Token və Chat ID birbaşa bura yazıldı (heç bir ayara ehtiyac yoxdur)
TOKEN = "8979537285:AAEpvAXbMaw6cPHFm05TVEqafD5z6YIPgzU"
CHAT_ID = "940235559"

BUY_THRESHOLD = 1.71
SELL_THRESHOLD = 1.75
CHECK_INTERVAL_SEC = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("p2p_bot")

def mesaj_gonder(metn: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": metn}, timeout=10)
    except: pass

@dataclass
class Veziyyet:
    son_bildirish: Optional[str] = None

def monitor():
    veziyyet = Veziyyet()
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    while True:
        try:
            # Alış
            res_a = requests.post(url, json={"asset": "USDT", "fiat": "AZN", "tradeType": "BUY", "rows": 1}, timeout=10).json()
            q_alis = float(res_a["data"][0]["adv"]["price"])
            
            # Satış
            res_s = requests.post(url, json={"asset": "USDT", "fiat": "AZN", "tradeType": "SELL", "rows": 1}, timeout=10).json()
            q_satis = float(res_s["data"][0]["adv"]["price"])

            if q_alis <= BUY_THRESHOLD and veziyyet.son_bildirish != "alis":
                mesaj_gonder(f"🚨 UCUZ USDT! {q_alis} AZN")
                veziyyet.son_bildirish = "alis"
            elif q_satis >= SELL_THRESHOLD and veziyyet.son_bildirish != "satis":
                mesaj_gonder(f"💰 SATMAQ VAXTIDIR! {q_satis} AZN")
                veziyyet.son_bildirish = "satis"
            elif q_alis > BUY_THRESHOLD and q_satis < SELL_THRESHOLD:
                veziyyet.son_bildirish = None
        except: pass
        time.sleep(CHECK_INTERVAL_SEC)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers()

if __name__ == "__main__":
    threading.Thread(target=monitor, daemon=True).start()
    HTTPServer(("0.0.0.0", 10000), HealthCheckHandler).serve_forever()

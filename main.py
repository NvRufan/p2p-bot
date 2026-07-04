import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests

TOKEN = "8979537285:AAEpvAXbMaw6cPHFm05TVEqafD5z6YIPgzU"
CHAT_ID = "940235559"

def mesaj_gonder(metn):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": metn})
    except:
        pass

def yoxla():
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
    }
    # Alış yoxlanışı
    try:
        res = requests.post(url, json={
            "asset": "USDT", "fiat": "AZN", "page": 1, "rows": 1, "tradeType": "BUY"
        }, headers=headers).json()
        if res.get("data"):
            q = float(res["data"][0]["adv"]["price"])
            if q <= 1.72:
                mesaj_gonder(f"🚨 UCUZ USDT!\nQiymət: {q} AZN")
    except:
        pass
        
    # Satış yoxlanışı
    try:
        res = requests.post(url, json={
            "asset": "USDT", "fiat": "AZN", "page": 1, "rows": 1, "tradeType": "SELL"
        }, headers=headers).json()
        if res.get("data"):
            q = float(res["data"][0]["adv"]["price"])
            if q >= 1.74:
                mesaj_gonder(f"💰 USDT SATMAQ VAXTIDIR!\nQiymət: {q} AZN")
    except:
        pass

def loop():
    print("Gözətçi işə düşdü...")
    while True:
        yoxla()
        time.sleep(5)

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    run_server()

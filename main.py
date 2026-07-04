import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests

TOKEN = "8979537285:AAEpvAXbMaw6cPHFm05TVEqafD5z6YIPgzU"
CHAT_ID = "940235559"

son_veziyyet = None  

def mesaj_gonder(metn):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": metn})
    except Exception as e:
        print("Mesaj göndərmə xətası:", e)

def yoxla():
    global son_veziyyet
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }
    
    data_alis = {
        "asset": "USDT", "fiat": "AZN", "merchantCheck": False,
        "page": 1, "rows": 1, "payTypes": [], "publisherType": None, "tradeType": "BUY"
    }
    
    data_satis = {
        "asset": "USDT", "fiat": "AZN", "merchantCheck": False,
        "page": 1, "rows": 1, "payTypes": [], "publisherType": None, "tradeType": "SELL"
    }

    while True:
        try:
            res_alis = requests.post(url, json=data_alis, headers=headers, timeout=10).json()
            if res_alis.get("data"):
                en_ucuz_alis = float(res_alis["data"][0]["adv"]["price"])
                # Qiymət limiti 1.71 edildi
                if en_ucuz_alis <= 1.71 and son_veziyyet != "ucuz":
                    mesaj_gonder(f"🚨 UCUZ USDT!\nQiymət: {en_ucuz_alis} AZN")
                    son_veziyyet = "ucuz"
                    
            res_satis = requests.post(url, json=data_satis, headers=headers, timeout=10).json()
            if res_satis.get("data"):
                en_baha_satis = float(res_satis["data"][0]["adv"]["price"])
                if en_baha_satis >= 2.00 and son_veziyyet != "baha":
                    mesaj_gonder(f"💰 USDT SATMAQ VAXTIDIR!\nQiymət: {en_baha_satis} AZN")
                    son_veziyyet = "baha"
            
            if 'en_ucuz_alis' in locals() and 'en_baha_satis' in locals():
                # Normala qayıtma şərti də 1.71-ə uyğunlaşdırıldı
                if en_ucuz_alis > 1.71 and en_baha_satis < 2.00:
                    son_veziyyet = None

        except Exception as e:
            print("P2P xətası:", e)
            
        time.sleep(15)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Live")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=yoxla)
    t.daemon = True
    t.start()
    run_server()

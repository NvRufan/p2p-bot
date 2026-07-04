import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests

TOKEN = "8979537285:AAEpvAXbMaw6cPHFm05TVEqafD5z6YIPgzU"
CHAT_ID = "940235559"

# Siqnalların təkrarlanmaması üçün son vəziyyət yaddaşı
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
    
    # AZN ilə USDT alış elanları üçün data
    data_alis = {
        "asset": "USDT", "fiat": "AZN", "merchantCheck": False,
        "page": 1, "rows": 1, "payTypes": [], "publisherType": None, "tradeType": "BUY"
    }
    
    # AZN ilə USDT satış elanları üçün data
    data_satis = {
        "asset": "USDT", "fiat": "AZN", "merchantCheck": False,
        "page": 1, "rows": 1, "payTypes": [], "publisherType": None, "tradeType": "SELL"
    }

    while True:
        try:
            # 1. Ən ucuz alış qiymətini yoxla
            res_alis = requests.post(url, json=data_alis, headers=headers, timeout=10).json()
            if res_alis.get("data"):
                en_ucuz_alis = float(res_alis["data"][0]["adv"]["price"])
                
                if en_ucuz_alis <= 1.72 and son_veziyyet != "ucuz":
                    mesaj_gonder(f"🚨 UCUZ USDT!\nQiymət: {en_ucuz_alis} AZN")
                    son_veziyyet = "ucuz"
                    
            # 2. Ən baha satış qiymətini yoxla
            res_satis = requests.post(url, json=data_satis, headers=headers, timeout=10).json()
            if res_satis.get("data"):
                en_baha_satis = float(res_satis["data"][0]["adv"]["price"])
                
                if en_baha_satis >= 2.00 and son_veziyyet != "baha":
                    mesaj_gonder(f"💰 USDT SATMAQ VAXTIDIR!\nQiymət: {en_baha_satis} AZN")
                    son_veziyyet = "baha"
            
            # Əgər qiymətlər normala qayıtsa, yaddaşı sıfırla ki, yenidən siqnal verə bilsin
            if 'en_ucuz_alis' in locals() and 'en_baha_satis' in locals():
                if en_ucuz_alis > 1.72 and en_baha_satis < 2.00:
                    son_veziyyet = None

        except Exception as e:
            print("P2P yoxlama xətası:", e)
            
        time.sleep(10)  # Hər 10 saniyədən bir yoxlayır

# Render-in sönməməsi üçün sadə HTTP Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    # P2P izləməni arxa fonda başladırıq
    t = threading.Thread(target=yoxla)
    t.daemon = True
    t.start()
    
    # Web serveri əsas axında başladırıq
    run_server()

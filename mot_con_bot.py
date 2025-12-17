import json
import os
import time
import requests
from datetime import datetime
import sys

# Import scrapers
from scraper_1 import (
    fetch_vcb_news, fetch_all_vietinbank, fetch_bidv_data, fetch_tcb_news, 
    fetch_mch_news, fetch_vpb_news, fetch_vgi_news, fetch_hpg_news, 
    fetch_acv_news, fetch_fpt_news, fetch_gas_news, fetch_lpb_news, 
    fetch_vnm_news, fetch_vjc_news, fetch_hdb_news, fetch_acb_news, 
    fetch_mwg_news, fetch_msn_group_news, fetch_gvr_news, fetch_mbb_news
)

# --- CẤU HÌNH ---
try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError:
    print("Lỗi: Không tìm thấy BOT_TOKEN hoặc CHAT_ID.")
    print("Hãy đảm bảo đã set Secrets trong GitHub Actions.")
    sys.exit(1) # Dừng chương trình nếu không có key
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data_news.json")

# --- CẤU HÌNH CHẾ ĐỘ CHẠY ---
FORCE_ALERT_MODE = False   # False = Không ép gửi tin cũ

# 👇👇👇 [QUAN TRỌNG] CÔNG TẮC BẬT/TẮT GỬI TIN 👇👇👇
# True  = Gửi tin nhắn Telegram bình thường (Chế độ chạy thật)
# False = CHỈ LƯU VÀO JSON, KHÔNG GỬI TIN (Chế độ chạy ngầm/cập nhật data)
ENABLE_TELEGRAM = True    
# 👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆

STOCK_MAP = {
    "VCB": fetch_vcb_news, "CTG": fetch_all_vietinbank, "BID": fetch_bidv_data,
    "TCB": fetch_tcb_news, "MCH": fetch_mch_news, "VPB": fetch_vpb_news,
    "VGI": fetch_vgi_news, "HPG": fetch_hpg_news, "ACV": fetch_acv_news,
    "FPT": fetch_fpt_news, "GAS": fetch_gas_news, "LPB": fetch_lpb_news,
    "VNM": fetch_vnm_news, "VJC": fetch_vjc_news, "HDB": fetch_hdb_news,
    "ACB": fetch_acb_news, "MWG": fetch_mwg_news, "MSN": fetch_msn_group_news,
    "GVR": fetch_gvr_news, "MBB": fetch_mbb_news
}

def load_database():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {}

def save_database(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Lỗi lưu file: {e}")

def send_telegram(message):
    # Nếu tắt công tắc thì return luôn, không gửi gì cả
    if not ENABLE_TELEGRAM: 
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except: pass

def format_message(stock_code, item):
    date_info = item.get('date', datetime.now().year)
    return (
        f"🚨 <b>{stock_code} - TIN MỚI!</b>\n"
        f"📅 {date_info}\n"
        f"📝 <b>{item['title']}</b>\n"
        f"🔗 <a href='{item['link']}'>Xem chi tiết</a>\n"
        f"#{stock_code}"
    )

def main():
    print(f"--- 🤖 BOT RUNNING | SEND_TELEGRAM={ENABLE_TELEGRAM} ---")
    db_data = load_database()
    
    is_first_run = len(db_data) == 0
    total_new = 0

    for stock_code, scraper_func in STOCK_MAP.items():
        print(f"\n🔍 {stock_code}...", end="")
        seen_ids = set(db_data.get(stock_code, []))
        
        try:
            new_items = scraper_func(seen_ids)
            
            if new_items:
                print(f" ✅ {len(new_items)} tin mới!", end="")
                if stock_code not in db_data: db_data[stock_code] = []
                
                for item in new_items:
                    # 1. Thêm vào bộ nhớ
                    db_data[stock_code].append(item['id'])
                    
                    # 2. Logic Gửi tin (Có kiểm tra công tắc ENABLE_TELEGRAM)
                    if ENABLE_TELEGRAM and ((not is_first_run) or FORCE_ALERT_MODE):
                        print(" -> 📨", end="")
                        send_telegram(format_message(stock_code, item))
                        time.sleep(1)
                
                # 3. LƯU FILE NGAY (Quan trọng: Dù gửi hay không gửi cũng phải lưu)
                save_database(db_data)
                total_new += len(new_items)
            else:
                print(" 💤", end="")
                
        except Exception as e:
            print(f" ❌ Lỗi: {e}", end="")
            save_database(db_data)

    print(f"\n\n🏁 XONG. Tổng cộng {total_new} tin mới đã được cập nhật vào Database.")

if __name__ == "__main__":
    main()
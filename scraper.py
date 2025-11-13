import requests
from bs4 import BeautifulSoup
import json
import os       # Thêm os
import sys      # Thêm sys
import time
import datetime # Thư viện mới để xử lý ngày giờ

# --- CẤU HÌNH CỐ ĐỊNH ---
VNEXPRESS_URL = 'https://vnexpress.net/the-gioi'
TUOI_TRE_URL = 'https://www.24h.com.vn/tin-tuc-quoc-te-c415.html'
KEYWORDS = ['nga', 'ukraine']
STATE_FILE = 'processed_links.json'

# --- LẤY BÍ MẬT TỪ GITHUB (Thay vì dán key) ---
try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError:
    print("Lỗi: Không tìm thấy BOT_TOKEN hoặc CHAT_ID.")
    print("Hãy đảm bảo đã set Secrets trong GitHub Actions.")
    sys.exit(1) # Dừng chương trình nếu không có key

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
}

# --- CÁC HÀM CHỨC NĂNG (Giữ nguyên) ---

def load_processed_links():
    """
    Tải links đã xử lý. (Phiên bản "Nhớ Vĩnh Cửu")
    """
    try:
        with open(STATE_FILE, 'r') as f:
            processed_list = json.load(f)
            print(f"Đã tải {len(processed_list)} links từ bộ nhớ vĩnh cửu.")
            return set(processed_list)
            
    except (FileNotFoundError, json.JSONDecodeError):
        # Nếu file không tồn tại hoặc rỗng, trả về set rỗng
        print(f"Không tìm thấy file {STATE_FILE} hoặc file rỗng. Bắt đầu bộ nhớ mới.")
        return set()

def save_processed_links(links_set):
    with open(STATE_FILE, 'w') as f:
        json.dump(list(links_set), f, indent=2)
    print(f"\nĐã lưu {len(links_set)} links vào {STATE_FILE}")

# --- HÀM SEND_TELEGRAM (ĐÃ NÂNG CẤP) ---
def send_telegram_message(text):
    """Gửi tin (NÂNG CẤP: Tự động xử lý lỗi 429 rate limit)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    # Thử gửi, tối đa 5 lần
    for i in range(5): 
        try:
            response = requests.post(url, data=payload, timeout=20)
            
            if response.status_code == 200:
                print("Gửi tin nhắn thành công!")
                return # Gửi thành công, thoát hàm
                
            elif response.status_code == 429:
                # Bị rate limit
                error_data = response.json()
                # Lấy tg retry, mặc định 5s nếu không đọc được
                retry_after = error_data.get('parameters', {}).get('retry_after', 5) 
                
                print(f"LỖI 429: Bị rate limit. Tự động chờ {retry_after + 1} giây...")
                time.sleep(retry_after + 1) # Chờ và vòng lặp sẽ thử lại
                
            else:
                # Lỗi khác (400, 404, 500...)
                print(f"LỖI lạ khi gửi tin: {response.status_code} - {response.text}")
                return # Lỗi lạ, không thử lại
                
        except Exception as e:
            print(f"LỖI ngoại lệ khi gửi tin: {e}")
            time.sleep(5) # Nghỉ 5s nếu có lỗi mạng
    
    print(f"LỖI: Không thể gửi tin nhắn sau 5 lần thử.")

# --- Các hàm scrape (KHÔNG THAY ĐỔI) ---

def scrape_vnexpress():
    print("Đang lấy tin từ VnExpress...")
    articles = []
    try:
        response = requests.get(VNEXPRESS_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('article.item-news')
        for item in items.copy():
            title_tag = item.select_one('h3.title-news a')
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                articles.append({'title': title, 'link': link, 'source': 'VnExpress'})
    except Exception as e:
        print(f"Lỗi khi scrape VnExpress: {e}")
    return articles

def scrape_24h():
    print("Đang lấy tin từ 24h.com.vn (Phương pháp URL)...")
    articles = []
    base_url = "https://www.24h.com.vn"
    try:
        response = requests.get(TUOI_TRE_URL, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = soup.select('a')
        found_links = set()
        for link_tag in all_links:
            if not link_tag.has_attr('href'):
                continue
            link = link_tag['href']
            if "-c415a" in link and ".html" in link and link not in found_links:
                title = link_tag.get_text(strip=True)
                if not title or len(title) < 15:
                    continue
                if not link.startswith('http'):
                    link = base_url + link
                articles.append({'title': title, 'link': link, 'source': '24h.com.vn'})
                found_links.add(link) 
    except Exception as e:
        print(f"Lỗi khi scrape 24h.com.vn: {e}")
    print(f"Tìm thấy {len(articles)} bài từ 24h.com.vn.")
    return articles

# --- HÀM CHẠY CHÍNH (Giữ nguyên) ---

def main():
    print("Bắt đầu chu trình chạy...")

    now = datetime.datetime.now()
    hashtag = f"#{now.strftime('%d_%m_%Y_%H')}h" 
    print(f"Hashtag cho lần chạy này: {hashtag}")

    processed_links = load_processed_links()
    print(f"Đã tải {len(processed_links)} links đã xử lý (của hôm nay).")

    all_articles = scrape_vnexpress() + scrape_24h()
    print(f"Tìm thấy tổng cộng {len(all_articles)} bài báo.")

    new_articles_to_send = []
    new_links_to_save = set(processed_links) 

    for article in all_articles:
        if article['link'] not in processed_links:
            new_links_to_save.add(article['link'])
            title_lower = article['title'].lower()
            if any(keyword.lower() in title_lower for keyword in KEYWORDS):
                print(f"[PHÁT HIỆN] {article['title']}")
                new_articles_to_send.append(article)
                
    if not new_articles_to_send:
        print("Không có bài báo mới nào chứa từ khóa.")
    else:
        print(f"Tìm thấy {len(new_articles_to_send)} bài mới, đang gửi thông báo...")
        for article in reversed(new_articles_to_send):
            message = (
                f"📰 <b>{article['source']} - Tin tức mới</b>\n\n"
                f"<b>{article['title']}</b>\n\n"
                f"{article['link']}\n\n"
                f"<i>{hashtag}</i>" 
            )
            send_telegram_message(message)
            # Chúng ta vẫn giữ 1s nghỉ "lịch sự" giữa các tin
            time.sleep(1) 
            
    save_processed_links(new_links_to_save)
    print("Hoàn tất chu trình.")

if __name__ == "__main__":
    main()
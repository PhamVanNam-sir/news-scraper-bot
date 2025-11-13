import requests
from bs4 import BeautifulSoup
import json
import os       # Thêm os
import sys      # Thêm sys
import time

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
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_processed_links(links_set):
    with open(STATE_FILE, 'w') as f:
        json.dump(list(links_set), f, indent=2)
    print(f"Đã lưu {len(links_set)} links vào {STATE_FILE}")


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print(f"Gửi tin nhắn thành công!")
        else:
            print(f"LỖI khi gửi tin: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"LỖI ngoại lệ khi gửi tin: {e}")

def scrape_vnexpress():
    print("Đang lấy tin từ VnExpress...")
    articles = []
    try:
        response = requests.get(VNEXPRESS_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('article.item-news')
        for item in items:
            title_tag = item.select_one('h3.title-news a')
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                articles.append({'title': title, 'link': link, 'source': 'VnExpress'})
    except Exception as e:
        print(f"Lỗi khi scrape VnExpress: {e}")
    return articles

def scrape_24h():
    """Lấy tin từ 24h.com.vn. (Phương pháp URL - Đã hoạt động)"""
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
    processed_links = load_processed_links()
    print(f"Đã tải {len(processed_links)} links đã xử lý từ file {STATE_FILE}.")
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
                f"{article['link']}"
            )
            send_telegram_message(message)
            time.sleep(1) 
    save_processed_links(new_links_to_save)
    print("Hoàn tất chu trình.")

if __name__ == "__main__":
    main()
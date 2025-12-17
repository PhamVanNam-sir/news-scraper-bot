import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_tcx_news(seen_ids):
    """
    Hàm cào Techcom Securities (TCX/TCBS).
    - Method: POST (Form Data).
    - Response: JSON chứa HTML string.
    - Logic: Parse JSON -> Lấy HTML -> Parse BeautifulSoup.
    """
    
    current_year = str(datetime.now().year)
    
    # URL Endpoint xử lý AJAX
    api_url = "https://www.tcbs.com.vn/wp-content/custom-ajax.php"
    
    # Danh sách Payload cấu hình cho từng mục
    categories = [
        {
            "name": "Công bố thông tin",
            "slug": "cong-bo-thong-tin"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "slug": "dai-hoi-dong-co-dong"
        },
        {
            "name": "Báo cáo tài chính",
            "slug": "bao-cao-tai-chinh"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest", # Giả lập AJAX call
        "Origin": "https://www.tcbs.com.vn",
        "Referer": "https://www.tcbs.com.vn/"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét TCX (Năm {current_year}) ---")

    for cat in categories:
        # Quét trang 0 và 1 (thường AJAX load more tính từ 0)
        # Vì filter theo năm 2025 nên server đã lọc sẵn, ta không cần loop quá nhiều trang
        for page in range(2): 
            # Cấu trúc Payload chuẩn như ảnh bạn gửi
            payload = {
                "action": "load_more_posts",
                "page": str(page),
                "types": "investor_relations",
                "category_slug": cat["slug"],
                "search_keywords": "",
                "search_year": current_year, # Server tự lọc năm
                "search_month": "-1"
            }
            
            try:
                # Gửi POST request
                response = session.post(api_url, headers=headers, data=payload, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[TCX] Lỗi kết nối {cat['name']}: {response.status_code}")
                    break
                
                # BƯỚC 1: Parse JSON để lấy cục HTML
                try:
                    json_data = response.json()
                    # Dựa vào ảnh 4, HTML nằm trong key 'html' hoặc đôi khi trả về trực tiếp nếu cấu hình lạ
                    # Nhưng thường WordPress trả về {"success": true, "html": "..."} hoặc chỉ {"html": "..."}
                    # Ta lấy linh động:
                    html_source = json_data.get("html") or json_data.get("data")
                    
                    # Nếu hết tin, html_source sẽ rỗng hoặc là chuỗi ""
                    if not html_source: 
                        break 
                        
                except json.JSONDecodeError:
                    # Trường hợp server trả về lỗi PHP hoặc string raw
                    print(f"[TCX] Response không phải JSON tại {cat['name']}")
                    break

                # BƯỚC 2: Dùng BS4 xử lý cục HTML đó
                soup = BeautifulSoup(html_source, 'html.parser')
                
                # Selector dựa trên ảnh 3 (div class="custom-post-item-news")
                items = soup.select('.custom-post-item-news')
                
                if not items:
                    break # Không có bài nào
                
                count_in_page = 0
                for item in items:
                    # 1. Lấy Link & Title (trong thẻ h2 > a)
                    h2_tag = item.find('h2')
                    if not h2_tag: continue
                    
                    a_tag = h2_tag.find('a')
                    if not a_tag: continue
                    
                    link = a_tag.get('href')
                    # Title nằm trong thẻ a, Python requests.json() đã tự decode unicode (\u...)
                    title = a_tag.get_text(strip=True)
                    
                    if not link: continue
                    
                    # Fix link nếu thiếu domain (đề phòng)
                    if not link.startswith('http'):
                        link = f"https://www.tcbs.com.vn{link}"

                    # 2. Lấy Ngày (div class="post-date")
                    date_tag = item.select_one('.post-date')
                    date_str = date_tag.get_text(strip=True) if date_tag else current_year
                    
                    # 3. Check trùng
                    news_id = link
                    if news_id in seen_ids: continue
                    if any(x['id'] == news_id for x in new_items): continue

                    new_items.append({
                        "source": f"TCX - {cat['name']}",
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_page += 1
                
                # Nếu page này không có tin nào -> Dừng loop
                if count_in_page == 0:
                    break
                    
                time.sleep(0.5)

            except Exception as e:
                print(f"[TCX] Lỗi xử lý {cat['name']}: {e}")
                break

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_stb_news(seen_ids):
    """
    Hàm cào Sacombank (STB).
    - Link 1 (CBTT): Key 'data' -> 'downloadPath'
    - Link 2 (BCTC): Key 'data' -> 'documents' -> 'urlFinancialReportStatements'
    - Link 3 (ĐHĐCĐ): Key 'news' -> 'downloadUrl'
    """
    
    current_year = datetime.now().year
    domain = "https://www.sacombank.com.vn"
    
    # Cấu hình 3 endpoint
    endpoints = [
        {
            "name": "Công bố thông tin",
            "url": "https://www.sacombank.com.vn/trang-chu/nha-dau-tu/cong-bo-thong-tin/_jcr_content/root/container/container/shareholdernotice.sacom.shnotice.json",
            "type": "CBTT"
        },
        {
            "name": "Báo cáo tài chính",
            "url": "https://www.sacombank.com.vn/trang-chu/nha-dau-tu/bao-cao/_jcr_content/root/container/container/reportlisting.sacom.reportlisting.financial.json",
            "type": "FINANCE"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://www.sacombank.com.vn/trang-chu/nha-dau-tu/dai-hoi-dong-co-dong/_jcr_content/root/container/container/shareholdercongress.sacom.shareholder.shareholder-congress.json",
            "type": "AGM"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét Sacombank (Năm {current_year}) ---")

    for ep in endpoints:
        try:
            # print(f"   >> Đang tải: {ep['name']}...")
            response = session.get(ep['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[STB] Lỗi kết nối {ep['name']}: {response.status_code}")
                continue

            json_data = response.json()
            
            # --- XỬ LÝ TỪNG LOẠI JSON ---
            
            # 1. LOẠI CBTT (Shareholder Notice)
            if ep['type'] == "CBTT":
                items = json_data.get("data", [])
                for item in items:
                    title = item.get("title")
                    link = item.get("downloadPath")
                    date_raw = item.get("date") # "Nov 28, 2025, 12:00:00 AM"
                    
                    if not link or not title: continue
                    
                    # Parse ngày
                    date_str = str(current_year)
                    if date_raw:
                        try:
                            # Parse format: Nov 28, 2025...
                            dt_obj = datetime.strptime(date_raw.split(",")[0] + ", " + date_raw.split(",")[1], "%b %d, %Y")
                            if dt_obj.year != current_year: continue
                            date_str = dt_obj.strftime("%d/%m/%Y")
                        except: pass
                    
                    # Ghép domain
                    full_link = f"{domain}{link}"
                    
                    # Lưu
                    news_id = full_link
                    if news_id in seen_ids: continue
                    if any(x['id'] == news_id for x in new_items): continue
                    
                    new_items.append({
                        "source": f"STB - {ep['name']}",
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": full_link
                    })

            # 2. LOẠI FINANCE (Báo cáo tài chính)
            elif ep['type'] == "FINANCE":
                # Cấu trúc: data -> list -> documents -> item
                groups = json_data.get("data", [])
                for group in groups:
                    docs = group.get("documents", [])
                    for doc in docs:
                        title = doc.get("reportTitle")
                        link = doc.get("urlFinancialReportStatements")
                        
                        if not link or not title: continue
                        
                        # Loại Finance này không có field date cụ thể trong item
                        # Ta lọc bằng tiêu đề hoặc lấy năm từ root (nếu cần)
                        # Ở đây lọc tiêu đề chứa năm hiện tại cho chắc
                        if str(current_year) not in title: continue

                        full_link = f"{domain}{link}"
                        
                        news_id = full_link
                        if news_id in seen_ids: continue
                        if any(x['id'] == news_id for x in new_items): continue
                        
                        new_items.append({
                            "source": f"STB - {ep['name']}",
                            "id": news_id,
                            "title": title,
                            "date": str(current_year),
                            "link": full_link
                        })

            # 3. LOẠI AGM (Đại hội đồng cổ đông)
            elif ep['type'] == "AGM":
                # Cấu trúc: news -> list
                items = json_data.get("news", [])
                for item in items:
                    title = item.get("title")
                    link = item.get("downloadUrl")
                    date_raw = item.get("date") # "Apr 21, 2025..."
                    year_val = item.get("year")
                    
                    if not link or not title: continue
                    
                    # Check năm
                    if year_val and int(year_val) != current_year:
                        continue
                        
                    # Parse ngày hiển thị
                    date_str = str(current_year)
                    if date_raw:
                        try:
                            dt_obj = datetime.strptime(date_raw.split(",")[0] + ", " + date_raw.split(",")[1], "%b %d, %Y")
                            date_str = dt_obj.strftime("%d/%m/%Y")
                        except: pass

                    full_link = f"{domain}{link}"
                    
                    news_id = full_link
                    if news_id in seen_ids: continue
                    if any(x['id'] == news_id for x in new_items): continue
                    
                    new_items.append({
                        "source": f"STB - {ep['name']}",
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": full_link
                    })

            time.sleep(0.5)

        except Exception as e:
            print(f"[STB] Lỗi tại {ep['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_hvn_news(seen_ids):
    """
    Hàm cào Vietnam Airlines (HVN).
    - Endpoint: .asmx WebAPI.
    - Response: { "d": "JSON_STRING" } -> Cần json.loads 2 lần.
    """
    
    current_year = str(datetime.now().year)
    domain = "https://www.vietnamairlines.com"
    
    # Cấu hình 2 endpoint
    endpoints = [
        {
            "name": "Đại hội cổ đông (Tin tức)",
            "url": "https://www.vietnamairlines.com/WebAPI/CD/CDService.asmx/ListNewsWithDate",
            "type": "NEWS",
            # Payload Link 1
            "payload": {
                "id": "{9539FC34-7AE2-44DE-80E2-7CF9D04742F4}",
                "nameLanguage": "vi-VN",
                "currentPage": "1", # Lấy trang 1 là đủ
                "pageSize": "10",   # Tăng nhẹ lên 10 để bao quát
                "group": "4",
                "catergoryId": "0",
                "subjectId": "0",
                "sortorder": ""
            }
        },
        {
            "name": "Báo cáo tài chính (Download)",
            "url": "https://www.vietnamairlines.com/WebAPI/CD/CDService.asmx/ListDownload",
            "type": "DOWNLOAD",
            # Payload Link 2
            "payload": {
                "id": "{F3056328-8000-4FE9-A779-E537BF70DC14}",
                "nameLanguage": "vi-VN",
                "currentPage": "1",
                "pageSize": "10",
                "group": "4",
                "catergoryId": "0",
                "subjectId": "0"
            }
        }
    ]
    
    # Header quan trọng cho ASMX
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8" 
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét Vietnam Airlines (Năm {current_year}) ---")

    for ep in endpoints:
        try:
            # Gửi request POST với payload JSON
            response = session.post(ep['url'], headers=headers, json=ep['payload'], timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[HVN] Lỗi kết nối {ep['name']}: {response.status_code}")
                continue

            # --- BÓC TÁCH JSON 2 LỚP ---
            try:
                # Lớp 1: Lấy wrapper
                wrapper = response.json()
                inner_json_str = wrapper.get("d")
                
                if not inner_json_str:
                    continue
                    
                # Lớp 2: Parse string bên trong 'd'
                real_data = json.loads(inner_json_str)
                
            except Exception as e:
                print(f"[HVN] Lỗi parse JSON {ep['name']}: {e}")
                continue

            # --- XỬ LÝ DỮ LIỆU ---
            items = []
            if ep['type'] == "NEWS":
                items = real_data.get("NewsWithDates", [])
            elif ep['type'] == "DOWNLOAD":
                items = real_data.get("DownloadItem", []) # Dựa vào snippet bạn gửi
            
            for item in items:
                title = item.get("Title")
                if not title: continue

                # Xử lý Link & Date tùy loại
                link = ""
                date_str = current_year
                
                if ep['type'] == "NEWS":
                    link = item.get("NewsWithDateLink")
                    # Lấy ngày từ CreateDate: "26/06/2025"
                    raw_date = item.get("CreateDate")
                    if raw_date:
                        date_str = raw_date
                        # Filter năm
                        if str(current_year) not in raw_date:
                            continue
                
                elif ep['type'] == "DOWNLOAD":
                    link = item.get("Link")
                    # Loại này không có field Date trong snippet
                    # Ta filter bằng cách check Title hoặc Link có chứa "2025" không
                    check_str = (title + str(link)).lower()
                    if str(current_year) not in check_str:
                         # Nếu không thấy năm hiện tại trong tên file/link -> Bỏ qua cho an toàn
                         continue

                if not link: continue
                
                # Ghép domain nếu cần
                if not link.startswith("http"):
                    full_link = f"{domain}{link}"
                else:
                    full_link = link
                
                # Check trùng
                news_id = full_link
                if news_id in seen_ids: continue
                if any(x['id'] == news_id for x in new_items): continue

                new_items.append({
                    "source": f"HVN - {ep['name']}",
                    "id": news_id,
                    "title": title,
                    "date": date_str,
                    "link": full_link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[HVN] Exception tại {ep['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_gee_news(seen_ids):
    """
    Hàm cào Gelex Electric (GEE) - V3 Final.
    - Sửa lỗi lấy tin 2024: Siết chặt format ngày dd-mm-yyyy.
    - Sửa lỗi BCTC: Bỏ params "?nam=..." để load mặc định năm hiện tại.
    - Map cột BCTC chuẩn: Tên, Q1, Q2, Q3, Q4.
    """
    
    current_year = str(datetime.now().year)
    
    configs = [
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://gelex-electric.com/doc-cat/tai-lieu-dai-hoi-dong-cd",
            "type": "LIST"
        },
        {
            "name": "Công bố thông tin",
            "url": "https://gelex-electric.com/doc-cat/cong-bo-thong-tin-2",
            "type": "LIST"
        },
        {
            "name": "Báo cáo tài chính",
            "url": "https://gelex-electric.com/doc-cat/bao-cao-tai-chinh",
            "type": "TABLE"
            # ĐÃ BỎ PARAMS GÂY LỖI
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét GEE (Năm {current_year}) ---")

    for cfg in configs:
        try:
            # print(f"   >> Đang tải: {cfg['name']}...")
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[GEE] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # ==========================================================
            # PARSER 1: DẠNG LIST (Tin tức, ĐHĐCĐ)
            # ==========================================================
            if cfg['type'] == "LIST":
                items = soup.select('.report-item')
                
                for item in items:
                    # 1. LẤY NGÀY & LỌC CỨNG (Quan trọng)
                    date_tag = item.select_one('.entry-date')
                    date_str = ""
                    if date_tag:
                        raw_date = date_tag.get_text(strip=True) # VD: 15-03-2024
                        
                        # Fix lỗi lấy nhầm 2024: Check string trực tiếp trước
                        if current_year not in raw_date:
                            continue # Bỏ qua ngay nếu không chứa "2025"
                            
                        # Format lại cho đẹp
                        date_str = raw_date.replace("-", "/")
                    else:
                        # Không có ngày -> Bỏ qua cho an toàn
                        continue

                    # 2. LẤY LINK (Ưu tiên link tải, fallback sang link bài viết)
                    # Link bài viết (luôn có)
                    title_a = item.select_one('.title a')
                    if not title_a: continue
                    title_link = title_a.get('href')
                    title = title_a.get_text(strip=True)
                    
                    # Link download (có thể rỗng href="")
                    dl_a = item.select_one('.report-item-link a')
                    dl_link = dl_a.get('href') if dl_a else ""

                    # Logic chọn link: Nếu link download xịn (dài > 5 ký tự) thì lấy, ko thì lấy link bài
                    final_link = dl_link if (dl_link and len(dl_link) > 5) else title_link
                    
                    if not final_link: continue
                    
                    # 3. Check trùng
                    if final_link in seen_ids: continue
                    if any(x['id'] == final_link for x in new_items): continue
                    
                    new_items.append({
                        "source": f"GEE - {cfg['name']}",
                        "id": final_link,
                        "title": title,
                        "date": date_str,
                        "link": final_link
                    })

            # ==========================================================
            # PARSER 2: DẠNG TABLE (Báo cáo tài chính)
            # ==========================================================
            elif cfg['type'] == "TABLE":
                table = soup.select_one('.table-report')
                
                # Nếu không có bảng (do chưa có tin 2025 hoặc lỗi load) -> Skip
                if not table: 
                    # print(f"[GEE] Không thấy bảng tại {cfg['name']}")
                    continue

                rows = table.select('tr')
                current_group = "Báo cáo"
                
                # Mapping cột: Index 0 là Tên, 1->4 là Quý
                quarter_map = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
                
                for row in rows:
                    # A. Dòng Nhóm (Parent) - VD: Báo cáo tài chính
                    parent_td = row.select_one('.parent')
                    if parent_td:
                        current_group = parent_td.get_text(strip=True)
                        continue
                    
                    # B. Dòng Con (Child) - VD: Báo cáo Riêng
                    # Class 'quatar' (sai chính tả) chứa tên dòng
                    name_td = row.select_one('.quatar')
                    if not name_td: continue
                    
                    row_name = name_td.get_text(strip=True)
                    
                    # Lấy tất cả các ô td trực tiếp của dòng này
                    cells = row.find_all('td', recursive=False)
                    
                    for idx, cell in enumerate(cells):
                        if idx == 0: continue # Cột 0 là tên, bỏ qua
                        
                        # Tìm link trong ô (class quarter)
                        a_tag = cell.find('a')
                        if not a_tag: continue
                        
                        link = a_tag.get('href')
                        if not link: continue
                        
                        # Lấy ngày (span.meta-date)
                        meta_date = cell.select_one('.meta-date')
                        date_text = meta_date.get_text(strip=True) if meta_date else ""
                        
                        # Filter năm cứng: Phải có "2025"
                        if current_year not in date_text: continue
                        
                        # Tạo tiêu đề: Báo cáo tài chính - Báo Cáo Riêng - Q2 2025
                        q_name = quarter_map.get(idx, "")
                        full_title = f"{current_group} - {row_name} {q_name} {current_year}"
                        
                        # Check trùng
                        if link in seen_ids: continue
                        if any(x['id'] == link for x in new_items): continue
                        
                        new_items.append({
                            "source": f"GEE - {cfg['name']}",
                            "id": link,
                            "title": full_title,
                            "date": date_text,
                            "link": link
                        })

            time.sleep(0.5)

        except Exception as e:
            print(f"[GEE] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_vre_news(seen_ids):
    """
    Hàm cào Vincom Retail (VRE).
    - Parser LIST: Xử lý ĐHĐCĐ & CBTT (h6 > a, time).
    - Parser TABLE: Xử lý BCTC (table > tr > td).
    """
    
    current_year = str(datetime.now().year)
    
    configs = [
        {
            "name": "Báo cáo tài chính",
            "url": "https://ir.vincom.com.vn/bao-cao-tai-chinh-va-tom-tat-ket-qua-kinh-doanh/",
            "type": "TABLE"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://ir.vincom.com.vn/cong-bo-thong-tin/dai-hoi-dong-co-dong/",
            "type": "LIST"
        },
        {
            "name": "Công bố thông tin",
            "url": "https://ir.vincom.com.vn/cong-bo-thong-tin/cong-bo-thong-tin-vi/",
            "type": "LIST"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét VRE (Năm {current_year}) ---")

    for cfg in configs:
        try:
            # print(f"   >> Đang tải: {cfg['name']}...")
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[VRE] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # ==========================================================
            # PARSER 1: DẠNG LIST (ĐHĐCĐ, CBTT)
            # Cấu trúc: .column > .item > h6 > a
            # ==========================================================
            if cfg['type'] == "LIST":
                # Tìm tất cả khối tin (.item)
                items = soup.select('.item')
                
                for item in items:
                    # 1. Tiêu đề & Link (h6 > a)
                    h6_tag = item.select_one('h6 a')
                    if not h6_tag: continue
                    
                    title = h6_tag.get_text(strip=True)
                    link = h6_tag.get('href')
                    if not link: continue

                    # 2. Ngày tháng (time tag)
                    # HTML: <time ...>26/8/2025</time>
                    date_tag = item.select_one('time')
                    date_str = ""
                    if date_tag:
                        date_str = date_tag.get_text(strip=True)
                    
                    # Nếu không có thẻ time, tìm div chứa ngày (fallback)
                    if not date_str:
                        meta_div = item.select_one('.post-meta')
                        if meta_div: date_str = meta_div.get_text(strip=True)

                    # Lọc năm (VRE dùng định dạng dd/mm/yyyy)
                    if current_year not in date_str: continue

                    # 3. Chuẩn hóa & Lưu
                    if not link.startswith('http'):
                        link = f"https://ir.vincom.com.vn{link}"
                    
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue
                    
                    new_items.append({
                        "source": f"VRE - {cfg['name']}",
                        "id": link,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })

            # ==========================================================
            # PARSER 2: DẠNG TABLE (Báo cáo tài chính)
            # Cấu trúc: table > tr > td (Link và Date nằm chung trong td)
            # ==========================================================
            elif cfg['type'] == "TABLE":
                # Tìm bảng
                # Có thể tìm table chung vì trang này chỉ có 1 bảng chính
                table = soup.select_one('table')
                if not table: continue

                rows = table.select('tr')
                current_group = "Báo cáo"
                
                # Mapping cột: Index 0 là Tên báo cáo, 1->4 là Q1->Q4
                quarter_map = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
                
                for row in rows:
                    # A. Xác định dòng Tiêu đề nhóm (VD: BÁO CÁO TÀI CHÍNH)
                    # Dựa vào style background-color hoặc thẻ b/strong trong cột đầu
                    first_td = row.select_one('td')
                    if first_td:
                        style = first_td.get('style', '').lower()
                        # Màu đỏ đặc trưng của Vincom (#d33039)
                        if 'background-color' in style or 'bold' in style:
                            text = first_td.get_text(strip=True)
                            if len(text) > 3: # Tránh lấy nhầm dòng rác
                                current_group = text
                                continue # Bỏ qua dòng tiêu đề này
                    
                    # B. Xác định dòng Dữ liệu
                    # Cột 1 là tên loại báo cáo (VD: Báo Cáo Hợp Nhất...)
                    cells = row.find_all('td', recursive=False)
                    if not cells: continue
                    
                    row_name = cells[0].get_text(strip=True)
                    if not row_name: continue

                    # Duyệt các cột Quý (từ index 1 trở đi)
                    for idx, cell in enumerate(cells):
                        if idx == 0: continue
                        
                        # Tìm link trong ô
                        a_tag = cell.find('a')
                        if not a_tag: continue
                        
                        link = a_tag.get('href')
                        if not link: continue
                        
                        # Tìm ngày: thường nằm trong thẻ div hoặc ngay sau thẻ p chứa link
                        # HTML: <div>28/08/2025</div>
                        # Lấy tất cả text trong ô, trừ text của link
                        cell_text = cell.get_text(" ", strip=True)
                        link_text = a_tag.get_text(strip=True)
                        date_text = cell_text.replace(link_text, "").strip() # Loại bỏ chữ "PDF"
                        
                        # Lọc năm 2025
                        if current_year not in date_text: continue
                        
                        # Tạo tiêu đề
                        q_name = quarter_map.get(idx, "")
                        full_title = f"{current_group} - {row_name} {q_name} {current_year}"
                        
                        # Chuẩn hóa link
                        if not link.startswith('http'):
                            link = f"https://ir.vincom.com.vn{link}"

                        # Check trùng
                        if link in seen_ids: continue
                        if any(x['id'] == link for x in new_items): continue
                        
                        new_items.append({
                            "source": f"VRE - {cfg['name']}",
                            "id": link,
                            "title": full_title,
                            "date": date_text, # Lấy chuỗi ngày tìm được
                            "link": link
                        })

            time.sleep(0.5)

        except Exception as e:
            print(f"[VRE] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_shb_news(seen_ids):
    """
    Hàm cào SHB (Ngân hàng Sài Gòn - Hà Nội).
    - Cấu trúc: div.item_ndt -> div.title -> a -> span.time
    - Xử lý ngày tháng dạng (dd-mm-yyyy) nằm trong ngoặc đơn.
    """
    
    current_year = str(datetime.now().year)
    
    # Cấu hình danh mục và URL template cho phân trang
    configs = [
        {
            "name": "Công bố thông tin",
            "base_url": "https://www.shb.com.vn/category/nha-dau-tu/cong-bo-thong-tin/"
        },
        {
            "name": "Báo cáo tài chính",
            "base_url": "https://www.shb.com.vn/category/nha-dau-tu/bao-cao-tai-chinh/"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét SHB (Năm {current_year}) ---")

    for cfg in configs:
        # Quét 2 trang đầu (WordPress thường phân trang kiểu /page/2/)
        for page in range(1, 2):
            if page == 1:
                url = cfg['base_url']
            else:
                url = f"{cfg['base_url']}page/{page}/"
                
            try:
                # print(f"   >> Đang tải: {cfg['name']} - Trang {page}...")
                response = session.get(url, headers=headers, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[SHB] Lỗi kết nối {cfg['name']}: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm các khối tin (item_ndt)
                items = soup.select('div.item_ndt')
                
                if not items:
                    break # Hết tin -> Dừng
                
                count_in_page = 0
                for item in items:
                    # 1. Tìm khối Title
                    title_div = item.select_one('.title')
                    if not title_div: continue
                    
                    a_tag = title_div.find('a')
                    if not a_tag: continue
                    
                    link = a_tag.get('href')
                    if not link: continue
                    
                    # 2. Xử lý Ngày tháng (span.time)
                    # Format: (22-10-2025)
                    time_span = a_tag.select_one('span.time')
                    date_str = ""
                    
                    if time_span:
                        raw_time = time_span.get_text(strip=True)
                        # Loại bỏ ngoặc đơn ()
                        clean_time = raw_time.replace('(', '').replace(')', '').strip()
                        
                        try:
                            # Parse ngày
                            dt_obj = datetime.strptime(clean_time, "%d-%m-%Y")
                            if str(dt_obj.year) != current_year:
                                continue # Bỏ qua tin cũ
                            date_str = clean_time.replace("-", "/")
                        except:
                            pass
                            
                    # Nếu không parse được ngày hoặc không có thẻ time -> Kiểm tra title/link fallback
                    if not date_str:
                        if current_year not in a_tag.get_text():
                            continue
                        date_str = current_year

                    # 3. Lấy Tiêu đề sạch (loại bỏ phần ngày tháng trong thẻ a)
                    # Vì SHB nhét span.time vào trong thẻ a, nên get_text() sẽ lấy cả ngày
                    # Ta cần remove text của time_span đi
                    full_text = a_tag.get_text(strip=True)
                    if time_span:
                        time_text = time_span.get_text(strip=True)
                        title = full_text.replace(time_text, "").strip()
                    else:
                        title = full_text

                    # 4. Check trùng
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue
                    
                    new_items.append({
                        "source": f"SHB - {cfg['name']}",
                        "id": link,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_page += 1
                
                # Nếu trang này không có tin mới nào -> Dừng loop
                if count_in_page == 0:
                    break
                
                time.sleep(0.5)

            except Exception as e:
                print(f"[SHB] Lỗi ngoại lệ tại {cfg['name']}: {e}")
                continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_bsr_news(seen_ids):
    """
    Hàm cào BSR (Lọc hóa dầu Bình Sơn).
    - Chỉ quét trang 1.
    - Lọc nhanh bằng thuộc tính 'data-year' của thẻ tr.
    - Lấy link tải trực tiếp từ thẻ a có title="Tải về".
    """
    
    current_year = str(datetime.now().year)
    domain = "https://bsr.com.vn"
    
    configs = [
        {
            "name": "Đại hội cổ đông",
            "url": "https://bsr.com.vn/dai-hoi-co-dong"
        },
        {
            "name": "Báo cáo tài chính",
            "url": "https://bsr.com.vn/bao-cao"
        },
        {
            "name": "Công bố thông tin khác",
            "url": "https://bsr.com.vn/cong-bo-thong-tin-khac"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét BSR (Năm {current_year}) ---")

    for cfg in configs:
        try:
            # Chỉ request trang đầu (Page 1)
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[BSR] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm tất cả các dòng dữ liệu (tr.document-item)
            rows = soup.select('tr.document-item')
            
            if not rows:
                continue

            for row in rows:
                # 1. LỌC NĂM CỰC NHANH
                # Web BSR có thuộc tính data-year="2025" ngay trên thẻ tr
                data_year = row.get('data-year')
                if data_year and data_year != current_year:
                    continue # Bỏ qua ngay nếu không phải năm nay
                
                # Nếu không có data-year (phòng hờ), check cột ngày
                cols = row.find_all('td')
                if len(cols) < 3: continue
                
                # Cột 1: Ngày (Index 1) - VD: 30/10/2025 13:02
                date_text = cols[1].get_text(strip=True)
                if current_year not in date_text:
                    continue
                
                # Format lại ngày: lấy phần đầu dd/mm/yyyy
                date_str = date_text.split(" ")[0] if " " in date_text else date_text

                # 2. LẤY TIÊU ĐỀ
                # Nằm trong thẻ p.document-title ở cột 0
                title_tag = row.select_one('.document-title')
                title = title_tag.get_text(strip=True) if title_tag else "Tài liệu BSR"

                # 3. LẤY LINK TẢI
                # Trong cột cuối cùng, tìm thẻ a có title="Tải về" hoặc chứa "get_file"
                # Ưu tiên tìm thẻ có thuộc tính download hoặc title="Tải về"
                download_a = row.select_one('a[title="Tải về"]')
                
                # Nếu không thấy, tìm thẻ a bất kỳ chứa link get_file
                if not download_a:
                    download_a = row.select_one('a[href*="get_file"]')
                
                if not download_a: continue
                
                link = download_a.get('href')
                if not link or "javascript" in link: continue

                # Chuẩn hóa link (thường BSR dùng link tương đối /c/document_library...)
                if not link.startswith('http'):
                    link = f"{domain}{link}"

                # 4. CHECK TRÙNG & LƯU
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue
                
                new_items.append({
                    "source": f"BSR - {cfg['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[BSR] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_bcm_news(seen_ids):
    """
    Hàm cào Becamex (BCM).
    - Cấu trúc chung cho cả 4 mục: div.shareholder-item
    - Xử lý ngày tiếng Việt: "02 Tháng 12, 2025"
    """
    
    current_year = str(datetime.now().year)
    
    configs = [
        {
            "name": "Công bố thông tin",
            "url": "https://becamex.com.vn/quan-he-co-dong/cong-bo-thong-tin/"
        },
        {
            "name": "Báo cáo tài chính",
            "url": "https://becamex.com.vn/quan-he-co-dong/bao-cao-tai-chinh/"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://becamex.com.vn/quan-he-co-dong/dai-hoi-dong-co-dong/"
        },
        {
            "name": "Thông tin cổ đông",
            "url": "https://becamex.com.vn/quan-he-co-dong/thong-tin-co-dong/"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét BCM (Năm {current_year}) ---")

    for cfg in configs:
        try:
            # Chỉ quét trang đầu
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[BCM] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm các khối tin (shareholder-item)
            items = soup.select('div.shareholder-item')
            
            if not items:
                continue

            for item in items:
                # 1. XỬ LÝ NGÀY THÁNG
                # Tìm thẻ p chứa ngày (thường là thẻ p đầu tiên trong item)
                p_tags = item.find_all('p')
                date_str = ""
                
                for p in p_tags:
                    text = p.get_text(strip=True)
                    # Format: "02 Tháng 12, 2025"
                    if "Tháng" in text and "," in text:
                        # Chuẩn hóa chuỗi ngày
                        clean_date = text.replace("Tháng", "").replace(",", "").strip() # -> "02  12  2025"
                        
                        # Xử lý khoảng trắng thừa
                        parts = clean_date.split()
                        if len(parts) == 3:
                            day, month, year = parts
                            if year != current_year:
                                break # Không phải năm nay -> Dừng check item này
                            date_str = f"{day}/{month}/{year}"
                            break # Đã tìm thấy ngày hợp lệ
                
                # Nếu không tìm thấy ngày năm nay -> Bỏ qua
                if not date_str:
                    continue

                # 2. LẤY LINK VÀ TITLE
                # Tìm thẻ h2 > a
                h2_tag = item.select_one('h2 a')
                if not h2_tag: continue
                
                link = h2_tag.get('href')
                title = h2_tag.get_text(strip=True)
                
                if not link: continue
                
                # 3. CHECK TRÙNG & LƯU
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue
                
                new_items.append({
                    "source": f"BCM - {cfg['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[BCM] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_sab_news(seen_ids):
    """
    Hàm cào SABECO (SAB) - Fix lỗi thiếu BCTC các quý cũ.
    - Duyệt qua TẤT CẢ các khối .financy-report (thay vì chỉ khối đầu tiên).
    """
    
    current_year = str(datetime.now().year)
    domain = "https://www.sabeco.com.vn"
    
    configs = [
        {
            "name": "Công bố thông tin",
            "url": f"https://www.sabeco.com.vn/co-dong/cong-bo-thong-tin/{current_year}"
        },
        {
            "name": "Báo cáo tài chính",
            "url": f"https://www.sabeco.com.vn/co-dong/bao-cao-tai-chinh/{current_year}-2"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": f"https://www.sabeco.com.vn/co-dong/dai-hoi-dong-co-dong/{current_year}-4"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét SABECO (Năm {current_year}) ---")

    for cfg in configs:
        try:
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[SAB] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- FIX: Lấy TẤT CẢ các khối báo cáo ---
            # Mỗi khối tương ứng với 1 Quý hoặc 1 Kỳ (Bán niên, Năm)
            report_blocks = soup.select('.financy-report')
            
            if not report_blocks:
                # print(f"[SAB] Không tìm thấy dữ liệu tại {cfg['name']}")
                continue
            
            for block in report_blocks:
                # Lấy danh sách tin trong từng khối
                list_items = block.select('li')
                
                for li in list_items:
                    # 1. Tìm Link & Title
                    a_tag = li.find('a')
                    if not a_tag: continue
                    
                    link = a_tag.get('href')
                    if not link: continue
                    
                    title = a_tag.get_text(strip=True)
                    
                    # 2. Xử lý Ngày tháng (Text nằm ngoài thẻ a)
                    # Nội dung li: <a...>Tiêu đề</a> (25/07/2025)
                    full_text = li.get_text(strip=True)
                    date_str = ""
                    
                    # Regex bắt chuỗi ngày trong ngoặc
                    match = re.search(r'\((\d{1,2}/\d{1,2}/\d{4})\)', full_text)
                    if match:
                        date_str = match.group(1)
                    else:
                        # Fallback: Tìm ngày dạng dd/mm/yyyy bất kỳ trong text
                        match_any = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', full_text)
                        if match_any:
                            date_str = match_any.group(1)
                    
                    # Filter năm
                    if current_year not in date_str: continue

                    # 3. Chuẩn hóa & Lưu
                    if not link.startswith('http'):
                        link = f"{domain}{link}"
                    
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue
                    
                    new_items.append({
                        "source": f"SAB - {cfg['name']}",
                        "id": link,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })

            time.sleep(0.5)

        except Exception as e:
            print(f"[SAB] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_ssi_news(seen_ids):
    """
    Hàm cào SSI (Chứng khoán SSI).
    - Phần 1: Báo cáo tài chính (Dựa trên div class chart__content__item).
    - Phần 2: Lịch sử cổ tức (Dựa trên Table).
    """
    
    current_year = datetime.now().year
    # current_year = 2024 # Uncomment dòng này nếu muốn test với dữ liệu năm cũ
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét SSI (Năm {current_year}) ---")

    # ==========================================================
    # PHẦN 1: BÁO CÁO TÀI CHÍNH
    # ==========================================================
    bctc_url = "https://www.ssi.com.vn/quan-he-nha-dau-tu/bao-cao-tai-chinh"
    
    # SSI có param lọc năm, ta tận dụng luôn
    params = {
        "year": current_year 
    }

    try:
        # print(f"   >> Quét BCTC...")
        response = session.get(bctc_url, headers=headers, params=params, timeout=20, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Tìm các item theo class trong ảnh source code
        items = soup.select('.chart__content__item')
        
        for item in items:
            # 1. Lấy Tiêu đề
            title_tag = item.select_one('.chart__content__item__desc p')
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            
            # 2. Lấy Link
            link_tag = item.select_one('.chart__content__item__time a')
            if not link_tag: continue
            link = link_tag.get('href')
            
            if not link: continue
            
            # Chuẩn hóa link (SSI thường để link tương đối /upload/...)
            if not link.startswith('http'):
                link = f"https://www.ssi.com.vn{link}"

            # 3. Kiểm tra năm trong tiêu đề (Double check)
            if str(current_year) not in title:
                continue

            # 4. Check trùng
            if link in seen_ids: continue
            if any(x['id'] == link for x in new_items): continue

            new_items.append({
                "source": "SSI - BCTC",
                "id": link,
                "title": title,
                "date": str(current_year),
                "link": link
            })

    except Exception as e:
        print(f"[SSI] Lỗi BCTC: {e}")


    # ==========================================================
    # PHẦN 2: LỊCH SỬ CỔ TỨC (Dạng Bảng)
    # ==========================================================
    div_url = "https://www.ssi.com.vn/quan-he-nha-dau-tu/lich-su-co-tuc"
    
    try:
        # print(f"   >> Quét Lịch sử cổ tức...")
        response = session.get(div_url, headers=headers, timeout=20, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm bảng
        table = soup.select_one('table.table')
        if table:
            rows = table.find_all('tr')
            
            # Bỏ qua dòng tiêu đề đầu tiên
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) < 7: continue # Đảm bảo đủ cột
                
                # Cấu trúc cột theo ảnh:
                # [0] Năm | [1] TG | [2] Tỷ lệ | [3] GDKHQ | [4] ĐKCC | [5] Thanh toán | [6] Hình thức
                
                ex_date_raw = cols[3].get_text(strip=True) # Ngày giao dịch không hưởng quyền
                content_type = cols[6].get_text(strip=True) # Tiền mặt / Cổ phiếu
                rate = cols[2].get_text(strip=True) # Tỷ lệ
                
                # Parse ngày GDKHQ (dd/mm/yyyy)
                try:
                    ex_date = datetime.strptime(ex_date_raw, "%d/%m/%Y")
                    
                    # LOGIC QUAN TRỌNG: Chỉ lấy nếu GDKHQ nằm trong năm hiện tại
                    if ex_date.year != current_year:
                        continue
                        
                    date_str = ex_date.strftime("%d/%m/%Y")
                    
                    title = f"Thông báo trả cổ tức {content_type} - Tỷ lệ {rate} (GDKHQ: {date_str})"
                    
                    # Tạo ID giả
                    fake_id = f"SSI_DIV_{ex_date_raw}_{content_type}"
                    link = div_url # Trỏ về trang bảng
                    
                    if fake_id in seen_ids: continue
                    if any(x['id'] == fake_id for x in new_items): continue

                    new_items.append({
                        "source": "SSI - Cổ Tức",
                        "id": fake_id,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    
                except ValueError:
                    continue 

    except Exception as e:
        print(f"[SSI] Lỗi Cổ tức: {e}")

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_vib_news(seen_ids):
    current_year = datetime.now().year
    domain = "https://www.vib.com.vn"
    
    # --- CẤU HÌNH HEADERS & COOKIES (Giữ nguyên từ cURL cũ) ---
    headers = {
        "accept": "text/html, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "priority": "u=1, i",
        "referer": "https://www.vib.com.vn/vn/nha-dau-tu",
        "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "x-requested-with": "XMLHttpRequest"
    }
    
    cookies = {
        "route": "c26a0b557457a2502d35448a2f46e3eb",
        "JSESSIONID": "0000B4eA_vZ-FKVb6ZnnQtx4c51:1evrkq9vn" 
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())
    
    # Danh sách tên miền rác cần loại bỏ (Footer links)
    JUNK_DOMAINS = ['facebook.com', 'youtube.com', 'linkedin.com', 'google.com', 'apple.com', 'goo.gl']

    print(f"--- 🚀 Bắt đầu quét VIB (Smart Filter - Năm {current_year}) ---")

    # ==========================================================
    # PHẦN 1: BÁO CÁO TÀI CHÍNH (QUÝ 1 -> 4)
    # ==========================================================
    bctc_cmpnt_id = "242afeb3-0b0e-4413-a11a-86ab453adc26"
    base_bctc = f"https://www.vib.com.vn/wps/wcm/connect/vib-vevib-vn/sa-homepage/shareholder/thong-tin-tai-chinh/{current_year}/bao-cao-quy-{{}}"
    
    for q in range(1, 5):
        current_time = int(time.time())
        url = f"{base_bctc.format(q)}?source=library&srv=cmpnt&cmpntid={bctc_cmpnt_id}&time={current_time}"
        
        try:
            response = session.get(url, headers=headers, cookies=cookies, timeout=20, verify=False)
            
            if response.status_code != 200 or len(response.text) < 100:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- CHIẾN THUẬT LỌC MỚI ---
            # 1. Tìm chính xác thẻ a có class "file-link" (như ảnh image_adc15e.png)
            links = soup.select('a.file-link')
            
            # 2. Nếu không thấy, fallback tìm thẻ a nằm trong h4 (như ảnh image_adbe79.png)
            if not links:
                links = [h4.find('a') for h4 in soup.select('h4') if h4.find('a')]
            
            # 3. Nếu vẫn không thấy, tìm thẻ a có path chứa "/vib-vevib-vn/" (Link nội bộ)
            if not links:
                links = soup.select('a[path^="/vib-vevib-vn/"]')

            found_in_quarter = 0
            for a_tag in links:
                # Lấy Link
                path = a_tag.get('href') or a_tag.get('path')
                if not path: continue
                
                # --- LỌC RÁC QUAN TRỌNG ---
                # Nếu link chứa domain rác -> Bỏ qua ngay
                if any(junk in path.lower() for junk in JUNK_DOMAINS):
                    continue
                
                # Link phải có độ dài nhất định và không phải javascript
                if len(path) < 5 or "javascript" in path: continue

                if not path.startswith('http'):
                    full_link = f"{domain}{path}"
                else:
                    full_link = path
                
                title = a_tag.get_text(strip=True)
                
                # Lấy Ngày (logic cũ vẫn tốt)
                date_str = str(current_year)
                date_tag = a_tag.find_next_sibling('i')
                if not date_tag and a_tag.parent: date_tag = a_tag.parent.find('i')
                    
                if date_tag:
                    raw_date = date_tag.get('date-created') or date_tag.get_text(strip=True)
                    if raw_date:
                        try:
                            clean_date = raw_date[:10].replace('-', '/')
                            d_obj = datetime.strptime(clean_date, "%Y/%m/%d")
                            if d_obj.year != current_year: continue
                            date_str = d_obj.strftime("%d/%m/%Y")
                        except: pass

                # Check trùng
                if full_link in seen_ids: continue
                if any(x['id'] == full_link for x in new_items): continue

                new_items.append({
                    "source": f"VIB - BCTC Q{q}",
                    "id": full_link,
                    "title": title,
                    "date": date_str,
                    "link": full_link
                })
                found_in_quarter += 1
                
            # print(f"   > Quý {q}: Tìm thấy {found_in_quarter} file hợp lệ.")

        except Exception as e:
            continue

    # ==========================================================
    # PHẦN 2: TIN KHÁC (ĐHĐCĐ & CỔ TỨC)
    # ==========================================================
    other_targets = [
        {
            "name": "ĐHĐCĐ",
            "url_base": "https://www.vib.com.vn/wps/wcm/connect/vib-vevib-vn/sa-homepage/shareholder/tin-co-dong/thong-tin-dai-hoi-co-dong",
            "cmpntid": "712752d0-d846-46dd-a6ce-c2a63d09ff86"
        },
        {
            "name": "Cổ tức",
            "url_base": "https://www.vib.com.vn/wps/wcm/connect/vib-vevib-vn/sa-homepage/shareholder/tin-co-dong/lich-su-tra-co-tuc-bang-tien",
            "cmpntid": "712752d0-d846-46dd-a6ce-c2a63d09ff86"
        }
    ]

    for target in other_targets:
        current_time = int(time.time())
        url = f"{target['url_base']}?source=library&srv=cmpnt&cmpntid={target['cmpntid']}&time={current_time}"
        
        try:
            response = session.get(url, headers=headers, cookies=cookies, timeout=20, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Logic tương tự: Tìm a có path hoặc trong h4
            links = soup.find_all('a', attrs={'path': True})
            if not links: links = [h4.find('a') for h4 in soup.select('h4') if h4.find('a')]

            for a_tag in links:
                if not a_tag: continue
                path = a_tag.get('path') or a_tag.get('href')
                
                # LỌC RÁC
                if not path or any(junk in path.lower() for junk in JUNK_DOMAINS): continue
                
                if not path.startswith('http'):
                    full_link = f"{domain}{path}"
                else:
                    full_link = path
                    
                title = a_tag.get_text(strip=True)
                
                # Ngày tháng
                date_str = str(current_year)
                date_tag = a_tag.find_next_sibling('i')
                if not date_tag and a_tag.parent: date_tag = a_tag.parent.find('i')
                
                if date_tag:
                    raw_date = date_tag.get('date-created') or date_tag.get_text(strip=True)
                    if raw_date:
                        try:
                            clean_date = raw_date[:10].replace('-', '/')
                            d_obj = datetime.strptime(clean_date, "%Y/%m/%d")
                            if d_obj.year != current_year: continue
                            date_str = d_obj.strftime("%d/%m/%Y")
                        except: pass
                
                if full_link in seen_ids: continue
                if any(x['id'] == full_link for x in new_items): continue

                new_items.append({
                    "source": f"VIB - {target['name']}",
                    "id": full_link,
                    "title": title,
                    "date": date_str,
                    "link": full_link
                })

        except Exception as e:
            # print(f"Lỗi VIB {target['name']}: {e}")
            pass

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_ssb_news(seen_ids):
    """
    Hàm cào SeABank (SSB).
    - Website dùng Tailwind CSS.
    - Cấu trúc: section.md:block -> a -> div -> h2 (Title).
    - Ngày tháng: Tìm text dạng dd/mm/yyyy gần icon lịch.
    """
    
    current_year = str(datetime.now().year)
    domain = "https://www.seabank.com.vn"
    
    configs = [
        {
            "name": "Công bố thông tin",
            "url": "https://www.seabank.com.vn/nha-dau-tu/cong-bo-thong-tin"
        },
        {
            "name": "Báo cáo tài chính",
            "url": "https://www.seabank.com.vn/nha-dau-tu/bao-cao-tai-chinh"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://www.seabank.com.vn/nha-dau-tu/dai-hoi-dong-co-dong"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét SSB (Năm {current_year}) ---")

    for cfg in configs:
        try:
            # print(f"   >> Đang tải: {cfg['name']}...")
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[SSB] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Tìm các khối tin dành cho Desktop (để tránh trùng lặp với mobile)
            # Class Tailwind: "hidden md:block" -> dùng select css selector
            # Lưu ý dấu : trong css selector phải escape hoặc dùng attribute selector
            sections = soup.select('section[class*="md:block"]')
            
            if not sections:
                # Fallback: Tìm thẻ a có href chứa /nha-dau-tu/
                sections = soup.select(f'a[href^="/nha-dau-tu/"]')

            for item in sections:
                # Nếu item là section -> tìm a con, nếu là a -> dùng luôn
                if item.name == 'a':
                    a_tag = item
                else:
                    a_tag = item.find('a')
                
                if not a_tag: continue
                
                link = a_tag.get('href')
                if not link: continue
                
                # 2. Lấy Title (h2)
                title_tag = a_tag.find('h2')
                if not title_tag: continue
                title = title_tag.get_text(strip=True)
                
                # 3. Lấy Ngày tháng
                # Cách 1: Tìm text có format ngày tháng trong toàn bộ khối
                full_text = a_tag.get_text(" ", strip=True)
                date_str = ""
                
                # Regex tìm dd/mm/yyyy
                match = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
                if match:
                    date_str = match.group(1)
                
                # Lọc năm
                if current_year not in date_str: continue

                # 4. Chuẩn hóa & Lưu
                if not link.startswith('http'):
                    link = f"{domain}{link}"
                
                # Check trùng
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue
                
                new_items.append({
                    "source": f"SSB - {cfg['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[SSB] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

def fetch_tpb_news(seen_ids):
    """
    Hàm cào TPBank (TPB) - Selenium Mode.
    - Cấu trúc: Web động, dùng Selenium để load hết các block.
    - Parsing: Dựa vào class 'group-content', 'b-right-download'.
    - Ngày tháng: Trích xuất trực tiếp từ chuỗi Title (Regex).
    """
    
    current_year = datetime.now().year
    # current_year = 2025 # Hardcode để test
    
    # 1. Cấu hình danh sách Link cần quét
    targets = [
        {
            "name": "Báo cáo tài chính",
            "url": "https://tpb.vn/nha-dau-tu/bao-cao-tai-chinh"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://tpb.vn/nha-dau-tu/dai-hoi-dong-co-dong"
        },
        {
            "name": "Thông báo cổ đông",
            "url": "https://tpb.vn/nha-dau-tu/thong-bao-co-dong"
        }
    ]

    # 2. Cấu hình Selenium (Headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    new_items = []
    
    print(f"--- 🚀 Bắt đầu quét TPB (Năm {current_year}) ---")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30) # TPB load hơi lâu

    try:
        for target in targets:
            try:
                # print(f"   >> Đang tải: {target['name']}...")
                driver.get(target['url'])
                
                # Chờ 5s để JS chạy và render các block năm 2025
                time.sleep(5)
                
                # --- LOGIC MỞ RỘNG ACCORDION (QUAN TRỌNG) ---
                # TPB thường đóng các mục, ta cần click mở năm hiện tại nếu nó chưa mở.
                # Tuy nhiên, thường năm mới nhất sẽ tự mở. 
                # Để chắc ăn, ta lấy toàn bộ source sau 5s chờ đợi.
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Tìm tất cả các khối nội dung tin
                # Dựa vào ảnh: div.group-content
                content_groups = soup.select('.group-content')
                
                count_in_cat = 0
                for group in content_groups:
                    # Tìm phần bên phải chứa link download
                    # Dựa vào ảnh: div.b_right -> div.b-right-download -> a
                    # Có thể có nhiều file trong 1 group (VD: file tiếng Việt, tiếng Anh)
                    
                    download_divs = group.select('.b-right-download')
                    
                    for div in download_divs:
                        a_tag = div.find('a')
                        if not a_tag: continue
                        
                        link = a_tag.get('href')
                        if not link or "javascript" in link or link == "#": continue
                        
                        # Lấy text gốc để tách ngày và tiêu đề
                        # Text thường nằm trong span hoặc trực tiếp trong a
                        # Ví dụ: " 18/08/2025 Báo cáo tài chính..."
                        full_text = a_tag.get_text(" ", strip=True)
                        
                        # --- XỬ LÝ NGÀY THÁNG BẰNG REGEX ---
                        # Tìm chuỗi dd/mm/yyyy ở đầu hoặc trong text
                        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
                        
                        date_str = str(current_year)
                        valid_date = False
                        
                        if date_match:
                            extracted_date = date_match.group(1)
                            try:
                                d_obj = datetime.strptime(extracted_date, "%d/%m/%Y")
                                if d_obj.year == current_year:
                                    date_str = extracted_date
                                    valid_date = True
                            except: pass
                        else:
                            # Nếu không thấy ngày trong text, check thử các class 'year-value' ở block bên trái (.b_left)
                            # Nhưng bạn khuyên không nên tin tưởng, nên ta ưu tiên Regex title.
                            # Nếu không có ngày trong title -> Bỏ qua hoặc lấy nếu nghi ngờ là năm nay?
                            # An toàn nhất: Nếu ko có ngày -> Bỏ qua (để tránh lấy tin cũ từ các năm trước lọt vào)
                            pass

                        if not valid_date: continue

                        # Xử lý Tiêu đề: Xóa ngày tháng khỏi tiêu đề cho đẹp
                        title = full_text.replace(date_str, "").strip()
                        # Xóa các ký tự thừa như dấu chấm, gạch ngang ở đầu
                        title = re.sub(r'^[\.\-\:\s]+', '', title)
                        
                        if not title: title = "Tài liệu TPBank"

                        # Chuẩn hóa Link
                        if not link.startswith('http'):
                            link = f"https://tpb.vn{link}"
                            
                        # Check trùng
                        if link in seen_ids: continue
                        if any(x['id'] == link for x in new_items): continue

                        new_items.append({
                            "source": f"TPB - {target['name']}",
                            "id": link,
                            "title": title,
                            "date": date_str,
                            "link": link
                        })
                        count_in_cat += 1

                # print(f"      -> Tìm thấy {count_in_cat} tin.")

            except Exception as e:
                print(f"[TPB] Lỗi tại {target['name']}: {e}")
                continue

    except Exception as e:
        print(f"[TPB] Lỗi Driver: {e}")
    finally:
        driver.quit()
        
    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_vea_news(seen_ids):
    """
    Hàm cào VEAM (VEA).
    - Fix lỗi lấy nhầm thẻ Title của ảnh (rỗng).
    - Selector chuẩn: .text-box-news > a.title-new
    """
    
    current_year = str(datetime.now().year)
    domain = "http://veamcorp.com"
    
    configs = [
        {
            "name": "Báo cáo tài chính",
            "url": "http://veamcorp.com/tin-tuc/bao-cao-tai-chinh-113.html"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "http://veamcorp.com/tin-tuc/dai-hoi-dong-co-dong-118.html"
        },
        {
            "name": "Công bố thông tin",
            "url": "http://veamcorp.com/tin-tuc/cong-bo-thong-tin-114.html"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('http://', LegacySSLAdapter())
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét VEAM (Năm {current_year}) ---")

    for cfg in configs:
        try:
            response = session.get(cfg['url'], headers=headers, timeout=20)
            response.encoding = 'utf-8' # Ép mã hóa
            
            if response.status_code != 200:
                print(f"[VEA] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm các khối tin
            items = soup.select('.box-catnew')
            
            for item in items:
                # --- FIX QUAN TRỌNG TẠI ĐÂY ---
                # Chỉ tìm thẻ a.title-new nằm trong khối .text-box-news
                # (Tránh lấy nhầm thẻ a.title-new bao quanh ảnh ở bên trái)
                title_tag = item.select_one('.text-box-news a.title-new')
                
                if not title_tag: continue
                
                title = title_tag.get_text(" ", strip=True)
                link = title_tag.get('href')
                
                if not link: continue
                
                # Fallback: Nếu vẫn rỗng, thử lấy từ thuộc tính title (nếu có)
                if not title: title = title_tag.get('title', 'Tài liệu VEAM')

                # 2. LẤY NGÀY
                date_div = item.select_one('.text-date-new')
                date_str = ""
                
                if date_div:
                    raw_text = date_div.get_text(strip=True) # "Ngày đăng: 25/11/2025"
                    clean_text = raw_text.replace("Ngày đăng:", "").strip()
                    
                    if current_year in clean_text:
                        date_str = clean_text
                
                if not date_str: continue

                # 3. CHUẨN HÓA LINK
                if not link.startswith('http'):
                    link = f"http://veamcorp.com{link}"
                
                # 4. CHECK TRÙNG
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue
                
                new_items.append({
                    "source": f"VEA - {cfg['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[VEA] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_fox_news(seen_ids):
    """
    Hàm cào FPT Telecom (FOX) - Phiên bản Lọc Tiếng Anh.
    - Sử dụng tham số ?tag={year} để lọc server-side.
    - Loại bỏ các tin có tiêu đề chứa "Tiếng Anh" hoặc "English".
    """
    
    current_year = str(datetime.now().year)
    
    configs = [
        {
            "name": "Báo cáo tài chính",
            "url": f"https://fpt.vn/vi/ve-fpt-telecom/quan-he-co-dong/bao-cao-tai-chinh/?tag={current_year}"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": f"https://fpt.vn/vi/ve-fpt-telecom/quan-he-co-dong/dai-hoi-co-dong-fpt-telecom/?tag={current_year}"
        },
        {
            "name": "Thông báo trả cổ tức",
            "url": f"https://fpt.vn/vi/ve-fpt-telecom/quan-he-co-dong/thong-bao-tra-co-tuc/?tag={current_year}"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét FOX (Năm {current_year}) ---")

    for cfg in configs:
        try:
            response = session.get(cfg['url'], headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[FOX] Lỗi kết nối {cfg['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm tất cả các dòng dữ liệu (tr.table-row)
            rows = soup.select('tr.table-row')
            
            if not rows:
                continue

            for row in rows:
                # Lấy các cột
                cols = row.find_all('td')
                if len(cols) < 2: continue
                
                # 1. LẤY TIÊU ĐỀ (Cột 0)
                title = cols[0].get_text(strip=True)
                
                # --- LOGIC LỌC TIẾNG ANH (MỚI THÊM) ---
                title_lower = title.lower()
                if "tiếng anh" in title_lower or "english" in title_lower:
                    # Bỏ qua ngay lập tức
                    continue

                # 2. LẤY NGÀY (Cột 1)
                # Format: 24-10-2025 16:54
                date_text = cols[1].get_text(strip=True)
                date_str = date_text.split(" ")[0] if " " in date_text else date_text
                
                # Check năm
                if current_year not in date_str:
                    continue

                # 3. LẤY LINK TẢI
                link_tag = row.select_one('a.img-download')
                if not link_tag:
                    link_tag = row.select_one('a.view-pdf')
                
                if not link_tag: continue
                
                link = link_tag.get('href')
                if not link: continue

                # Chuẩn hóa Link
                if not link.startswith('http'):
                    link = f"https://fpt.vn{link}"

                # 4. CHECK TRÙNG & LƯU
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue
                
                new_items.append({
                    "source": f"FOX - {cfg['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[FOX] Lỗi ngoại lệ tại {cfg['name']}: {e}")
            continue

    return new_items

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_gex_news(seen_ids):
    """
    Hàm cào Gelex (GEX) - Fix Selector Bảng & List.
    """
    
    current_year = datetime.now().year
    # current_year = 2025 # Mở dòng này để test nếu cần
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét GEX (Fixed Selector - Năm {current_year}) ---")

    # ==========================================================
    # PHẦN 1: BÁO CÁO TÀI CHÍNH (Xử lý Bảng phức tạp)
    # ==========================================================
    url_bctc = "https://gelex.vn/doc-cat/bao-cao-tai-chinh"
    
    try:
        response = session.get(url_bctc, headers=headers, timeout=20, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # FIX: Tìm div wrapper trước, sau đó tìm table bên trong
        # -> div.report-table -> table
        wrapper = soup.select_one('.report-table')
        if wrapper:
            table = wrapper.find('table')
            if table:
                rows = table.find_all('tr')
                
                # Biến trạng thái để nhớ tiêu đề của nhóm hiện tại
                # VD: Đang duyệt nhóm "Báo cáo tài chính" -> "Báo cáo Riêng"
                current_group = "BCTC"
                current_sub = ""
                
                for row in rows:
                    # 1. Cập nhật Tiêu đề Nhóm (Class 'parent')
                    parent_td = row.find('td', class_='parent')
                    if parent_td:
                        current_group = parent_td.get_text(strip=True)
                        current_sub = "" # Reset sub khi sang nhóm mới
                    
                    # 2. Cập nhật Tiêu đề Con (Class 'quatar' - lỗi chính tả của GEX, hoặc 'child')
                    # Tìm td có class chứa 'child' hoặc 'quatar'
                    sub_td = row.find('td', class_=lambda x: x and ('child' in x or 'quatar' in x))
                    if sub_td:
                        # Chỉ lấy text nếu td này KHÔNG chứa file download (để tránh nhầm lẫn)
                        if not sub_td.find('div', class_='report-table-item'):
                            text = sub_td.get_text(strip=True)
                            if text: current_sub = text
                    
                    # 3. Tìm các ô chứa file (report-table-item)
                    file_items = row.select('.report-table-item')
                    
                    for item in file_items:
                        # Lấy Ngày: <div class="date-pdf">22/04/2025</div>
                        date_tag = item.select_one('.date-pdf')
                        if not date_tag: continue
                        
                        date_str = date_tag.get_text(strip=True)
                        try:
                            d_obj = datetime.strptime(date_str, "%d/%m/%Y")
                            if d_obj.year != current_year: continue
                        except: continue

                        # Lấy Link
                        a_tag = item.find('a')
                        if not a_tag: continue
                        link = a_tag.get('href')
                        if not link: continue
                        
                        # Tạo tiêu đề thông minh
                        # VD: Báo cáo tài chính - Báo cáo Riêng (22/04/2025)
                        full_title = f"{current_group}"
                        if current_sub:
                            full_title += f" - {current_sub}"
                        full_title += f" ({date_str})"
                        
                        if link in seen_ids: continue
                        if any(x['id'] == link for x in new_items): continue

                        new_items.append({
                            "source": "GEX - BCTC",
                            "id": link,
                            "title": full_title,
                            "date": date_str,
                            "link": link
                        })

    except Exception as e:
        print(f"[GEX] Lỗi BCTC: {e}")


    # ==========================================================
    # PHẦN 2: DANH SÁCH (CBTT & ĐHĐCĐ)
    # ==========================================================
    list_targets = [
        {"name": "CBTT", "url": "https://gelex.vn/doc-cat/cong-bo-thong-tin-2"},
        {"name": "ĐHĐCĐ", "url": "https://gelex.vn/doc-cat/tai-lieu-dai-hoi-dong-cd"}
    ]

    for target in list_targets:
        try:
            response = session.get(target['url'], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # FIX: Tìm thẻ li cha (li-report-list) cho chắc chắn
            #
            list_items = soup.select('li.li-report-list')
            
            # print(f"   > {target['name']}: Tìm thấy {len(list_items)} mục.")
            
            for li in list_items:
                # 1. Lấy Ngày (.meta)
                date_tag = li.select_one('.meta')
                if not date_tag: continue
                
                date_str = date_tag.get_text(strip=True) # VD: 19/11/2025
                try:
                    d_obj = datetime.strptime(date_str, "%d/%m/%Y")
                    if d_obj.year != current_year: continue
                except: continue

                # 2. Lấy Tiêu đề & Link (.li-report-item-title-link)
                # Ưu tiên lấy title link (chứa text tiêu đề)
                # Lưu ý: Có thể có 2 thẻ a (1 cái là icon download, 1 cái là text). Ta lấy cái text.
                # Cách phân biệt: class icon download thường là 'li-report-item-title-link-download'
                
                title_link = li.select_one('a.li-report-item-title-link')
                if not title_link: continue
                
                title = title_link.get_text(strip=True)
                link = title_link.get('href')
                
                if not link: continue
                
                # Check trùng
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue

                new_items.append({
                    "source": f"GEX - {target['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

        except Exception as e:
            print(f"[GEX] Lỗi {target['name']}: {e}")

    return new_items

def fetch_eib_news(seen_ids):
    """
    Hàm cào Eximbank (EIB).
    - Trang web sử dụng Next.js + Tailwind CSS.
    - Dữ liệu nằm trong các div có ID số (vd: id="810", id="795").
    - Có bộ lọc ngôn ngữ (Bỏ bản Tiếng Anh).
    """
    
    current_year = datetime.now().year
    # current_year = 2025 # Mở dòng này để test giả lập năm 2025
    
    # Cấu hình Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    new_items = []
    print(f"--- 🚀 Bắt đầu quét EIB (Năm {current_year}) ---")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)

    # Danh sách link cần cào
    targets = [
        {"name": "BCTC", "url": "https://eximbank.com.vn/bao-cao-tai-chinh"},
        {"name": "ĐHĐCĐ", "url": "https://eximbank.com.vn/dai-hoi-dong-co-dong"}
    ]

    try:
        for target in targets:
            # print(f"   >> Đang tải: {target['name']}...")
            driver.get(target['url'])
            
            # Cuộn trang để đảm bảo dữ liệu load hết (React hay lazy load)
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            time.sleep(3) # Chờ render cuối cùng
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # --- CHIẾN THUẬT: TÌM CÁC KHỐI TIN THEO ID SỐ ---
            # Dựa vào ảnh: <div id="810">, <div id="795">...
            # Ta tìm tất cả div có thuộc tính id, và id đó phải là số
            # Hoặc tìm div chứa class "flex flex-col" (Container chính của EIB)
            
            # Cách an toàn nhất: Tìm tất cả thẻ <a> có thuộc tính download hoặc href chứa .pdf
            all_links = soup.select('a[href$=".pdf"]')
            
            # Nếu không tìm thấy theo đuôi pdf, tìm theo thẻ a có attribute 'download'
            if not all_links:
                all_links = soup.select('a[download]')

            for a_tag in all_links:
                link = a_tag.get('href')
                if not link: continue
                
                # Lấy text tiêu đề (thường nằm trong thẻ a hoặc thẻ p con)
                raw_text = a_tag.get_text(" ", strip=True)
                
                # --- 1. LỌC TIẾNG ANH ---
                # Bỏ qua nếu tên file hoặc tiêu đề có dấu hiệu tiếng Anh
                lower_text = raw_text.lower()
                lower_link = link.lower()
                
                keywords_eng = ["financial statement", "eng.pdf", "- en", "english", "resolution", 'eng']
                if any(kw in lower_link for kw in keywords_eng) or any(kw in lower_text for kw in keywords_eng):
                    # print(f"      -> Bỏ qua bản Tiếng Anh: {raw_text[:30]}...")
                    continue

                # --- 2. TÌM NGÀY THÁNG ---
                date_str = str(current_year)
                found_date = False
                
                # Chiến thuật tìm ngày:
                # Cách A (BCTC): Ngày nằm trong tiêu đề cha (div id="810" -> p)
                # VD: "Báo cáo tài chính Quý 3 năm 2025 (30/10/2025)"
                # Ta phải leo ngược lên tìm container cha
                
                # Cách B (ĐHĐCĐ): Ngày nằm trong thẻ <p> anh em với tiêu đề bên trong thẻ <a>
                # VD: <p>29/04/2025</p>
                
                # Thử tìm ngày trong chính text của thẻ a trước
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_text)
                if date_match:
                    date_str = date_match.group(1)
                    found_date = True
                
                # Nếu không thấy, leo lên cha để tìm (Cho trường hợp BCTC)
                if not found_date:
                    parent = a_tag.find_parent(id=True) # Tìm div cha có ID (như id="810")
                    if parent:
                        # Tìm thẻ p đầu tiên trong block này (thường là tiêu đề nhóm chứa ngày)
                        header_p = parent.find('p')
                        if header_p:
                            header_text = header_p.get_text(strip=True)
                            date_match_parent = re.search(r'(\d{2}/\d{2}/\d{4})', header_text)
                            if date_match_parent:
                                date_str = date_match_parent.group(1)
                                found_date = True
                
                # --- 3. KIỂM TRA NĂM ---
                try:
                    d_obj = datetime.strptime(date_str, "%d/%m/%Y")
                    if d_obj.year != current_year:
                        continue # Bỏ qua năm cũ
                except:
                    # Nếu không parse được ngày, kiểm tra xem link có chứa "2025" không
                    if str(current_year) not in link and str(current_year) not in raw_text:
                        continue

                # --- 4. CHUẨN HÓA TIÊU ĐỀ ---
                # Nếu text quá dài hoặc chứa ngày, làm sạch
                title = raw_text.replace(date_str, "").strip()
                title = re.sub(r'\s+', ' ', title) # Xóa khoảng trắng thừa
                if len(title) < 5: title = "Tài liệu Eximbank"

                # Check trùng
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue

                new_items.append({
                    "source": f"EIB - {target['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

    except Exception as e:
        print(f"[EIB] Lỗi: {e}")
    finally:
        driver.quit()
        
    return new_items

def fetch_msb_news(seen_ids):
    """
    Hàm cào MSB (Maritime Bank) - Phiên bản Selenium.
    - Lý do: Dữ liệu được render bằng JS (Liferay), requests không lấy được.
    - Chiến thuật: Chờ class .baocao-item xuất hiện rồi mới cào.
    """
    
    current_year = datetime.now().year
    # current_year = 2025 # Mở dòng này để test
    
    # Danh sách link cần cào
    targets = [
        {"name": "ĐHĐCĐ", "url": "https://www.msb.com.vn/vi/nha-dau-tu/dai-hoi-dong-co-dong.html"},
        {"name": "BCTC", "url": "https://www.msb.com.vn/vi/nha-dau-tu/bao-cao-tai-chinh.html"}
    ]
    
    # Cấu hình Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    new_items = []
    print(f"--- 🚀 Bắt đầu quét MSB (Selenium Mode - Năm {current_year}) ---")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)

    try:
        for target in targets:
            # print(f"   >> Đang tải: {target['name']}...")
            driver.get(target['url'])
            
            # 1. CHỜ DỮ LIỆU XUẤT HIỆN
            # Chờ tối đa 15s cho đến khi class 'baocao-item' xuất hiện
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "baocao-item"))
                )
                # Chờ thêm 2s để các script render hoàn tất hẳn
                time.sleep(2)
            except:
                print(f"   ! Timeout: Không thấy dữ liệu tại {target['name']}")
                continue

            # 2. PARSE HTML ĐÃ RENDER
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.select('.baocao-item')
            
            # print(f"      -> Tìm thấy {len(items)} mục.")
            
            for item in items:
                # --- LẤY NGÀY (Logic cũ - vẫn đúng với Element) ---
                p_tag = item.find('p')
                if not p_tag: continue
                
                raw_date_text = p_tag.get_text(" ", strip=True) 
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', raw_date_text)
                
                date_str = str(current_year)
                if date_match:
                    extracted_date = date_match.group(1)
                    try:
                        d_obj = datetime.strptime(extracted_date, "%d/%m/%Y")
                        if d_obj.year != current_year:
                            continue # Bỏ qua năm cũ
                        date_str = extracted_date
                    except: continue
                else:
                    continue

                # --- LẤY TIÊU ĐỀ & LINK ---
                h3_tag = item.find('h3')
                if not h3_tag: continue
                title = h3_tag.get_text(strip=True)

                a_tag = item.find('a')
                if not a_tag: continue
                link = a_tag.get('href')
                
                if not link: continue
                if not link.startswith('http'):
                    link = f"https://www.msb.com.vn{link}"

                # Check trùng
                if link in seen_ids: continue
                if any(x['id'] == link for x in new_items): continue

                new_items.append({
                    "source": f"MSB - {target['name']}",
                    "id": link,
                    "title": title,
                    "date": date_str,
                    "link": link
                })

    except Exception as e:
        print(f"[MSB] Lỗi Selenium: {e}")
    finally:
        driver.quit()
        
    return new_items

def fetch_bvh_news(seen_ids):
    """
    Hàm cào BVH - Phiên bản Final (Đã fix cấu trúc CBTT f-panel).
    """
    current_year = datetime.now().year
    # current_year = 2025 # Mở dòng này để test
    
    url = "https://baoviet.com.vn/vi/quan-he-co-dong"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    new_items = []
    print(f"--- 🚀 Bắt đầu quét BVH (V4 Final - Năm {current_year}) ---")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(30)

    try:
        driver.get(url)
        time.sleep(3)

        # ==================================================================
        # 1. XỬ LÝ CÔNG BỐ THÔNG TIN (CBTT) - Bộ lọc trên
        # ==================================================================
        # print("   >> [1/2] Đang xử lý CBTT...")
        try:
            # --- FILTER NĂM ---
            # Tìm ô chọn năm CBTT (ko có đuôi --2)
            nice_select_cbtt = driver.find_element(By.CSS_SELECTOR, "div.js-form-item-field-doc-year .nice-select")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nice_select_cbtt)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", nice_select_cbtt)
            time.sleep(1)
            
            # Chọn năm
            options = nice_select_cbtt.find_elements(By.CSS_SELECTOR, "ul.list li")
            found_year_cbtt = False
            for opt in options:
                if str(current_year) in opt.get_attribute("innerText"):
                    driver.execute_script("arguments[0].click();", opt)
                    found_year_cbtt = True
                    break
            
            if found_year_cbtt:
                # Bấm Apply (ID: edit-submit-document-report)
                apply_btn = driver.find_element(By.ID, "edit-submit-document-report")
                driver.execute_script("arguments[0].click();", apply_btn)
                time.sleep(5) # Chờ reload
            
            # --- CÀO DỮ LIỆU CBTT (LOGIC MỚI) ---
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Tìm container lớn bao quanh các accordion
            cbtt_container = soup.select_one('.tlBCao-table')
            
            if cbtt_container:
                # Tìm tất cả thẻ f-panel (Dù nằm trong accordion đóng hay mở thì source vẫn có)
                items = cbtt_container.select('.f-panel')
                
                # print(f"      -> Tìm thấy {len(items)} tin CBTT.")
                
                for item in items:
                    # 1. Tiêu đề: h3.post__title
                    #
                    title_tag = item.select_one('.post__title')
                    if not title_tag: continue
                    title = title_tag.get_text(strip=True)
                    
                    # 2. Link: a.btn-link
                    #
                    link_tag = item.select_one('a.btn-link')
                    if not link_tag: continue
                    link = link_tag.get('href')
                    
                    if not link: continue
                    if not link.startswith('http'): link = f"https://baoviet.com.vn{link}"
                    
                    # 3. Ngày: p.post__date -> time
                    date_str = str(current_year)
                    time_tag = item.select_one('.post__date time')
                    if time_tag:
                        try:
                            # Text dạng: 01.12.2025
                            raw_date = time_tag.get_text(strip=True)
                            d = datetime.strptime(raw_date, "%d.%m.%Y")
                            if d.year == current_year:
                                date_str = d.strftime("%d/%m/%Y")
                            else:
                                continue # Bỏ qua năm cũ
                        except: pass

                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue
                    
                    new_items.append({
                        "source": "BVH - CBTT",
                        "id": link, "title": title, "date": date_str, "link": link
                    })
        except Exception as e:
            print(f"   ! Lỗi phần CBTT: {e}")

        # ==================================================================
        # 2. XỬ LÝ BÁO CÁO TÀI CHÍNH (BCTC) - Bộ lọc dưới (Đã chạy OK)
        # ==================================================================
        # print("   >> [2/2] Đang xử lý BCTC...")
        try:
            # Tìm ô select BCTC (CÓ đuôi --2)
            bctc_nice_select = driver.find_element(By.XPATH, "//select[@id='edit-field-doc-year--2']/following-sibling::div[contains(@class, 'nice-select')]")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", bctc_nice_select)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", bctc_nice_select)
            time.sleep(1)
            
            options_bctc = bctc_nice_select.find_elements(By.CSS_SELECTOR, "ul.list li")
            found_year_bctc = False
            for opt in options_bctc:
                if str(current_year) in opt.get_attribute("innerText"):
                    driver.execute_script("arguments[0].click();", opt)
                    found_year_bctc = True
                    break
            
            if found_year_bctc:
                apply_btn_bctc = driver.find_element(By.ID, "edit-submit-document-report--2")
                driver.execute_script("arguments[0].click();", apply_btn_bctc)
                time.sleep(5)
            
            # --- CÀO DỮ LIỆU BCTC ---
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Container: view-display-id-bao_cao_tai_chinh_block
            bctc_block = soup.select_one('.view-display-id-bao_cao_tai_chinh_block')
            
            if bctc_block:
                links = bctc_block.select('ul.item-list li a')
                for a_tag in links:
                    link = a_tag.get('href')
                    title = a_tag.get_text(strip=True)
                    
                    if not link or not title: continue
                    if not link.startswith('http'): link = f"https://baoviet.com.vn{link}"
                    
                    # BCTC không có ngày cụ thể, lọc theo Text Title
                    if str(current_year) not in title and str(current_year - 1) in title:
                        continue
                        
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue

                    new_items.append({
                        "source": "BVH - BCTC",
                        "id": link, "title": title, "date": str(current_year), "link": link
                    })

        except Exception as e:
            # print(f"   ! Lỗi phần BCTC: {e}")
            pass

    except Exception as e:
        print(f"[BVH] Lỗi Selenium: {e}")
    finally:
        driver.quit()
        
    return new_items
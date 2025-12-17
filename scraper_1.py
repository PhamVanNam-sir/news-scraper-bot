import requests
from bs4 import BeautifulSoup
import time

def fetch_vcb_news(seen_ids):
    """
    Hàm cào tin tức từ VCB (Đã bổ sung field 'date').
    """
    # ... (Phần import và setup giữ nguyên) ...
    from datetime import datetime # Nhớ import nếu thiếu
    current_year = str(datetime.now().year)

    # 1. Cấu hình danh sách URL API cần quét
    api_urls = [
        "https://vietcombank.com.vn/sxa/InvestmentApi/InvestmentDetailResults/?l=vi-VN&s={3B4CF33A-7B38-431C-B2C5-42EBBE48896A}&itemid={158CFC95-E771-4FC2-B6EA-1D93BCD69E70}&sig=investment-detail&o=SortOrder,Descending&v={93B61FD8-B8A6-48CA-B2B0-1C9494F79C93}&investmentFacetSource={2B981AA6-1CC7-4C36-8A64-85D2F82E21A5}&investmentdocumentmenu=B%C3%A1o%20c%C3%A1o%20T%C3%A0i%20ch%C3%ADnh&investmentdocumentchip=B%C3%A1o%20c%C3%A1o%20%C4%91%E1%BB%8Bnh%20k%E1%BB%B3&investmentdocumentyear=N%C4%83m%202025&p=200",
        "https://vietcombank.com.vn/sxa/InvestmentApi/InvestmentDetailResults/?l=vi-VN&s={3B4CF33A-7B38-431C-B2C5-42EBBE48896A}&itemid={158CFC95-E771-4FC2-B6EA-1D93BCD69E70}&sig=investment-detail&o=SortOrder,Descending&v={93B61FD8-B8A6-48CA-B2B0-1C9494F79C93}&investmentFacetSource={2B981AA6-1CC7-4C36-8A64-85D2F82E21A5}&investmentdocumentmenu=%C4%90%E1%BA%A1i%20h%E1%BB%99i%20%C4%91%E1%BB%93ng%20c%E1%BB%95%20%C4%91%C3%B4ng%20b%E1%BA%A5t%20th%C6%B0%E1%BB%9Dng&investmentdocumentchip=%C4%90%E1%BA%A1i%20h%E1%BB%99i%20%C4%91%E1%BB%93ng%20c%E1%BB%95%20%C4%91%C3%B4ng&investmentdocumentyear=N%C4%83m%202025&p=200",
        "https://vietcombank.com.vn/sxa/InvestmentApi/InvestmentDetailResults/?l=vi-VN&s={3B4CF33A-7B38-431C-B2C5-42EBBE48896A}&itemid={158CFC95-E771-4FC2-B6EA-1D93BCD69E70}&sig=investment-detail&o=SortOrder,Descending&v={93B61FD8-B8A6-48CA-B2B0-1C9494F79C93}&investmentFacetSource={2B981AA6-1CC7-4C36-8A64-85D2F82E21A5}&investmentdocumentmenu=%C4%90%E1%BA%A1i%20h%E1%BB%99i%20%C4%91%E1%BB%93ng%20c%E1%BB%95%20%C4%91%C3%B4ng%20th%C6%B0%E1%BB%9Dng%20ni%C3%AAn%20n%C4%83m%202025&investmentdocumentchip=%C4%90%E1%BA%A1i%20h%E1%BB%99i%20%C4%91%E1%BB%93ng%20c%E1%BB%95%20%C4%91%C3%B4ng&investmentdocumentyear=N%C4%83m%202025&p=200"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    new_items = []

    for url in api_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200: continue

            data = response.json()
            if data.get('Count', 0) == 0: continue

            sections = data.get('SectionResults', [])
            for section in sections:
                results = section.get('Results', [])
                for item in results:
                    news_id = item.get('Id')
                    if news_id in seen_ids: continue
                    
                    raw_html = item.get('Html', '')
                    if not raw_html: continue

                    soup = BeautifulSoup(raw_html, 'html.parser')
                    a_tag = soup.find('a')
                    
                    if a_tag:
                        relative_link = a_tag.get('href')
                        title = a_tag.get_text(strip=True)
                        full_link = f"https://vietcombank.com.vn{relative_link}"
                        
                        # --- FIX: LẤY NGÀY HOẶC GÁN MẶC ĐỊNH ---
                        # VCB API có trả về PublishDate, ta lấy luôn cho xịn
                        # Dạng: /Date(1713546000000)/ -> Cần xử lý hơi cực, nên ta gán tạm current_year
                        # Vì URL đã filter sẵn năm 2025 rồi
                        
                        new_items.append({
                            "source": "Vietcombank",
                            "id": news_id,
                            "title": title,
                            "date": current_year, # <--- ĐÃ BỔ SUNG DATE
                            "link": full_link
                        })
            
            time.sleep(0.5)

        except Exception as e:
            print(f"[VCB] Exception: {e}")
            continue

    return new_items

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time

# --- CẤU HÌNH CÁC TRANG CẦN CÀO ---
# Bạn thêm bớt link thoải mái ở đây mà không cần sửa code logic bên dưới
VIETIN_CONFIG = [
    {
        "name": "ĐHĐCĐ (Shareholder)",
        "url": "https://investor.vietinbank.vn/ShareholderMeetings.aspx",
        "payload_key": "Cart_ctl00_webPartManager_wp218868305_wp414346945_cbEvents_Callback_Param",
        # Selector dùng để tìm vùng chứa tin (Shareholder dùng p.event_title)
        "selector_tag": "p", 
        "selector_class": "event_title",
        "container_id": None # Không cần lọc theo ID bảng
    },
    {
        "name": "Công bố thông tin (Filings)",
        "url": "https://investor.vietinbank.vn/Filings.aspx",
        "payload_key": "Cart_ctl00_webPartManager_wp1515247873_wp473486273_cbNews_Callback_Param",
        # Filings dùng div.rpt_title
        "selector_tag": "div",
        "selector_class": "rpt_title",
        "container_id": None
    },
    {
        "name": "Báo cáo tài chính (Reports)",
        "url": "https://investor.vietinbank.vn/Download.aspx",
        "payload_key": "Cart_ctl00_webPartManager_wp1220103785_wp1185227757_cbReportsMerge_Callback_Param",
        # BCTC đặc biệt hơn: Phải tìm trong bảng có ID cụ thể để loại bỏ cái "Individual"
        "selector_tag": "tr", # Tìm các dòng trong bảng
        "selector_class": None,
        "container_id": "tblReportsMerge" # <--- QUAN TRỌNG: Chỉ cào trong bảng Hợp Nhất
    },
    {
        "name": "Sự kiện khác (Other Events)",
        "url": "https://investor.vietinbank.vn/OtherEvents.aspx",
        "payload_key": "Cart_ctl00_webPartManager_wp89254061_wp1184749212_cbEvents_Callback_Param",
        # Thường cấu trúc giống Shareholder
        "selector_tag": "p",
        "selector_class": "event_title",
        "container_id": None
    }
]

def fetch_all_vietinbank(seen_ids):
    """
    Hàm tổng hợp cào tất cả các mục của VietinBank (Đã bổ sung field 'date').
    """
    # ... (Phần config giữ nguyên) ...
    # Để gọn, mình chỉ viết lại đoạn xử lý cuối vòng lặp
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    current_year = str(datetime.now().year)
    all_new_items = []

    print(f"--- Bắt đầu quét VietinBank (Năm {current_year}) ---")

    for config in VIETIN_CONFIG:
        try:
            key = config['payload_key']
            payload = [(key, current_year), (key, "0")]
            
            response = requests.post(config['url'], headers=headers, data=payload, timeout=20)
            if response.status_code != 200: continue

            raw_content = response.text
            match = re.search(r'<!\[CDATA\[(.*?)\]\]>', raw_content, re.DOTALL)
            if not match: continue

            html_content = match.group(1)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            search_scope = soup
            if config['container_id']:
                found_container = soup.find(id=config['container_id'])
                if found_container: search_scope = found_container
                else: continue

            if config['selector_class']:
                elements = search_scope.find_all(config['selector_tag'], class_=config['selector_class'])
            else:
                elements = search_scope.find_all(config['selector_tag'])

            for el in elements:
                a_tag = el.find('a')
                if not a_tag: continue
                
                link = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                if not link or not title: continue
                if "javascript" in link.lower(): continue

                if not link.startswith("http"):
                    full_link = f"https://investor.vietinbank.vn{link}"
                else:
                    full_link = link

                id_match = re.search(r'(\d+)\.aspx', full_link)
                news_id = id_match.group(1) if id_match else full_link
                
                if news_id in seen_ids: continue

                all_new_items.append({
                    "source": f"VietinBank - {config['name']}",
                    "id": news_id,
                    "title": title,
                    "date": current_year, # <--- ĐÃ BỔ SUNG DATE
                    "link": full_link
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[{config['name']}] Lỗi ngoại lệ: {e}")
            continue

    return all_new_items

import requests
import re
import html
import ssl
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# --- CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

def fetch_bidv_data(seen_ids):
    """
    Hàm cào tổng hợp BIDV:
    1. Thông tin cổ đông
    2. Báo cáo và Tài liệu (BCTC)
    3. Lịch sự kiện
    
    Chỉ lấy dữ liệu của năm hiện tại (2025).
    """
    
    # Danh sách các link cần cào
    target_urls = [
        "https://bidv.com.vn/vn/quan-he-nha-dau-tu/thong-tin-co-dong",
        "https://bidv.com.vn/vn/quan-he-nha-dau-tu/bao-cao-va-tai-lieu",
        "https://bidv.com.vn/vn/quan-he-nha-dau-tu/lich-su-kien"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    current_year = datetime.now().year
    new_items = []
    
    # Tạo session chung
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    for url in target_urls:
        try:
            # print(f"--- Đang quét: {url} ---")
            response = session.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[BIDV] Lỗi kết nối {url}: {response.status_code}")
                continue

            raw_content = response.text

            # --- REGEX XỬ LÝ ĐA NĂNG ---
            
            # Pattern 1: Dành cho TÀI LIỆU (có file_title để tải PDF)
            # Cấu trúc: title: ..., publishdate: ..., file_title: ...
            pattern_doc = r"title:\s*formatTitle\('(.*?)'\),\s*publishdate:\s*'(.*?)',\s*file_title:\s*formatTitle\('(.*?)'\)"
            matches_doc = re.findall(pattern_doc, raw_content)

            # Pattern 2: Dành cho SỰ KIỆN / TIN TỨC (có path để xem chi tiết)
            # Cấu trúc: title: ..., publishdate: ..., ..., path: ...
            # Dùng non-greedy (.*?) để tránh nuốt quá nhiều ký tự
            pattern_event = r"title:\s*formatTitle\('(.*?)'\),\s*publishdate:\s*'(.*?)'[\s\S]*?path:\s*'(.*?)'"
            matches_event = re.findall(pattern_event, raw_content)
            
            # Gộp 2 danh sách lại để xử lý
            # Đánh dấu loại để dễ debug: (Title, Date, Link, Type)
            all_matches = [(m[0], m[1], m[2], 'DOC') for m in matches_doc] + \
                          [(m[0], m[1], m[2], 'EVENT') for m in matches_event]

            for item_match in all_matches:
                raw_title, date_str, relative_link, item_type = item_match
                
                # 1. Lọc dữ liệu rác
                if not relative_link or relative_link == "undefined" or relative_link == "":
                    continue
                
                # 2. LỌC NĂM (Logic quan trọng nhất)
                try:
                    # BIDV ngày tháng thường là dd/mm/yyyy
                    pub_date = datetime.strptime(date_str, "%d/%m/%Y")
                    if pub_date.year != current_year:
                        continue # Không phải năm nay thì bỏ qua
                except ValueError:
                    continue # Lỗi ngày tháng -> Bỏ qua

                # 3. Làm sạch tiêu đề
                title = html.unescape(raw_title)
                
                # 4. Xử lý Link hoàn chỉnh
                if not relative_link.startswith("http"):
                    full_link = f"https://bidv.com.vn{relative_link}"
                else:
                    full_link = relative_link

                # 5. Tạo ID và Check trùng
                news_id = full_link # Dùng link làm ID là an toàn nhất

                if news_id in seen_ids:
                    continue
                
                # Đánh dấu nguồn cụ thể để sếp dễ nhìn
                source_name = "BIDV"
                if "lich-su-kien" in url:
                    source_name = "BIDV - Sự Kiện"
                elif "bao-cao" in url:
                    source_name = "BIDV - BCTC & Tài Liệu"
                else:
                    source_name = "BIDV - Cổ Đông"

                # 6. Thêm vào danh sách kết quả
                # Lưu ý: Check lại lần nữa để tránh trùng lặp giữa Pattern 1 và Pattern 2
                # (Vì đôi khi 1 tin vừa có path vừa có file_title)
                is_duplicate_in_batch = False
                for existing in new_items:
                    if existing['id'] == news_id:
                        is_duplicate_in_batch = True
                        break
                
                if not is_duplicate_in_batch:
                    new_items.append({
                        "source": source_name,
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": full_link
                    })

        except Exception as e:
            print(f"[BIDV] Lỗi tại {url}: {e}")
            continue

    return new_items

import requests
from datetime import datetime
import time

def fetch_tcb_news(seen_ids):
    """
    Hàm cào Techcombank (Phiên bản Vét Cạn).
    - Xử lý cả trường hợp file nằm ở Parent (chính item) và file nằm ở Children (documentItems).
    - Quét đủ 6 danh mục.
    - Sắp xếp thời gian chuẩn.
    """
    
    categories = [
        "tai-lieu",
        "nghi-quyet",
        "thong-cao-bao-chi-dhcd",
        "thong-bao-va-thu-moi",
        "bao-cao-tai-chinh-vas",
        "hoi-dong-quan-tri"
    ]

    base_url_template = "https://techcombank.com/graphql/execute.json/techcombank/viewDocumentList%3BcfPath%3D/content/dam/techcombank/master-data/vi/list-view-document/{}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://techcombank.com/"
    }

    current_year = datetime.now().year
    new_items = []

    print(f"--- Bắt đầu quét TCB (Năm {current_year}) ---")

    for cat in categories:
        url = base_url_template.format(cat)
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"[TCB - {cat}] Lỗi: {response.status_code}")
                continue

            json_data = response.json()
            items = json_data.get("data", {}).get("listViewDocumentFragmentList", {}).get("items", [])
            
            if not items: continue

            for item in items:
                # --- 1. CHECK NGÀY THÁNG (Dùng chung cho cả Parent và Child) ---
                date_str = item.get("date") 
                if not date_str: continue

                try:
                    pub_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if pub_date.year != current_year:
                        continue
                except ValueError:
                    continue

                # Lấy tiêu đề gốc (Category Title)
                cat_title = item.get("categoryTitle", {}).get("plaintext", "")
                
                # --- 2. LOGIC VÉT CẠN (QUAN TRỌNG) ---
                
                # A. Kiểm tra CHÍNH NÓ (Parent) - Đây là phần code cũ bị thiếu
                parent_doc_path = item.get("documentPath")
                if parent_doc_path and isinstance(parent_doc_path, dict):
                    file_link = parent_doc_path.get("_publishUrl")
                    
                    if file_link:
                        # Với Parent, tiêu đề chính là cat_title
                        # Kiểm tra thêm documentTitle nếu có
                        doc_title = item.get("documentTitle", {}).get("plaintext")
                        full_title = f"{cat_title} - {doc_title}" if doc_title else cat_title
                        
                        # Thêm vào list (dùng hàm nội bộ hoặc append trực tiếp)
                        if file_link not in seen_ids:
                             new_items.append({
                                "source": f"TCB - {cat}",
                                "id": file_link,
                                "title": full_title.strip(" -"),
                                "date": date_str,
                                "link": file_link,
                                "raw_date": pub_date
                            })

                # B. Kiểm tra CON NÓ (Children) - Logic cũ
                children = item.get("documentItems", [])
                for child in children:
                    child_doc_path = child.get("documentPath")
                    if not child_doc_path or not isinstance(child_doc_path, dict):
                        continue
                        
                    file_link = child_doc_path.get("_publishUrl")
                    if not file_link: continue

                    # Tiêu đề con
                    sub_title = child.get("documentTitle", {}).get("plaintext", "")
                    if sub_title and sub_title.lower() != "tải file":
                        full_title = f"{cat_title} - {sub_title}"
                    else:
                        full_title = cat_title

                    if file_link not in seen_ids:
                        # Kiểm tra xem đã thêm ở bước A chưa để tránh trùng lặp trong cùng 1 vòng lặp
                        is_exist = False
                        for x in new_items:
                            if x['id'] == file_link:
                                is_exist = True
                                break
                        
                        if not is_exist:
                            new_items.append({
                                "source": f"TCB - {cat}",
                                "id": file_link,
                                "title": full_title.strip(" -"),
                                "date": date_str,
                                "link": file_link,
                                "raw_date": pub_date
                            })

            time.sleep(0.2)

        except Exception as e:
            print(f"[TCB - {cat}] Exception: {e}")
            continue

    # Sắp xếp lại từ Mới nhất -> Cũ nhất
    new_items.sort(key=lambda x: x['raw_date'], reverse=True)
    for item in new_items:
        del item['raw_date']

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_mch_news(seen_ids):
    # Cấu hình năm
    target_year_id = "411" 
    target_year_title = "2025"
    current_year = datetime.now().year
    
    categories = [
        "thong-tin-tai-chinh", 
        "cong-bo-thong-tin/thong-tin-cong-bo",
        "dai-hoi-dong-co-dong"
    ]

    base_url_template = "https://masanconsumer.com/quan-he-co-dong/{}/page/{}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []

    print(f"--- 🚀 Bắt đầu quét MCH ---")

    for cat in categories:
        print(f"📂 Đang quét mục: {cat}")
        
        # --- CÀI ĐẶT PHANH TAY: Chỉ quét tối đa 3 trang ---
        for page in range(1, 2): 
            url_path = base_url_template.format(cat, page)
            full_url = f"{url_path}/?yearID={target_year_id}&yearTitle={target_year_title}"
            
            # print(f"   >> Đang tải trang {page}...") 

            try:
                response = requests.get(full_url, headers=headers, timeout=10, verify=False)
                
                # Nếu bị redirect về trang 1 (dấu hiệu hết trang của Masan) thì dừng ngay
                if page > 1 and (response.url == base_url_template.format(cat, 1) or "page/1" in response.url):
                    print("      -> Hết trang (Redirect loop detected).")
                    break

                if response.status_code == 404:
                    print("      -> Hết trang (404).")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm link PDF
                pdf_links = soup.select('a[href$=".pdf"], a[href$=".PDF"]')
                
                if not pdf_links:
                    # print("      -> Không thấy PDF nào.")
                    if page == 1: continue # Trang 1 mà ko có thì lạ, nhưng cứ tiếp tục
                    else: break # Các trang sau ko có thì dừng

                count_added = 0
                for a_tag in pdf_links:
                    link = a_tag.get('href')
                    title = a_tag.get_text(strip=True) or a_tag.get('title') or "Tài liệu PDF"

                    if not link: continue
                    
                    if not link.startswith('http'):
                        link = f"https://masanconsumer.com{link}"

                    # Check trùng
                    if link in seen_ids:
                        continue
                    
                    # Check xem link có chứa năm 2025 không (Optional - để lọc kỹ hơn)
                    # if "2025" not in link and "25" not in link:
                    #     continue 

                    new_items.append({
                        "source": f"MCH - {cat.split('/')[0]}",
                        "id": link,
                        "title": title,
                        "date": str(current_year),
                        "link": link
                    })
                    count_added += 1
                
                # print(f"      -> Lấy được {count_added} tin mới.")
                
                # Nếu trang này không lấy được tin nào mới -> Khả năng là hết tin mới -> Dừng luôn cho nhanh
                # if count_added == 0 and page > 1:
                #    break

            except Exception as e:
                print(f"[MSN] Lỗi kết nối: {e}")
                break
            
    return new_items

import requests
import time
from datetime import datetime

def fetch_vpb_news(seen_ids):
    """
    Hàm cào dữ liệu từ VPBank (API JSON).
    - Tự động ghép URL theo năm hiện tại.
    - Quét 4 danh mục.
    - Vét cạn các file trong 'itemList'.
    """
    
    # 1. Cấu hình danh mục (Params)
    categories = [
        "cong-bo-thong-tin-khac",
        "dai-hoi-co-dong",
        "bao-cao-tai-chinh/vas",
        "tai-lieu-cho-nha-dau-tu/bao-cao-phan-tich-ket-qua-hoat-dong"
    ]

    # Endpoint API gốc
    api_url = "https://www.vpbank.com.vn/uiux-api/api/document"
    domain = "https://www.vpbank.com.vn"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.vpbank.com.vn/"
    }

    current_year = datetime.now().year
    new_items = []

    print(f"--- Bắt đầu quét VPBank (Năm {current_year}) ---")

    for cat in categories:
        # Cấu trúc path: /quan-he-nha-dau-tu/{category}/{year}
        category_path = f"/quan-he-nha-dau-tu/{cat}/{current_year}"
        
        # Quét tối đa 3 trang (thường 1 năm không quá nhiều tin/mục)
        for page in range(1, 2):
            params = {
                "lang": "vi",
                "categoryPath": category_path,
                "pageSize": 10, # Lấy 10 tin mỗi lần
                "pageIndex": page
            }

            try:
                response = requests.get(api_url, headers=headers, params=params, timeout=15)
                
                if response.status_code != 200:
                    print(f"[VPB] Lỗi kết nối: {response.status_code}")
                    break

                json_data = response.json()
                items = json_data.get("data", [])

                # Nếu không có dữ liệu -> Hết trang -> Dừng danh mục này
                if not items:
                    break
                
                for item in items:
                    # Lấy thông tin chung của bài viết
                    article_title = item.get("title", "")
                    publish_date = item.get("publishDate", "") # 2025-10-17T18:00...
                    
                    # Xử lý ngày tháng cho đẹp (bỏ phần giờ)
                    if publish_date:
                        try:
                            date_obj = datetime.fromisoformat(publish_date)
                            date_str = date_obj.strftime("%d/%m/%Y")
                        except:
                            date_str = str(current_year)
                    else:
                        date_str = str(current_year)

                    # QUAN TRỌNG: Lấy file đính kèm trong 'itemList'
                    file_list = item.get("itemList", [])
                    
                    for file_info in file_list:
                        file_url = file_info.get("url")
                        file_title = file_info.get("title") or article_title
                        
                        if not file_url:
                            continue

                        # Ghép domain nếu thiếu
                        if not file_url.startswith("http"):
                            full_link = f"{domain}{file_url}"
                        else:
                            full_link = file_url

                        # Tạo ID và Check trùng
                        news_id = full_link 

                        if news_id in seen_ids:
                            continue

                        # Đóng gói
                        new_items.append({
                            "source": f"VPBank - {cat.split('/')[-1]}", # Lấy tên ngắn gọn
                            "id": news_id,
                            "title": file_title, # Ưu tiên tên file
                            "date": date_str,
                            "link": full_link
                        })
                
                # Nghỉ nhẹ
                time.sleep(0.5)

            except Exception as e:
                print(f"[VPB] Lỗi xử lý: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
import re # Cần thêm thư viện Regex để bắt cookie
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_vgi_news(seen_ids):
    """
    Hàm cào Viettel Global (VGI).
    - Fix lỗi SSL.
    - Fix lỗi Cookie Challenge (D1N).
    """
    
    current_year = datetime.now().year
    categories = [
        "dai-hoi-dong-co-dong",
        "dieu-le-tong-cong-ty",
        "bao-cao-tai-chinh",
        "tin-co-dong"
    ]
    
    base_url_template = "https://www.viettelglobal.com.vn/{}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Tạo session và gắn Adapter
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét VGI (Năm {current_year}) ---")

    for cat in categories:
        for page in range(1, 2):
            url = base_url_template.format(cat)
            params = {"year": current_year, "page": page}
            
            try:
                # Lần gọi 1: Có thể bị chặn bởi Cookie Challenge
                response = session.get(url, headers=headers, params=params, timeout=20, verify=False)
                
                # --- LOGIC BYPASS COOKIE (Mới thêm) ---
                if "document.cookie" in response.text:
                    # print(f"   ! Phát hiện tường lửa tại {cat}, đang vượt qua...")
                    
                    # Dùng Regex tìm chuỗi: document.cookie="KEY=VALUE"
                    # Pattern tìm: mọi ký tự trừ dấu " và dấu =
                    match = re.search(r'document\.cookie="([^=]+)=([^"]+)"', response.text)
                    
                    if match:
                        cookie_name = match.group(1) # D1N
                        cookie_val = match.group(2)  # Chuỗi mã hóa
                        
                        # Gán cookie vào session
                        session.cookies.set(cookie_name, cookie_val, domain=".viettelglobal.com.vn")
                        
                        # Gọi lại lần 2 (Lúc này đã có cookie trong người)
                        response = session.get(url, headers=headers, params=params, timeout=20, verify=False)
                    else:
                        print(f"[VGI] Không giải mã được cookie tại {cat}")
                        continue

                # Sau khi bypass xong, xử lý như bình thường
                if response.status_code != 200:
                    print(f"[VGI] Lỗi kết nối {cat}: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                all_links = soup.find_all('a', href=True)
                
                count_in_page = 0
                for a_tag in all_links:
                    link = a_tag.get('href')
                    title = a_tag.get_text(strip=True) or a_tag.get('title')

                    if not link or not title: continue
                    
                    if not link.startswith('http'):
                        link = f"https://www.viettelglobal.com.vn{link}"
                    
                    # Logic lọc file/tin
                    is_valid = False
                    lower_link = link.lower()
                    if lower_link.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                        is_valid = True
                    elif cat in lower_link:
                        is_valid = True
                    
                    if not is_valid: continue
                    if len(title) < 5 or "xem thêm" in title.lower(): continue

                    # Check trùng
                    news_id = link
                    if news_id in seen_ids: continue
                    
                    # Check trùng nội bộ
                    if any(x['id'] == news_id for x in new_items): continue

                    new_items.append({
                        "source": f"Viettel Global - {cat}",
                        "id": news_id,
                        "title": title,
                        "date": str(current_year),
                        "link": link
                    })
                    count_in_page += 1
                
                if count_in_page == 0:
                    break
                
                time.sleep(0.5)

            except Exception as e:
                print(f"[VGI] Lỗi tại {cat}: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo SSL (nếu có)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX (Giữ nguyên để đảm bảo kết nối mượt) ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_hpg_news(seen_ids):
    """
    Hàm cào dữ liệu từ Hòa Phát (HPG).
    - Hỗ trợ cả dạng Tin tức (Grid) và Tài liệu (Table).
    - Lọc theo năm hiện tại (sort_year).
    """
    
    current_year = datetime.now().year
    
    # Danh sách các mục cần cào
    categories = [
        "cong-bo-thong-tin",
        "bao-cao-tai-chinh",
        "dai-hoi-co-dong"
    ]

    base_url_template = "https://www.hoaphat.com.vn/quan-he-co-dong/{}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Tạo session
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét HPG (Năm {current_year}) ---")

    for cat in categories:
        # Quét tối đa 3 trang (Năm hiện tại thường ít tin)
        for page in range(1, 2):
            url = base_url_template.format(cat)
            
            # Params chuẩn của HPG
            params = {
                "sort_year": current_year,
                "page": page
            }
            
            try:
                response = session.get(url, headers=headers, params=params, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[HPG] Lỗi kết nối {cat}: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # --- CHIẾN THUẬT "HYBRID PARSER" (Xử lý cả 2 dạng giao diện) ---
                
                found_items_in_page = 0
                
                # CASE 1: Dạng Tin tức (Thường là các div có class 'item')
                news_items = soup.select('.item')
                
                # CASE 2: Dạng Bảng (Thường là tr trong table, dùng cho BCTC)
                table_rows = soup.select('table tr')
                
                # Gộp chung lại để xử lý (lọc bỏ các tr tiêu đề)
                all_elements = news_items + [tr for tr in table_rows if tr.find('a')]

                if not all_elements:
                    if page == 1: 
                        # print(f"   [HPG - {cat}] Không thấy dữ liệu ở trang 1.")
                        pass
                    else:
                        break # Hết trang -> Dừng

                for element in all_elements:
                    # Tìm thẻ a (Link và Title)
                    a_tag = element.find('a')
                    if not a_tag: continue
                    
                    link = a_tag.get('href')
                    title = a_tag.get_text(strip=True) or a_tag.get('title')
                    
                    if not link or not title: continue

                    # Tìm ngày tháng (HPG thường để trong class 'time' hoặc td cuối cùng)
                    date_str = ""
                    time_tag = element.select_one('.time')
                    if time_tag:
                        date_str = time_tag.get_text(strip=True)
                    else:
                        # Nếu là dạng bảng, thử lấy cột cuối cùng (thường là ngày)
                        tds = element.find_all('td')
                        if tds:
                            date_str = tds[-1].get_text(strip=True)

                    # Chuẩn hóa Link
                    if not link.startswith('http'):
                        link = f"https://www.hoaphat.com.vn{link}"
                    
                    # --- CHECK TRÙNG ---
                    news_id = link
                    if news_id in seen_ids:
                        continue
                    
                    # Check trùng nội bộ
                    if any(x['id'] == news_id for x in new_items):
                        continue
                    
                    # --- CHECK NĂM (Double Check) ---
                    # Dù đã dùng param sort_year, nhưng check thêm cho chắc
                    is_valid_year = True
                    if date_str:
                        try:
                            # HPG format thường là dd/mm/yyyy
                            pub_date = datetime.strptime(date_str, "%d/%m/%Y")
                            if pub_date.year != current_year:
                                is_valid_year = False
                        except:
                            pass # Lỗi parse ngày thì cứ tin vào param sort_year của server
                    
                    if not is_valid_year:
                        continue

                    new_items.append({
                        "source": f"Hoa Phat - {cat}",
                        "id": news_id,
                        "title": title,
                        "date": date_str or str(current_year),
                        "link": link
                    })
                    found_items_in_page += 1
                
                if found_items_in_page == 0:
                    break # Hết tin ở trang này -> Dừng quét danh mục
                
                time.sleep(0.5)

            except Exception as e:
                print(f"[HPG] Lỗi tại {cat}: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX (Vẫn giữ để đảm bảo kết nối ổn định) ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_acv_news(seen_ids):
    """
    Hàm cào tin tức từ ACV (Airports Corporation of Vietnam).
    - URL: https://acv.vn/tin-tuc/{category}/page/{page}
    - Lọc chặt chẽ theo năm hiện tại.
    """
    
    # Lấy năm hiện tại (2025)
    current_year = datetime.now().year
    
    categories = [
        "bao-cao-tai-chinh",
        "dai-hoi-dong-co-dong",
        "thong-bao-co-dong"
    ]
    
    base_url_template = "https://acv.vn/tin-tuc/{}/page/{}"
    domain = "https://acv.vn"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Tạo session và gắn Adapter
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét ACV (Năm {current_year}) ---")

    for cat in categories:
        # Quét 3 trang đầu mỗi mục
        for page in range(1, 2):
            url = base_url_template.format(cat, page)
            
            try:
                # ACV đôi khi phản hồi chậm, để timeout 20s
                response = session.get(url, headers=headers, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[ACV] Lỗi kết nối {cat}: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tìm danh sách tin (li.item)
                items = soup.select('li.item')
                
                if not items:
                    break # Hết tin hoặc lỗi cấu trúc -> Dừng
                
                count_in_page = 0
                
                for item in items:
                    # --- 1. XỬ LÝ NGÀY THÁNG (Quan trọng) ---
                    # HTML mẫu: <div class="datetime"><span>16:17 | 30/10/2024</span></div>
                    date_tag = item.select_one('.datetime span')
                    if not date_tag:
                        continue
                        
                    date_raw = date_tag.get_text(strip=True) 
                    
                    try:
                        # Cắt chuỗi lấy phần ngày: "30/10/2024"
                        date_part = date_raw.split('|')[-1].strip()
                        pub_date = datetime.strptime(date_part, "%d/%m/%Y")
                        
                        # LỌC NĂM: Nếu không phải năm nay -> Bỏ qua
                        if pub_date.year != current_year:
                            continue
                    except:
                        continue # Lỗi format ngày -> Bỏ qua

                    # --- 2. LẤY TIÊU ĐỀ & LINK ---
                    title_tag = item.select_one('.title a')
                    if not title_tag:
                        continue
                        
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href')
                    
                    if not link: continue
                        
                    # Ghép domain nếu thiếu
                    if not link.startswith('http'):
                        link = f"{domain}{link}"

                    # --- 3. CHECK TRÙNG & LƯU ---
                    news_id = link
                    if news_id in seen_ids:
                        continue
                    
                    # Check trùng lặp trong cùng 1 lần chạy
                    if any(x['id'] == news_id for x in new_items):
                        continue

                    new_items.append({
                        "source": f"ACV - {cat}",
                        "id": news_id,
                        "title": title,
                        "date": date_part,
                        "link": link
                    })
                    count_in_page += 1
                
                # Nếu quét cả trang mà không thấy tin nào của năm nay -> Dừng luôn danh mục này
                # (Vì tin được sắp xếp theo thời gian, trang sau chắc chắn cũ hơn)
                if count_in_page == 0:
                     break
                
                time.sleep(0.5)

            except Exception as e:
                print(f"[ACV] Lỗi ngoại lệ tại {cat}: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX (Chuẩn bài cho các web doanh nghiệp VN) ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_fpt_news(seen_ids):
    """
    Hàm cào dữ liệu nhà đầu tư từ FPT.
    - Quét 3 danh mục chính: Báo cáo thường niên, ĐHĐCĐ, CBTT.
    - Lọc theo năm hiện tại (dựa trên param URL và check lại content).
    """
    
    current_year = datetime.now().year
    
    # Cấu hình danh mục và param ID tương ứng
    # Lưu ý: FPT dùng param id để filter server-side
    categories = [
        {
            "name": "Báo cáo thường niên",
            "url": "https://fpt.com/vi/nha-dau-tu/bao-cao-thuong-nien",
            "id_param": f"monthly-year-{current_year}"
        },
        {
            "name": "Đại hội đồng cổ đông",
            "url": "https://fpt.com/vi/nha-dau-tu/dai-hoi-co-dong",
            "id_param": f"shareholders-year-{current_year}"
        },
        {
            "name": "Công bố thông tin",
            "url": "https://fpt.com/vi/nha-dau-tu/thong-tin-cong-bo",
            "id_param": f"whats-year-{current_year}"
        }
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Tạo session
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét FPT (Năm {current_year}) ---")

    for cat in categories:
        # FPT thường show hết trong 1 trang nếu filter theo năm, nhưng cứ loop nhẹ 1-2 trang cho chắc
        # Tuy nhiên, link FPT bạn đưa là dạng filter param, thường không có paging kiểu /page/2 trên URL này
        # Mà nó dùng JS load more hoặc show all. 
        # Với requests, ta cứ gọi link gốc kèm param id là lấy được list đầu tiên.
        
        full_url = f"{cat['url']}?id={cat['id_param']}"
        
        try:
            # print(f"   >> Đang tải: {cat['name']}...")
            response = session.get(full_url, headers=headers, timeout=20, verify=False)
            
            if response.status_code != 200:
                print(f"[FPT] Lỗi kết nối {cat['name']}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- CHIẾN THUẬT TÌM KIẾM ---
            # FPT thường để tin trong các thẻ div có class chứa 'item'
            # Hoặc ta tìm tất cả thẻ 'a' có chứa link PDF hoặc link chi tiết
            
            # Tìm vùng nội dung chính để tránh menu/footer (thường là main hoặc content)
            main_content = soup.select_one('main') or soup.select_one('.main-content') or soup
            
            # Lấy tất cả các khối tin (thường là .item hoặc .col-)
            # Cách an toàn nhất: Tìm tất cả thẻ 'a'
            all_links = main_content.find_all('a', href=True)
            
            count_in_cat = 0
            
            for a_tag in all_links:
                link = a_tag.get('href')
                title = a_tag.get_text(strip=True) or a_tag.get('title')

                # 1. Lọc rác
                if not link or not title: continue
                
                # 2. Chuẩn hóa Link
                # Link FPT hay có dạng /-/media/... (Sitecore)
                if link.startswith('/'):
                    link = f"https://fpt.com{link}"
                
                # 3. Logic Lọc "Đúng cái cần lấy":
                is_valid = False
                
                # Ưu tiên 1: Link là file tài liệu (PDF, DOC, ZIP)
                if link.lower().endswith(('.pdf', '.doc', '.docx', '.zip', '.rar')):
                    is_valid = True
                
                # Ưu tiên 2: Link chi tiết tin tức (thường chứa slug dài)
                # Tránh link quay về trang chủ, link menu ngắn
                elif len(link) > 40 and '/nha-dau-tu/' in link:
                    is_valid = True

                if not is_valid: continue

                # 4. Kiểm tra Năm (Double check content)
                # Thử tìm ngày tháng xung quanh thẻ a (parent, sibling)
                date_str = str(current_year) # Mặc định
                
                # Tìm thử class 'date' hoặc 'time' gần đó
                parent = a_tag.find_parent()
                if parent:
                    date_tag = parent.find(class_=lambda x: x and ('date' in x or 'time' in x))
                    if not date_tag: # Thử tìm ở ông nội
                        grandparent = parent.find_parent()
                        if grandparent:
                            date_tag = grandparent.find(class_=lambda x: x and ('date' in x or 'time' in x))
                    
                    if date_tag:
                        raw_date = date_tag.get_text(strip=True)
                        # FPT format: 15/04/2025
                        try:
                             # Cố gắng parse ngày
                            import re
                            date_match = re.search(r'\d{2}/\d{2}/\d{4}', raw_date)
                            if date_match:
                                date_str = date_match.group(0)
                                parsed_year = datetime.strptime(date_str, "%d/%m/%Y").year
                                if parsed_year != current_year:
                                    continue # Bỏ qua tin năm cũ
                        except:
                            pass

                # 5. Check trùng
                news_id = link
                if news_id in seen_ids: continue
                
                if any(x['id'] == news_id for x in new_items): continue

                new_items.append({
                    "source": f"FPT - {cat['name']}",
                    "id": news_id,
                    "title": title,
                    "date": date_str,
                    "link": link
                })
                count_in_cat += 1

            time.sleep(0.5)

        except Exception as e:
            print(f"[FPT] Lỗi tại {cat['name']}: {e}")
            continue

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
import re
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. BỘ DỊCH NGÀY TIẾNG VIỆT (Nâng cấp) ---
def parse_vietnamese_date(date_str):
    if not date_str: return None
    
    # Chuẩn hóa: bỏ chữ "Đăng ngày:", chuyển thường, bỏ dấu thừa
    clean_str = date_str.lower().replace('đăng ngày:', '').strip()
    
    # Xử lý các biến thể unicode của chữ "tháng" (nếu có)
    # Đơn giản nhất là xóa chữ "tháng" đi, chỉ giữ lại số ngày, tên tháng, năm
    clean_str = re.sub(r'th\w+ng', '', clean_str) # Xóa từ bắt đầu bằng th...ng
    
    # Bảng mã tháng (cập nhật thêm các biến thể)
    month_mapping = {
        'một': '01', 'giêng': '01', 'jan': '01',
        'hai': '02', 'feb': '02',
        'ba': '03', 'mar': '03',
        'tư': '04', 'bốn': '04', 'apr': '04',
        'năm': '05', 'may': '05',
        'sáu': '06', 'jun': '06',
        'bảy': '07', 'jul': '07',
        'tám': '08', 'aug': '08',
        'chín': '09', 'sep': '09',
        'mười một': '11', 'nov': '11', # Check tháng ghép trước
        'mười hai': '12', 'chạp': '12', 'dec': '12',
        'mười': '10', 'oct': '10', # Check tháng đơn sau
    }
    
    # Thay thế tên tháng bằng số
    for key, val in month_mapping.items():
        # Dùng regex để thay thế nguyên từ (word boundary) tránh nhầm lẫn
        if re.search(r'\b' + key + r'\b', clean_str):
            clean_str = re.sub(r'\b' + key + r'\b', val, clean_str)
            break
            
    try:
        # Lúc này chuỗi sẽ có dạng "03  02 2025" (nhiều khoảng trắng)
        # Dùng regex để lấy 3 cụm số: ngày, tháng, năm
        numbers = re.findall(r'\d+', clean_str)
        if len(numbers) >= 3:
            day, month, year = numbers[0], numbers[1], numbers[2]
            return datetime(int(year), int(month), int(day))
        return None
    except:
        return None

# --- 2. CẤU HÌNH SSL ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_gas_news(seen_ids):
    current_year = datetime.now().year
    new_items = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét GAS (Năm {current_year}) ---")

    # --- LINK 1: TIN CÔNG BỐ (pgrid/574) ---
    print("   >> [1/2] Quét Tin công bố (CBTT)...")
    # URL có chứa % mã hóa
    base_url_1 = "https://www.pvgas.com.vn/quan-he-co-%C4%91ong/pgrid/574/pageid/{}"
    
    for page in range(1, 2):
        url = base_url_1.format(page)
        try:
            response = session.get(url, headers=headers, timeout=20, verify=False)
            if len(response.text) < 500: break 

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Cập nhật Selector theo file gas_2.devtools
            # Tìm các khối tin trong class EDN_article
            articles = soup.select('.EDN_article')
            
            found_in_page = 0
            for art in articles:
                # 1. Ngày tháng: span.EDN_simpleDate
                date_tag = art.select_one('.EDN_simpleDate')
                if not date_tag: continue
                
                pub_date = parse_vietnamese_date(date_tag.get_text(strip=True))
                if not pub_date or pub_date.year != current_year: continue

                # 2. Link & Title: h3.simpleArticleTitle a
                title_tag = art.select_one('.simpleArticleTitle a')
                if not title_tag: continue
                
                title = title_tag.get('title') or title_tag.get_text(strip=True)
                link = title_tag.get('href')
                
                if not link: continue
                if not link.startswith('http'):
                    link = f"https://www.pvgas.com.vn{link}"

                # 3. Check trùng & Lưu
                if link in seen_ids: continue
                
                new_items.append({
                    "source": "GAS - CBTT",
                    "id": link,
                    "title": title,
                    "date": pub_date.strftime("%d/%m/%Y"),
                    "link": link
                })
                found_in_page += 1
            
            if found_in_page == 0: break

        except Exception as e:
            print(f"[GAS-P1] Lỗi: {e}")

    # --- LINK 2: TÀI LIỆU CỔ ĐÔNG (Chỉ lấy BCTC) ---
    print("   >> [2/2] Quét Tài liệu cổ đông (Chỉ lấy BCTC)...")
    url_2 = "https://www.pvgas.com.vn/quan-he-co-%C4%91ong/tai-lieu-co-%C4%91ong"
    
    try:
        response = session.get(url_2, headers=headers, timeout=20, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Quét rộng: Tìm tất cả thẻ article, tr, div
        all_elements = soup.find_all(['article', 'tr', 'div'])
        
        keywords = ["báo cáo tài chính", "bctc", "financial report"]
        
        for el in all_elements:
            # 1. Lọc theo Năm
            has_year = False
            # Tìm thẻ time hoặc tìm text năm trực tiếp
            if el.find('time'):
                d_str = el.find('time').get_text(strip=True)
                d = parse_vietnamese_date(d_str)
                if d and d.year == current_year: has_year = True
            elif str(current_year) in el.get_text():
                has_year = True
            
            if not has_year: continue

            # 2. Tìm Link
            a_tag = el.find('a', href=True)
            if not a_tag: continue
            
            link = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            # 3. Lọc từ khóa BCTC
            is_bctc = False
            for kw in keywords:
                if kw in title.lower():
                    is_bctc = True
                    break
            if not is_bctc: continue

            if not link.startswith('http'):
                link = f"https://www.pvgas.com.vn{link}"

            if link in seen_ids: continue
            if any(x['id'] == link for x in new_items): continue

            new_items.append({
                "source": "GAS - BCTC",
                "id": link,
                "title": title,
                "date": str(current_year),
                "link": link
            })

    except Exception as e:
        print(f"[GAS-P2] Lỗi: {e}")

    return new_items

import requests
import json
from datetime import datetime
import time
import urllib3
import ssl
import re # Cần regex để bóc tách link từ chuỗi HTML
from bs4 import BeautifulSoup # Dùng BS4 để xử lý đoạn HTML trong JSON cho an toàn
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_lpb_news(seen_ids):
    """
    Hàm cào LPBank (Đã fix theo file page.txt).
    - Đường dẫn JSON: data -> content.
    - Ngày tháng: ISO 8601 string.
    - Link: Parse từ trường HTML 'content'.
    """
    
    current_year = datetime.now().year
    
    categories = [
        "CONG_BO_THONG_TIN",
        "BAO_CAO.BAO_CAO_TAI_CHINH", 
        "DAI_HOI_CO_DONG"
    ]

    api_url = "https://lpbank.com.vn/api/content-service/public/findAllInvestor"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Referer": "https://lpbank.com.vn/"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét LPBank (Năm {current_year}) ---")

    for cat in categories:
        for page in range(1): 
            payload = {
                "title": None,
                "category": cat,
                "subCategory": None,
                "year": str(current_year),
                "otherYear": None,
                "page": page,
                "size": 20,
                "sortCustoms": [{"sortAsc": False, "nullsFirst": False, "sortField": "updatedDate"}]
            }

            try:
                response = session.post(api_url, headers=headers, json=payload, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[LPB] Lỗi kết nối {cat}: {response.status_code}")
                    break

                json_resp = response.json()
                
                # 1. Lấy list tin (data -> content)
                data_block = json_resp.get("data")
                if not data_block: break
                
                items = data_block.get("content", [])
                if not items:
                    if page == 0: pass
                    break

                count_in_page = 0
                for item in items:
                    title = item.get("title")
                    if not title: continue

                    # 2. Xử lý ngày tháng (ISO String)
                    # VD: '2025-12-03T09:52:27.225+00:00'
                    date_raw = item.get("startDate") or item.get("createdDate")
                    date_str = str(current_year)
                    
                    if date_raw:
                        try:
                            # Cắt chuỗi lấy phần YYYY-MM-DD (10 ký tự đầu)
                            # Cách này nhanh và an toàn hơn parse full ISO
                            date_part = date_raw[:10] 
                            pub_date = datetime.strptime(date_part, "%Y-%m-%d")
                            
                            if pub_date.year != current_year:
                                continue
                            
                            date_str = pub_date.strftime("%d/%m/%Y")
                        except:
                            pass

                    # 3. Lấy Link từ trường 'content' (HTML)
                    # Nội dung file.txt cho thấy link nằm trong thẻ <a href="..."> bên trong trường 'content'
                    html_content = item.get("content", "")
                    link = None
                    
                    if html_content:
                        # Dùng Regex hoặc BeautifulSoup để moi link ra
                        # Regex tìm href="..."
                        match = re.search(r'href="([^"]+)"', html_content)
                        if match:
                            link = match.group(1)
                        else:
                            # Nếu không có link trong content, thử dùng slug
                             slug = item.get("slug")
                             if slug: link = f"https://lpbank.com.vn/nha-dau-tu/{slug}"

                    if not link: continue

                    # 4. Check trùng & Lưu
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue

                    new_items.append({
                        "source": f"LPBank - {cat}",
                        "id": link,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_page += 1
                
                if count_in_page == 0: break
                time.sleep(0.5)

            except Exception as e:
                print(f"[LPB] Lỗi tại {cat}: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
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

def fetch_vnm_news(seen_ids):
    """
    Hàm cào Vinamilk (VNM) - Phiên bản Vét Cạn.
    - Link 1: Báo cáo tài chính (/financial)
    - Link 2: Báo cáo thường niên (/annual)
    - Link 3: ĐHĐCĐ (/amg) - Mới thêm
    """
    
    current_year = datetime.now().year
    
    # Danh sách URL cần quét (đã gắn param lọc năm)
    target_urls = [
        f"https://www.vinamilk.com.vn/investor/reports/financial?year={current_year}",
        f"https://www.vinamilk.com.vn/investor/reports/amg?year={current_year}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.vinamilk.com.vn/"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét Vinamilk (Năm {current_year}) ---")

    for url in target_urls:
        # Xác định tên nguồn dựa trên URL để dễ theo dõi
        source_type = "Khác"
        if "financial" in url: source_type = "BCTC"
        elif "amg" in url: source_type = "ĐHĐCĐ"

        try:
            # print(f"   >> Đang quét: {source_type}...")
            response = session.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                print(f"[VNM] Lỗi kết nối {source_type}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- CHIẾN THUẬT VÉT CẠN ---
            # Tìm tất cả thẻ <a>
            all_links = soup.find_all('a', href=True)
            
            count_in_page = 0
            for a_tag in all_links:
                link = a_tag.get('href')
                title = a_tag.get_text(strip=True) or a_tag.get('title')

                # 1. Lọc rác
                if not link or not title: continue
                if len(title) < 5: continue # Tiêu đề quá ngắn -> bỏ qua

                # 2. Chuẩn hóa Link
                if not link.startswith('http'):
                    link = f"https://www.vinamilk.com.vn{link}"

                # 3. Logic Lọc File Tài Liệu
                is_file = False
                lower_link = link.lower()
                
                # Case A: Đuôi file phổ biến
                if lower_link.endswith(('.pdf', '.doc', '.docx', '.zip', '.rar', '.xls', '.xlsx')):
                    is_file = True
                # Case B: Link chứa từ khóa download/uploads (đặc trưng Vinamilk)
                elif 'download' in lower_link or 'uploads' in lower_link:
                    is_file = True
                
                if not is_file: continue

                # 4. Check trùng
                news_id = link
                if news_id in seen_ids: continue
                if any(x['id'] == news_id for x in new_items): continue

                # Lưu kết quả
                new_items.append({
                    "source": f"Vinamilk - {source_type}",
                    "id": news_id,
                    "title": title,
                    "date": str(current_year), # Gán năm hiện tại vì URL đã lọc
                    "link": link
                })
                count_in_page += 1
            
            time.sleep(1)

        except Exception as e:
            print(f"[VNM] Lỗi xử lý {source_type}: {e}")
            continue

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
import re
import html
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CẤU HÌNH SSL FIX ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_vjc_news(seen_ids):
    """
    Hàm cào Vietjet Air (VJC).
    - Tự động giải mã HTML Entities (lỗi phông chữ).
    - Trích xuất ngày tháng từ tên file (20250417...).
    - Lọc năm hiện tại.
    """
    
    current_year = datetime.now().year
    
    # Danh sách danh mục
    categories = [
        "bao-cao-tai-chinh-quy",
        "bao-cao-tai-chinh-kiem-toan",
        "thong-tin-dinh-ky",
        "thong-tin-khac",
        "dai-hoi-dong-co-dong"
    ]
    
    base_url_template = "https://ir.vietjetair.com/Home/Menu/{}"
    domain = "https://ir.vietjetair.com"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- Bắt đầu quét VJC (Năm {current_year}) ---")

    for cat in categories:
        url = base_url_template.format(cat)
        
        try:
            # VJC thường load tất cả trong 1 trang, không phân trang rõ ràng ở URL
            # Nên ta chỉ cần request 1 lần cho mỗi danh mục
            response = session.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code != 200:
                print(f"[VJC] Lỗi kết nối {cat}: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tìm tất cả thẻ a có href
            all_links = soup.find_all('a', href=True)
            
            count_in_cat = 0
            for a_tag in all_links:
                raw_link = a_tag.get('href')
                # Giải mã tiêu đề (Fix lỗi font tiếng Việt)
                raw_title = a_tag.get_text(strip=True) or a_tag.get('title')
                title = html.unescape(raw_title) if raw_title else "Tài liệu không tiêu đề"

                # 1. Lọc rác & Chuẩn hóa Link
                if not raw_link or len(raw_link) < 5: continue
                
                if not raw_link.startswith('http'):
                    link = f"{domain}{raw_link}"
                else:
                    link = raw_link
                
                # 2. Logic Lọc File & Năm
                is_valid = False
                date_str = ""
                
                # Kiểm tra xem link có phải file tài liệu không
                lower_link = link.lower()
                if lower_link.endswith(('.pdf', '.doc', '.docx', '.zip', '.rar')):
                    
                    # --- TRÍCH XUẤT NGÀY TỪ LINK ---
                    # VJC hay đặt tên file kiểu: 20250417 - VJC...
                    # Regex tìm chuỗi 8 số liền nhau (YYYYMMDD)
                    date_match = re.search(r'(\d{4})(\d{2})(\d{2})', link)
                    
                    if date_match:
                        y, m, d = date_match.groups()
                        if int(y) == current_year:
                            is_valid = True
                            date_str = f"{d}/{m}/{y}"
                    
                    # Nếu không có ngày trong tên file, kiểm tra trong đường dẫn thư mục
                    # Ví dụ: .../nam 2025/...
                    elif str(current_year) in link:
                        is_valid = True
                        date_str = str(current_year)
                    
                    # Nếu không tìm thấy năm trong link, thử tìm trong tiêu đề
                    elif str(current_year) in title:
                        is_valid = True
                        date_str = str(current_year)

                if not is_valid: continue

                # 3. Check trùng
                news_id = link
                if news_id in seen_ids: continue
                if any(x['id'] == news_id for x in new_items): continue

                new_items.append({
                    "source": f"VJC - {cat}",
                    "id": news_id,
                    "title": title, # Tiêu đề đã được fix lỗi font
                    "date": date_str,
                    "link": link
                })
                count_in_cat += 1

            # print(f"   -> Tìm thấy {count_in_cat} tin tại {cat}")
            time.sleep(1)

        except Exception as e:
            print(f"[VJC] Lỗi tại {cat}: {e}")
            continue

    return new_items

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from datetime import datetime

def fetch_hdb_news(seen_ids):
    current_year = str(datetime.now().year)
    
    target_urls = [
        "https://hdbank.com.vn/vi/investor/thong-tin-nha-dau-tu/dai-hoi-dong-co-dong",
        "https://hdbank.com.vn/vi/investor/thong-tin-nha-dau-tu/quan-he-co-dong/cong-bo-thong-tin-thong-tin-khac",
        "https://hdbank.com.vn/vi/investor/thong-tin-nha-dau-tu/bao-cao-tai-chinh"
    ]

    new_items = []

    # --- TỐI ƯU CẤU HÌNH ---
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Block ảnh và CSS để tải siêu nhanh
    prefs = {
        "profile.managed_default_content_settings.images": 2, 
        "profile.managed_default_content_settings.stylesheets": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Quan trọng: Không chờ tải full trang, chỉ cần HTML về là chạy
    chrome_options.page_load_strategy = 'eager'

    print(f"--- 🚀 Quét HDBank (Turbo Mode) ---")
    
    # Khởi tạo driver 1 lần duy nhất
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(15) # Giới hạn max 15s/trang

    try:
        for url in target_urls:
            cat_name = url.split('/')[-1]
            try:
                driver.get(url)
                
                # --- BỎ QUA SCROLL LOOP ---
                # Vì dữ liệu ẩn đã có trong HTML, ta chỉ cần chờ nhẹ 1s để JS render cơ bản
                # Thay vì cuộn 3 lần mất 6s
                time.sleep(1.5) 
                
                # Lấy source ngay lập tức
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                # --- QUÉT LINK (Logic cũ vẫn ngon) ---
                all_links = soup.find_all('a', href=True)
                
                count_page = 0
                for a_tag in all_links:
                    link = a_tag.get('href')
                    title = a_tag.get_text(strip=True) or a_tag.get('title')

                    if not link or len(link) < 5: continue
                    
                    # Chuẩn hóa link
                    if not link.startswith('http'):
                        link = f"https://hdbank.com.vn{link}"

                    # 1. Lọc File/Chi tiết
                    lower_link = link.lower()
                    is_valid_type = lower_link.endswith(('.pdf', '.doc', '.docx', '.zip')) or '/chi-tiet/' in lower_link
                    if not is_valid_type: continue

                    # 2. Lọc Tiêu đề rác
                    if not title or len(title) < 10: 
                        # Thử lấy text từ cha (vì HDB hay để text ở thẻ p/div bao quanh a)
                        parent = a_tag.find_parent()
                        if parent: title = parent.get_text(strip=True)[:200]
                        else: continue

                    # 3. Lọc NĂM (2025) - Quét cả cha lẫn con
                    # Nếu tìm thấy "2025" ở bất cứ đâu xung quanh link -> Lấy
                    has_year = False
                    if current_year in title or current_year in link:
                        has_year = True
                    else:
                        # Check thẻ cha (div chứa link)
                        parent = a_tag.find_parent()
                        if parent and current_year in parent.get_text(): has_year = True
                        # Check ông nội (row chứa link)
                        elif parent and parent.parent and current_year in parent.parent.get_text(): has_year = True
                    
                    if not has_year: continue

                    # 4. Check trùng
                    if link in seen_ids: continue
                    if any(x['id'] == link for x in new_items): continue

                    new_items.append({
                        "source": f"HDBank - {cat_name}",
                        "id": link,
                        "title": title,
                        "date": current_year,
                        "link": link
                    })
                    count_page += 1
                
                # print(f"   > {cat_name}: {count_page} tin.")

            except Exception as e:
                print(f"[HDB] Lỗi load {cat_name}: {e}")
                continue

    finally:
        driver.quit()

    return new_items

import requests
import json
from datetime import datetime
import time
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_acb_news(seen_ids):
    """
    Hàm cào dữ liệu từ ACB.
    - Cấu trúc API đồng nhất.
    - Tự động ghép Params cho từng loại tin.
    """
    
    current_year = datetime.now().year
    
    # ID của Tag Năm (Bạn cung cấp là 1551 cho năm 2025)
    # Nếu sang năm 2026, cần cập nhật số này hoặc viết hàm tìm ID động
    YEAR_TAG_ID = 1551 
    
    # Cấu hình các danh mục cần quét
    config_categories = [
        # Nhóm 1: Lấy ý kiến CĐ (Gộp 3 ID)
        {"name": "Lấy ý kiến CĐ", "cat_ids": [1597, 1598, 1599], "use_year_tag": True},
        
        # Nhóm 2: Đại hội ĐCĐ (Gộp 3 ID)
        {"name": "Đại hội ĐCĐ", "cat_ids": [1365, 1366, 1380], "use_year_tag": True},
        
        # Nhóm 3: Công bố thông tin
        {"name": "CBTT", "cat_ids": [656], "use_year_tag": True},
        
        # Nhóm 4: Báo cáo tài chính (Không dùng tag năm theo link mẫu)
        {"name": "BCTC", "cat_ids": [1541], "use_year_tag": False} 
    ]

    base_api = "https://acb.com.vn/api/front/v1/posts"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://acb.com.vn/"
    }

    new_items = []
    session = requests.Session()
    # session.mount('https://', LegacySSLAdapter()) # ACB thường SSL chuẩn, nếu lỗi thì mở lại dòng này

    print(f"--- Bắt đầu quét ACB (Năm {current_year}) ---")

    for group in config_categories:
        # Duyệt qua từng Category ID trong nhóm
        for cat_id in group["cat_ids"]:
            # Tạo params cơ bản
            params = {
                "search[categories.category_id:in]": cat_id,
                "search[is_active:in]": 1,
                "page": 1,
                "limit": 10 # Lấy 10 tin mới nhất
            }
            
            # Thêm tag năm nếu cấu hình yêu cầu
            if group["use_year_tag"]:
                params["search[session_tags::tags:in]"] = YEAR_TAG_ID

            try:
                # print(f"   >> Đang tải: {group['name']} (ID {cat_id})...")
                response = session.get(base_api, headers=headers, params=params, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[ACB] Lỗi kết nối {group['name']}: {response.status_code}")
                    continue

                json_data = response.json()
                items = json_data.get("data", [])
                
                if not items: continue

                count_in_group = 0
                for item in items:
                    # 1. Lấy thông tin cơ bản
                    title = item.get("title")
                    if not title: continue

                    # 2. Xử lý ngày tháng (created_at: 2025-10-22T07:20:08...)
                    created_at = item.get("created_at")
                    date_str = str(current_year)
                    if created_at:
                        try:
                            # Cắt chuỗi lấy yyyy-mm-dd
                            dt_obj = datetime.strptime(created_at[:10], "%Y-%m-%d")
                            
                            # Nếu là BCTC (không lọc tag năm), ta lọc thủ công bằng code
                            if not group["use_year_tag"] and dt_obj.year != current_year:
                                continue
                                
                            date_str = dt_obj.strftime("%d/%m/%Y")
                        except:
                            pass

                    # 3. Lấy Link File (Ưu tiên featured_image -> path)
                    link = None
                    featured_img = item.get("featured_image")
                    if featured_img and isinstance(featured_img, dict):
                        link = featured_img.get("path")
                    
                    # Nếu không có file, lấy link bài viết (slug)
                    if not link:
                        slug = item.get("slug")
                        if slug: link = f"https://acb.com.vn/nha-dau-tu/{slug}"
                    
                    if not link: continue

                    # 4. Check trùng & Lưu
                    news_id = str(item.get("id")) # Dùng ID của bài viết làm key check trùng
                    
                    if news_id in seen_ids: continue
                    # Check trùng link (vì đôi khi 1 file được post lại)
                    if any(x['link'] == link for x in new_items): continue

                    new_items.append({
                        "source": f"ACB - {group['name']}",
                        "id": news_id, # Lưu ID bài viết vào DB
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_group += 1
                
                # print(f"      -> Tìm thấy {count_in_group} tin.")
                time.sleep(0.5)

            except Exception as e:
                print(f"[ACB] Lỗi xử lý {group['name']}: {e}")
                continue

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import html
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

# Tắt cảnh báo bảo mật (nhìn cho đỡ rối mắt)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL FIX (Phiên bản mạnh nhất) ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        # Cho phép kết nối server cũ (Legacy)
        ctx.options |= 0x4 
        # Tắt kiểm tra tên miền và chứng chỉ
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_mwg_news(seen_ids):
    """
    Hàm cào Thế Giới Di Động (MWG).
    - Đã fix lỗi SSL: UNSAFE_LEGACY_RENEGOTIATION_DISABLED.
    - Cấu trúc: HTML tĩnh (Server-Side Rendering).
    """
    
    current_year = datetime.now().year
    
    url = "https://mwg.vn/cong-bo-thong-tin"
    domain = "https://mwg.vn"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Tạo session và gắn Adapter fix lỗi
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét MWG (Năm {current_year}) ---")

    try:
        # verify=False để chắc chắn requests không check lại lần nữa
        response = session.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            print(f"[MWG] Lỗi kết nối: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm tất cả thẻ <a> có class là 'l-list__item'
        # (Dựa trên file mwg.txt bạn gửi)
        items = soup.find_all('a', class_='l-list__item')
        
        # print(f"   > Tìm thấy {len(items)} mục trên trang.")
        
        count_valid = 0
        
        for item in items:
            # 1. Lấy ngày tháng
            date_tag = item.find('p', class_='l-list-date')
            if not date_tag: continue
            
            date_str = date_tag.get_text(strip=True) # VD: "27/04/2025"
            
            try:
                pub_date = datetime.strptime(date_str, "%d/%m/%Y")
                if pub_date.year != current_year:
                    continue # Bỏ qua tin cũ
            except:
                continue # Lỗi ngày -> Bỏ qua

            # 2. Lấy Link
            link = item.get('href')
            if not link: continue
            
            # Chuẩn hóa link
            if not link.startswith('http'):
                link = f"{domain}{link}"

            # 3. Lấy Tiêu đề
            title_tag = item.find('p', class_='l-list-ttl')
            raw_title = title_tag.get_text(strip=True) if title_tag else ""
            
            # Giải mã ký tự lỗi (VD: &#x110; -> Đ)
            title = html.unescape(raw_title) 
            
            if not title: title = "Tài liệu MWG"

            # 4. Check trùng
            news_id = link
            if news_id in seen_ids: continue
            if any(x['id'] == news_id for x in new_items): continue

            new_items.append({
                "source": "MWG - CBTT",
                "id": news_id,
                "title": title,
                "date": date_str,
                "link": link
            })
            count_valid += 1

        # print(f"   > Lọc được {count_valid} tin của năm {current_year}.")

    except Exception as e:
        print(f"[MWG] Lỗi ngoại lệ: {e}")

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CẤU HÌNH SSL ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl_.create_urllib3_context()
        ctx.options |= 0x4 
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
        )

def fetch_msn_group_news(seen_ids):
    """
    Hàm cào Masan Group (MSN).
    - Cập nhật logic lấy Title từ span.text và thuộc tính download.
    """
    
    current_year = str(datetime.now().year)
    current_date_check = datetime.now().strftime("%d/%m/%Y")
    
    # Danh sách ID danh mục
    sections = [
        {"id": "12", "name": "Mục 12"},
        {"id": "102", "name": "Mục 102"},
        {"id": "103", "name": "Mục 103 (CBTT/ĐHĐCĐ)"},
        {"id": "104", "name": "Mục 104 (BCTC)"}
    ]

    base_url = "https://www.masangroup.com/vi/investor-relations.html/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    new_items = []
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét Masan Group (Năm {current_year}) ---")

    for section in sections:
        sec_id = section['id']
        
        for page in range(1, 2):
            params = {
                "CURRENT_PAGE": page,
                "NEWS_COUNT": 20,
                "TEMPLATE_PAGE": "investor-center/template-vertical",
                "IBLOCK_ID": "62",
                "PROPERTY_CODE[]": "file_vn",
                "PARENT_SECTION": sec_id,
                "year": current_year,
                "dateCheck": current_date_check
            }
            
            try:
                response = session.get(base_url, headers=headers, params=params, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[MSN Group] Lỗi ID {sec_id}: {response.status_code}")
                    break
                
                if len(response.text) < 100: break

                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.block-download')
                
                if not items: break

                count_in_page = 0
                for item in items:
                    # 1. Lấy Link (class="link-overlay")
                    link_tag = item.select_one('a.link-overlay')
                    if not link_tag: continue
                    link = link_tag.get('href')
                    if not link: continue

                    # 2. Lấy Ngày
                    date_tag = item.select_one('.date span')
                    date_str = date_tag.get_text(strip=True) if date_tag else str(current_year)

                    # 3. LẤY TIÊU ĐỀ (LOGIC MỚI)
                    title = "Tài liệu Masan"
                    
                    # Ưu tiên 1: Lấy từ span.text (như bạn chỉ)
                    text_span = item.select_one('span.text')
                    if text_span:
                        title = text_span.get_text(strip=True)
                    else:
                        # Ưu tiên 2: Lấy từ thuộc tính download của a.icon-download
                        download_a = item.select_one('a.icon-download')
                        if download_a and download_a.get('download'):
                            title = download_a.get('download')
                        else:
                            # Ưu tiên 3: Lấy từ .name span (fallback cũ)
                            name_span = item.select_one('.name span')
                            if name_span:
                                title = name_span.get_text(strip=True)

                    # 4. Check trùng & Lưu
                    news_id = link 
                    
                    if news_id in seen_ids: continue
                    if any(x['id'] == news_id for x in new_items): continue

                    new_items.append({
                        "source": f"Masan Group - {section['name']}",
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_page += 1
                
                if count_in_page == 0: break
                time.sleep(0.5)

            except Exception as e:
                print(f"[MSN Group] Lỗi ID {sec_id}: {e}")
                break

    return new_items

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib3
import ssl
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

def fetch_gvr_news(seen_ids):
    """
    Hàm cào GVR (Vietnam Rubber Group) - Phiên bản khớp HTML Elementor.
    URL gốc: https://vrg.vn/quan-he-co-dong/{category}/page/{page}/
    """
    
    current_year = datetime.now().year
    
    # Danh sách danh mục bạn yêu cầu
    categories = [
        "dai-hoi-dong-co-dong",
        "bao-cao-tai-chinh",
        "tin-co-dong"
    ]
    
    base_url_template = "https://vrg.vn/quan-he-co-dong/{}/page/{}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    new_items = []
    
    # Setup Session với SSL Fix
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét GVR (Năm {current_year}) ---")

    for cat in categories:
        # Quét 3 trang đầu mỗi danh mục (thường đủ phủ hết năm hiện tại)
        for page in range(1, 2):
            url = base_url_template.format(cat, page)
            
            try:
                # print(f"   >> Đang tải: {cat} - Trang {page}...")
                response = session.get(url, headers=headers, timeout=20, verify=False)
                
                if response.status_code != 200:
                    print(f"[GVR] Lỗi kết nối {cat}: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # --- PHÂN TÍCH HTML DỰA TRÊN ẢNH SCREENSHOT ---
                # Mỗi bài viết nằm trong 1 khối Loop Item
                # Class phổ biến của Elementor Loop là 'e-loop-item'
                items = soup.select('.e-loop-item')
                
                if not items:
                    # Fallback: Nếu không thấy class e-loop-item, thử tìm container chung
                    # Dựa vào ảnh: Tìm thẻ h3 chứa title trước
                    items = soup.select('.elementor-widget-theme-post-title')
                
                count_in_page = 0
                
                for item in items:
                    # Nếu item là h3 (trường hợp fallback), ta cần tìm cha của nó để kiếm ngày tháng
                    container = item
                    if 'e-loop-item' in item.get('class', []):
                        container = item
                    else:
                        # Leo lên tìm container chung chứa cả Title và Date
                        # Thường là 3-4 cấp div
                        container = item.find_parent(class_='e-loop-item') or item.find_parent(class_='elementor-column') or item.parent.parent
                    
                    if not container: continue

                    # 1. TÌM NGÀY THÁNG (Dựa trên ảnh: span.elementor-icon-list-text)
                    date_tag = container.select_one('.elementor-icon-list-text')
                    if not date_tag: continue
                    
                    date_str = date_tag.get_text(strip=True) # VD: 28/12/2025
                    
                    try:
                        pub_date = datetime.strptime(date_str, "%d/%m/%Y")
                        if pub_date.year != current_year:
                            continue # Bỏ qua tin năm cũ
                    except:
                        continue # Lỗi format ngày -> bỏ qua

                    # 2. TÌM LINK & TITLE (Dựa trên ảnh: h3.elementor-heading-title a)
                    # Lưu ý: Tìm bên trong container
                    title_tag = container.select_one('.elementor-heading-title a')
                    if not title_tag: continue
                    
                    link = title_tag.get('href')
                    title = title_tag.get_text(strip=True)
                    
                    if not link: continue
                    
                    # 3. CHUẨN HÓA LINK
                    if not link.startswith('http'):
                        link = f"https://vrg.vn{link}"
                        
                    # 4. CHECK TRÙNG
                    news_id = link
                    if news_id in seen_ids: continue
                    if any(x['id'] == news_id for x in new_items): continue

                    new_items.append({
                        "source": f"GVR - {cat}",
                        "id": news_id,
                        "title": title,
                        "date": date_str,
                        "link": link
                    })
                    count_in_page += 1
                
                # Nếu trang này không có tin nào của năm nay -> Dừng loop trang (vì các trang sau sẽ cũ hơn)
                if count_in_page == 0:
                    break
                
                time.sleep(0.5)

            except Exception as e:
                print(f"[GVR] Lỗi xử lý {cat}: {e}")
                break
                
    return new_items

import requests
import json
from datetime import datetime
import time
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import ssl_

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

def fetch_mbb_news(seen_ids):
    current_year = datetime.now().year
    base_domain = "https://www.mbbank.com.vn"
    new_items = []
    
    session = requests.Session()
    session.mount('https://', LegacySSLAdapter())

    print(f"--- 🚀 Bắt đầu quét MBB (Multi-Auth Mode - Năm {current_year}) ---")

    # --- BỘ CHÌA KHÓA 1: DÀNH CHO TÀI CHÍNH (ID 7 & 13) ---
    # Token lấy từ cURL GetListFinance bạn gửi (77Po...)
    finance_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "mb-xsrf-token-formonline": "77PoEGcVfl7NUNBq3RpRf3s0rEVZtKIhJQOF25nDRueqh6dSoEA1PLKcSTjHnoVXZSkOyIbZZHpM1zgZiX5-bdEw9ySBjnIZ71X6Fiulr1A1",
        "priority": "u=1, i",
        "referer": "https://www.mbbank.com.vn/Investor/bao-cao-tai-chinh/2025/0//0",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }
    
    finance_cookies = {
        "ASP.NET_SessionId": "oelkfrgme0kc4ngll30qlxfh",
        "LANG_CODE": "VI",
        "f5avraaaaaaaaaaaaaaaa_session_": "PBKDJABIPPFAKCIPDJFFBPDLBNHIPFEIDIPAKNDDMLBPGAFLFLILHOMCHBHLGIEPBDIDCGDGGOGPDBGHAHNAJGBAIMKAFIMDDBLPAGKBGBLMGOBBOCOFFAPMMGAFHHDG",
        "alias_current": "",
        "f5_cspm": "1234",
        "__RequestVerificationToken": "7th4Ag_M3Z9_M_M2PR1kXOJfk-nTFHCmvFKcjIUPZKaXy33YNutZcc3Y897A-E5MDdRl8v34Q25jAx65RcsYiHejhUurIiI3SxznMKm0f7E1"
    }

    # --- BỘ CHÌA KHÓA 2: DÀNH CHO CỔ ĐÔNG (SHAREHOLDERS) ---
    # Token lấy từ cURL GetShareholders bạn gửi (7uIx...)
    shareholder_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "mb-xsrf-token-formonline": "7uIxGtxA3E4Hg5coPOfIqwXF5YjdvY-YzGHqsKntXP6Yi8TUlXuMors-ugxxVzsHVLrCS6VBB4jM2uuxukLwg16kz3byTvU3VAuvDXMYaQk1",
        "priority": "u=1, i",
        "referer": "https://www.mbbank.com.vn/Investor/nha-dau-tu",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }
    
    shareholder_cookies = {
        "ASP.NET_SessionId": "oelkfrgme0kc4ngll30qlxfh",
        "LANG_CODE": "VI",
        "f5avraaaaaaaaaaaaaaaa_session_": "PBKDJABIPPFAKCIPDJFFBPDLBNHIPFEIDIPAKNDDMLBPGAFLFLILHOMCHBHLGIEPBDIDCGDGGOGPDBGHAHNAJGBAIMKAFIMDDBLPAGKBGBLMGOBBOCOFFAPMMGAFHHDG",
        "__RequestVerificationToken": "7th4Ag_M3Z9_M_M2PR1kXOJfk-nTFHCmvFKcjIUPZKaXy33YNutZcc3Y897A-E5MDdRl8v34Q25jAx65RcsYiHejhUurIiI3SxznMKm0f7E1",
        "alias_current": "nha-dau-tu",
        "f5avr0884827113aaaaaaaaaaaaaaaa_cspm_": "DCNGMIAFLHDFOEEHJAIJICHMEONJMELLIIFHCLPIDCCJHIDJHHOBKIKAMPCELCBAGIICNCHIBMIDJLNEJFEADLKPDJEJAHKJKILOEMFOEJLGGKGHIMPMFPKAJOKCADJP"
    }

    # Danh sách các request cần thực hiện, map với bộ chìa khóa tương ứng
    targets = [
        {
            "url": "https://www.mbbank.com.vn/api/GetListFinance/7/1/2025",
            "headers": finance_headers,
            "cookies": finance_cookies,
            "name": "BCTC (ID 7)"
        },
        {
            "url": "https://www.mbbank.com.vn/api/GetListFinance/13/1/2025",
            "headers": finance_headers, # ID 13 dùng chung chìa khóa Tài chính
            "cookies": finance_cookies,
            "name": "Báo cáo khác (ID 13)"
        },
        {
            "url": "https://www.mbbank.com.vn/api/GetShareholders_meeting",
            "headers": shareholder_headers, # Dùng chìa khóa Cổ đông riêng
            "cookies": shareholder_cookies,
            "name": "ĐHĐCĐ"
        }
    ]

    for target in targets:
        try:
            # print(f"   >> Đang gọi: {target['name']}...")
            response = session.get(
                target["url"], 
                headers=target["headers"], 
                cookies=target["cookies"], 
                timeout=15, 
                verify=False
            )
            
            if response.status_code != 200:
                print(f"[MBB] Lỗi HTTP {response.status_code} tại {target['name']}")
                continue

            try:
                json_data = response.json()
            except json.JSONDecodeError:
                print(f"[MBB] Không phải JSON tại {target['name']}")
                continue

            # --- PARSE DỮ LIỆU ---
            cat_info = json_data.get("data", {})
            cat_name = cat_info.get("title", target["name"])
            
            items = json_data.get("lst", [])
            if not items: continue

            count_in_cat = 0
            for item in items:
                title = item.get("title")
                file_path = item.get("file_path")
                last_save_date = item.get("last_Save_Date")
                
                if not title or not file_path: continue

                if not file_path.startswith("http"):
                    full_link = f"{base_domain}{file_path}"
                else:
                    full_link = file_path

                date_str = str(current_year)
                if last_save_date:
                    try:
                        dt_obj = datetime.strptime(last_save_date[:10], "%Y-%m-%d")
                        date_str = dt_obj.strftime("%d/%m/%Y")
                    except: pass
                
                # Check trùng
                news_id = str(item.get("id"))
                if not news_id or news_id == "None": news_id = full_link
                
                if news_id in seen_ids: continue
                if any(x['id'] == news_id for x in new_items): continue

                new_items.append({
                    "source": f"MBBank - {cat_name}",
                    "id": news_id,
                    "title": title,
                    "date": date_str,
                    "link": full_link
                })
                count_in_cat += 1
            
            time.sleep(0.5)

        except Exception as e:
            print(f"[MBB] Exception tại {target['name']}: {e}")
            continue

    return new_items

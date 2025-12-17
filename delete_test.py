import json
import os

# --- CẤU HÌNH ĐƯỜNG DẪN ---
# Tự động tìm file data_news.json nằm cùng thư mục với file code này
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data_news_3.json")

def main():
    # 1. Kiểm tra file tồn tại
    if not os.path.exists(DB_FILE):
        print(f"❌ Lỗi: Không tìm thấy file tại {DB_FILE}")
        print("   -> Bạn cần chạy bot chế độ 'Chỉ lưu' để tạo file trước.")
        return

    # 2. Đọc file JSON
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi đọc file JSON: {e}")
        return

    print(f"--- ✂️ BẮT ĐẦU CẮT TỈA DỮ LIỆU ĐỂ TEST ---")
    print(f"📂 File: {DB_FILE}\n")

    total_removed = 0

    # 3. Duyệt qua từng mã và xóa
    # Chúng ta dùng list(data.keys()) để tránh lỗi khi thay đổi dict trong lúc lặp (dù ở đây chỉ sửa value)
    for stock_code in list(data.keys()):
        news_list = data[stock_code]
        count_before = len(news_list)
        
        deleted_this_round = 0

        # Logic xóa:
        if count_before >= 2:
            # Xóa tin đầu (index 0) và tin cuối (index -1)
            # Cách an toàn: dùng slicing lấy phần ở giữa
            data[stock_code] = news_list[1:-1]
            deleted_this_round = 2
            
        elif count_before == 1:
            # Nếu chỉ có 1 tin thì xóa luôn cho sạch
            data[stock_code] = []
            deleted_this_round = 1
            
        else:
            # Nếu rỗng thì thôi
            deleted_this_round = 0

        count_after = len(data[stock_code])
        total_removed += deleted_this_round

        # 4. Print Log chi tiết
        print(f"📉 {stock_code:<5} : Trước {count_before:3} ➔ Sau {count_after:3} | 🗑️ Đã xóa: {deleted_this_round}")

    # 5. Lưu lại vào file
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ ĐÃ LƯU FILE THÀNH CÔNG!")
        print(f"   -> Tổng cộng đã xóa {total_removed} tin.")
        print("   -> Bây giờ hãy chạy 'python bot.py' (nhớ bật ENABLE_TELEGRAM=True) để thấy Bot gửi tin!")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")

if __name__ == "__main__":
    main()
# VN Stock ML Lab

Web app phân tích & dự báo cổ phiếu Việt Nam bằng học máy — chạy hoàn toàn trên máy tính cá nhân, không cần cloud, không cần trả phí.

> **Đây là công cụ nghiên cứu phương pháp, không phải khuyến nghị đầu tư.**

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Cài đặt](#cài-đặt)
4. [Khởi động](#khởi-động)
5. [Cách dùng dashboard](#cách-dùng-dashboard)
6. [Cách đọc kết quả](#cách-đọc-kết-quả)
7. [Kiến trúc kỹ thuật](#kiến-trúc-kỹ-thuật)
8. [Lộ trình](#lộ-trình)
9. [Câu hỏi thường gặp](#câu-hỏi-thường-gặp)

---

## Tính năng

- **Dữ liệu thật** từ VCI (qua vnstock) — hỗ trợ mọi mã HOSE/HNX
- **21 đặc trưng kỹ thuật** (momentum, MA, RSI, GARCH, P/E, P/B, giá nguyên liệu)
- **5 mô hình ML** thi đấu nhau: Ridge, ElasticNet, Random Forest, Gradient Boosting, Stacking Ensemble
- **Walk-forward backtest** — không dùng dữ liệu tương lai để tránh "rò rỉ thông tin"
- **Hai chế độ dự báo**: lợi suất (Return) hoặc biến động (Volatility)
- **Cache Parquet** — sau lần đầu, dữ liệu được lưu local, chạy lại gần như tức thì
- **Real-time progress** — xem từng bước phân tích qua SSE stream
- Tự động fallback sang **dữ liệu mô phỏng** nếu không có mạng/vnstock

---

## Yêu cầu hệ thống

| Mục | Yêu cầu |
|-----|---------|
| Hệ điều hành | macOS / Windows 10+ / Linux |
| Python | **3.10 trở lên** (khuyến nghị 3.11) |
| RAM | 2 GB trở lên |
| Ổ cứng | ~500 MB (bao gồm venv và cache) |
| Mạng | Cần cho lần tải dữ liệu đầu tiên |

### Kiểm tra Python đã cài chưa

Mở **Terminal** (macOS/Linux) hoặc **Command Prompt** (Windows), gõ:

```
python --version
```

hoặc:

```
python3 --version
```

Nếu hiện `Python 3.10.x` hoặc cao hơn → ổn. Nếu không có hoặc thấp hơn 3.10 → cài từ [python.org](https://www.python.org/downloads/).

> **Windows**: Khi cài Python, tick vào ô **"Add Python to PATH"** trước khi nhấn Install.

---

## Cài đặt

Chỉ cần làm **một lần duy nhất**.

### Bước 1 — Mở Terminal trong thư mục dự án

- **macOS**: Chuột phải vào thư mục `stockml` → "New Terminal at Folder"
- **Windows**: Giữ Shift, chuột phải vào thư mục `stockml` → "Open PowerShell window here"

### Bước 2 — Tạo môi trường ảo (virtual environment)

```bash
python3 -m venv venv
```

Lệnh này tạo thư mục `venv/` để cài các thư viện vào đó, không ảnh hưởng phần còn lại của máy.

### Bước 3 — Kích hoạt môi trường ảo

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

Sau khi kích hoạt, dấu nhắc lệnh sẽ có `(venv)` ở đầu — ví dụ: `(venv) user@mac stockml %`.

### Bước 4 — Cài thư viện

```bash
pip install -r requirements.txt
```

Quá trình này mất 2–5 phút tùy tốc độ mạng. Thư viện được cài bao gồm:
- `fastapi`, `uvicorn` — web server
- `scikit-learn` — các mô hình ML
- `pandas`, `numpy` — xử lý số liệu
- `arch` — mô hình GARCH
- `vnstock` — dữ liệu cổ phiếu VN
- `yfinance` — giá nguyên liệu quốc tế
- `pyarrow` — đọc/ghi cache Parquet

---

## Khởi động

### Cách nhanh (double-click)

- **macOS**: Double-click file `start.command` trong thư mục `stockml/`
- **Windows**: Double-click file `start.bat` trong thư mục `stockml/`

Launcher sẽ tự động làm tất cả: tạo môi trường ảo, cài thư viện, khởi động server, mở trình duyệt. Lần đầu mất 3–5 phút do cài thư viện — **đừng tắt cửa sổ Terminal trong lúc đó**.

> Trình duyệt mở tự động. Nếu không mở, vào thủ công: `http://localhost:8000`

---

### ⚠️ macOS: Cảnh báo bảo mật Gatekeeper (lần đầu chạy)

macOS chặn các file script tải từ internet. Lần đầu double-click `start.command` sẽ thấy thông báo **"start.command cannot be opened because it is from an unidentified developer"**.

**Cách mở lần đầu (chỉ cần làm 1 lần):**

**Cách A — Nhanh nhất:**
1. **Chuột phải** (hoặc Ctrl+Click) vào file `start.command`
2. Chọn **"Open"** trong menu xuất hiện
3. Trong hộp thoại cảnh báo, click **"Open"**
4. Từ lần sau có thể double-click bình thường

**Cách B — Qua System Settings:**
1. Double-click `start.command` → nhận cảnh báo → click "OK"
2. Mở **System Settings** (macOS 13+) hoặc **System Preferences** (macOS 12-)
3. Vào **Privacy & Security** → cuộn xuống cuối
4. Thấy dòng _"start.command was blocked"_ → click **"Open Anyway"**
5. Nhập mật khẩu máy nếu được hỏi

**Cách C — Terminal (1 lệnh):**
```bash
xattr -dr com.apple.quarantine ~/Desktop/hpg/files/stockml
```
Thay đường dẫn nếu bạn để thư mục `stockml` ở chỗ khác. Sau đó double-click bình thường.

### Cách thủ công (Terminal)

```bash
# Kích hoạt venv (nếu chưa kích hoạt)
source venv/bin/activate       # macOS/Linux
# hoặc venv\Scripts\activate  # Windows

# Vào thư mục backend và chạy server
cd backend
uvicorn main:app --reload
```

Rồi mở trình duyệt, vào `http://localhost:8000`.

### Dừng server

Nhấn **Ctrl+C** trong cửa sổ Terminal để tắt.

---

## Cách dùng dashboard

1. **Nhập mã cổ phiếu** — ví dụ: `HPG`, `FPT`, `VNM`, `VCB`, `MWG`
2. **Chọn khoảng thời gian** — mặc định 2020–2026 (6 năm)
3. **Chọn Horizon** — số phiên dự báo trước (1–20 phiên, mặc định 5)
4. **Chọn chế độ dự báo**:
   - `Return` — dự báo lợi suất (% tăng/giảm giá) trong h phiên tới
   - `Volatility` — dự báo biến động (độ bất ổn giá) trong h phiên tới
5. Nhấn **Phân tích** và theo dõi thanh tiến trình theo từng bước

### Thanh tiến trình realtime

| Bước | Ý nghĩa |
|------|---------|
| Tải dữ liệu | Lấy OHLCV từ VCI (hoặc cache nếu đã tải rồi) |
| Kiểm tra | Xác nhận số dòng, nguồn dữ liệu, thiếu dữ liệu |
| Yếu tố cơ bản | Tải P/E, P/B từ vnstock; giá sắt thép từ yfinance |
| Tạo đặc trưng | Tính 21 features kỹ thuật và cơ bản |
| Huấn luyện | Walk-forward trên 5 mô hình ML (9 folds mặc định) |

---

## Cách đọc kết quả

### Câu hỏi trung tâm: mô hình có đánh bại "random walk" không?

**Random walk** (đi ngẫu nhiên) là baseline đơn giản nhất: giả sử giá ngày mai = giá hôm nay. Nếu mô hình ML không thể đánh bại baseline này → mô hình không có giá trị dự báo thực tế.

### Các chỉ số

| Chỉ số | Ý nghĩa | Tốt khi nào |
|--------|---------|------------|
| **RMSE** | Sai số dự báo trung bình (càng nhỏ càng tốt) | Nhỏ hơn baseline (cột màu xanh) |
| **R²** | Mức giải thích phương sai | > 0 (càng dương càng tốt) |
| **Direction Acc** | Tỷ lệ đoán đúng chiều tăng/giảm | > 0.55 ổn định |

### Màu sắc

- Cột RMSE **xanh** = mô hình đánh bại baseline
- Cột RMSE **đỏ** = mô hình thua baseline
- Đường **vàng amber** = mức RMSE của baseline random walk

### Biểu đồ

- **Giá + dự báo**: đường giá thực tế và giá dự báo theo thời gian
- **Fold RMSE**: RMSE từng fold trong walk-forward — xem mô hình ổn định không
- **Scatter plot**: tương quan giữa giá trị dự báo và thực tế

### Lưu ý quan trọng

- R² < 0 = mô hình tệ hơn đoán giá trị trung bình — đừng dùng để giao dịch
- Direction Acc > 0.5 = hơn tung đồng xu, nhưng **phải > 0.55 ổn định** mới đáng chú ý
- Nếu mô hình đánh bại baseline → **kiểm tra rò rỉ thông tin** trước khi tin (đặc trưng dùng dữ liệu tương lai? target shift sai chiều?)

---

## Kiến trúc kỹ thuật

```
stockml/
├── backend/
│   ├── main.py                   # FastAPI: API endpoints + serve frontend
│   ├── providers.py              # DataProvider: vnstock (thật) | synthetic (mô phỏng)
│   ├── data_cache.py             # Cache Parquet TTL-1-ngày để tránh fetch lặp
│   ├── fundamental_providers.py  # P/E, P/B từ vnstock; giá sắt thép từ yfinance
│   ├── feature_engineering.py   # 21 đặc trưng: momentum, MA, RSI, GARCH, cơ bản
│   ├── financial_regression.py  # 5 mô hình ML + GARCHBaseline
│   ├── walk_forward.py          # Walk-forward backtest + baseline + directional acc
│   └── service.py               # Orchestrator: fetch→features→train→SSE stream
├── frontend/
│   └── index.html               # Dashboard SPA (Chart.js, SSE client)
├── cache/                        # Parquet cache tự động (gitignore)
├── requirements.txt
├── start.command                 # Launcher macOS
└── start.bat                     # Launcher Windows
```

### Nguyên tắc thiết kế

- **Chống rò rỉ thông tin (no look-ahead)**: mọi đặc trưng tại thời điểm t chỉ dùng dữ liệu ≤ t
- **Walk-forward thật sự**: không bao giờ retrain trên dữ liệu tương lai của từng fold
- **Tách tầng rõ ràng**: nguồn dữ liệu ⟂ phân tích ⟂ trình bày

### Thêm mô hình mới

Mở `backend/financial_regression.py`, thêm `ModelSpec(...)` vào danh sách `MODELS`. Không cần sửa file khác.

### Thêm nguồn dữ liệu mới

Mở `backend/providers.py`, tạo class kế thừa `DataProvider` với method `fetch()`. Đăng ký trong `get_provider()`.

---

## Lộ trình

- **Phase 2 (hoàn thành):** cache Parquet; GARCH features + volatility mode; yếu tố cơ bản P/E, P/B, giá nguyên liệu
- **Phase 3:** N8N lập lịch refresh + retrain hằng đêm; báo cáo qua Telegram

---

## Câu hỏi thường gặp

**Lần đầu chạy mất bao lâu?**
Khoảng 30–60 giây cho mã HPG (6 năm dữ liệu): tải dữ liệu ~5s, tạo features ~10s, huấn luyện 5 mô hình × 9 folds ~30–40s. Từ lần 2 trở đi, dữ liệu lấy từ cache → chỉ còn ~20–30s.

**Không thấy dữ liệu thật, chỉ thấy "synthetic"?**
Cần có `vnstock` cài đúng và mạng kết nối được tới VCI. Kiểm tra `http://localhost:8000/api/health` — nếu thấy `"data_source": "synthetic"` → cài lại vnstock hoặc kiểm tra tường lửa.

**Muốn dùng cổng khác (không phải 8000)?**
```bash
uvicorn main:app --reload --port 8001
```

**Cache ở đâu, xóa cache thế nào?**
Thư mục `stockml/cache/`. Xóa file `.parquet` của mã cụ thể hoặc xóa toàn bộ thư mục để force fetch lại.

**Lỗi `ModuleNotFoundError`?**
Bạn chưa kích hoạt venv. Chạy lại `source venv/bin/activate` (macOS/Linux) hoặc `venv\Scripts\activate` (Windows) trước khi khởi động server.

# VN Stock ML Lab

Web app phân tích & dự báo cổ phiếu Việt Nam bằng học máy có giám sát,
với phương pháp **walk-forward** trung thực và **baseline random-walk**.
Hỗ trợ **mọi mã chứng khoán**, không chỉ HPG.

## Kiến trúc

```
stockml/
├── backend/
│   ├── main.py                 # FastAPI: API + serve frontend (1 process)
│   ├── providers.py            # DataProvider (Strategy+Factory): vnstock | synthetic
│   ├── service.py              # điều phối: fetch → features → walk-forward → JSON
│   ├── feature_engineering.py  # 15 đặc trưng kỹ thuật, chống look-ahead
│   ├── walk_forward.py         # backtest walk-forward + baseline + directional acc
│   └── financial_regression.py # Ridge / ElasticNet / RF / GBR qua Pipeline
├── frontend/
│   └── index.html              # dashboard (Chart.js), aesthetic "quant lab"
└── requirements.txt
```

Tách tầng rõ ràng: nguồn dữ liệu ⟂ phân tích ⟂ trình bày. Thêm thuật toán
sửa `ModelFactory`; thêm nguồn dữ liệu thêm 1 lớp `DataProvider`.

## Chạy

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
# mở http://localhost:8000
```

- **Có `vnstock` + mạng tới sàn** → dùng dữ liệu THẬT (mọi mã HOSE/HNX).
- **Không có** → tự động dùng dữ liệu mô phỏng (hiệu chỉnh theo chế độ thị
  trường VN 2020-2026), gắn cờ `synthetic_fallback` để bạn không nhầm.

## Cách đọc dashboard

Câu hỏi trung tâm: **mô hình ML có đánh bại baseline "random walk" không?**
- Cột RMSE **xanh** = đánh bại baseline; **đỏ** = thua. Đường amber = baseline.
- Direction Accuracy: chỉ **>0.55 ổn định** mới đáng chú ý (>0.5 = hơn tung đồng xu).
- R² < 0 = tệ hơn đoán giá trị trung bình.
- Nếu một mô hình **đánh bại baseline**, KIỂM TRA LEAKAGE trước khi tin
  (đặc trưng dùng dữ liệu tương lai? target shift sai chiều?).

## Hiệu năng

Mỗi lần phân tích retrain mô hình qua nhiều cửa sổ thời gian → mất ~30-40s
cho ~6 năm dữ liệu. Web dùng preset cây nhẹ (`fast_default`) để phản hồi nhanh.
Phase 2: thêm cache (SQLite/Parquet) để không fetch & tính lại mỗi lần.

## Lộ trình

- **Phase 2:** cache dữ liệu; thêm target *biến động* (so với GARCH); thêm
  yếu tố cơ bản (P/E, P/B, giá nguyên liệu).
- **Phase 3:** N8N lập lịch refresh + retrain hằng đêm; báo cáo qua Telegram.

## Lưu ý

Đây là công cụ **nghiên cứu phương pháp**, không phải khuyến nghị đầu tư.

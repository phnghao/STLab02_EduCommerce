# STLab02 – EduCommerce Test Case Execution

Bài thực hành Software Testing: phân tích requirement → test condition → test scenario → test case → thực thi tự động bằng Python từ CSV → report CSV/Excel/HTML + dashboard Gradio.

- **Ứng dụng kiểm thử:** `ecommerce_app.py` (giữ nguyên mã nguồn từ STLab02 Instruction – không sửa bug trước khi test).
- **REQ đã chọn (không trùng REQ-06/08/11):** REQ-01, REQ-02, REQ-07, REQ-09, REQ-10, REQ-15, REQ-16 (7 REQ, 6 module).
- **Kết quả lần chạy tham chiếu:** 18 test cases – 16 PASS / 2 FAIL / 0 BLOCKED (pass rate 88.9%, REQ coverage 7/7).

---

## Cấu trúc thư mục

| File / Thư mục | Vai trò |
| :--- | :--- |
| `ecommerce_app.py` | Ứng dụng EduCommerce (Catalog, Cart, Promotions, Shipping, Inventory, Payments, Checkout) |
| `test_runner.py` | Runner đọc CSV, validate schema, fixture độc lập, dispatch lệnh, assert return + state, xuất report |
| `TestCases.csv` | 18 test cases data-driven (đầy đủ 15 cột bắt buộc theo mục 1.5) |
| `dashboard.py` | Dashboard Gradio: biểu đồ tỉ lệ cạnh bảng chi tiết, bộ lọc theo REQ/status |
| `STLab02_EduCommerce.ipynb` | Google Colab Notebook thực thi toàn bộ quy trình kiểm thử |
| `pyproject.toml` / `uv.lock` | Cấu hình quản lý môi trường và khóa phiên bản thư viện bằng `uv` |
| `reports/` | Thư mục báo cáo tự sinh: `test_execution.csv`, `test_report.xlsx` (3 sheets), `test_dashboard.html` |

---

## Chạy từ môi trường sạch (Local với `uv`)

```bash
# Clone repository
git clone git@github.com:phnghao/STLab02_EduCommerce.git && cd STLab02_EduCommerce

# Cài đặt môi trường và dependencies
uv sync

# Chạy kiểm thử tự động
uv run test_runner.py

# Khởi chạy Gradio Dashboard (mở http://127.0.0.1:7860)
uv run dashboard.py
```

*Chạy trên Google Colab:* Mở `STLab02_EduCommerce.ipynb` và chọn **Runtime → Run all**.

---

## Quy ước trạng thái

- **PASS:** Mọi khóa trong `expected_json` khớp chính xác giá trị quan sát (`return` + `state`: orders, charges, stock, used_codes).
- **FAIL:** Có khóa bị lệch hoặc ném ngoại lệ ngoài mong đợi từ ứng dụng.
- **BLOCKED:** Lỗi dữ liệu/setup (JSON hỏng, thiếu cột, fixture/action không tồn tại). Dòng BLOCKED vẫn được tính vào tổng số và kéo giảm pass rate.

*Nguyên tắc:* Expected được suy ra từ acceptance criteria, tuyệt đối không sửa theo actual.

---

## FAIL đã tìm thấy (Defects)

| Defect ID | TC ID | Tóm tắt lỗi phát hiện |
| :--- | :--- | :--- |
| **DEF-001** | `TC-SAF-001` | `Checkout.place()` gọi `inventory.reserve()` trước `payments.collect()`; method thanh toán lạ (`WALLET`) bị từ chối nhưng không `release` tồn kho → kho bị trừ dù không tạo đơn hàng. |
| **DEF-002** | `TC-SHP-002` | `Shipping.calculate()` dùng toán tử `>` thay vì `>=` ở mốc 500.000đ → đơn nội thành đúng 500.000đ bị tính phí 30.000đ thay vì miễn ship (0đ). |
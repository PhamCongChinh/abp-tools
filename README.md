# FastAPI với PostgreSQL - Truy vấn trực tiếp

Project FastAPI đơn giản để kết nối và truy vấn PostgreSQL trực tiếp.

## Yêu cầu

- Python 3.8+
- PostgreSQL

## Cài đặt

### Cách 1: Sử dụng script tự động (Khuyến nghị)

**Windows CMD:**
```bash
# Cài đặt
setup.bat

# Chạy ứng dụng
run.bat
```

**Windows PowerShell:**
```powershell
# Cài đặt
.\setup.ps1

# Chạy ứng dụng
.\run.ps1
```

**Linux/Mac:**
```bash
# Cài đặt
chmod +x setup.sh run.sh
./setup.sh

# Chạy ứng dụng
./run.sh
```

### Cách 2: Cài đặt thủ công

#### 1. Tạo môi trường ảo

```bash
# Windows
python -m venv .env
.env\Scripts\activate

# Linux/Mac
python3 -m venv .env
source .env/bin/activate
```

#### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

#### 3. Cấu hình Database

Chỉnh sửa file `.env` với thông tin PostgreSQL của bạn:

```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
APP_NAME=FastAPI Application
DEBUG=True
```

#### 4. Chạy ứng dụng

```bash
python main.py
```

hoặc

```bash
uvicorn main:app --reload
```

Ứng dụng sẽ chạy tại: http://localhost:8000

## API Documentation

Sau khi chạy ứng dụng, truy cập:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Trang chủ
- `GET /health` - Kiểm tra health và kết nối database
- `GET /query?sql=SELECT...` - Thực thi câu truy vấn SELECT
- `POST /execute` - Thực thi câu lệnh SQL (INSERT, UPDATE, DELETE, CREATE, etc.)
- `GET /tables` - Liệt kê tất cả các bảng trong database
- `GET /table/{table_name}` - Xem cấu trúc của một bảng

## Cấu trúc Project

```
.
├── .env                 # File cấu hình môi trường (không commit)
├── .env.example         # File mẫu cấu hình
├── .gitignore          # Git ignore file
├── config.py           # Cấu hình ứng dụng
├── database.py         # Cấu hình database connection
├── main.py             # File chính của ứng dụng
├── requirements.txt    # Python dependencies
└── README.md          # File này
```

## Ví dụ sử dụng

### Kiểm tra kết nối

```bash
curl "http://localhost:8000/health"
```

### Liệt kê các bảng

```bash
curl "http://localhost:8000/tables"
```

### Xem cấu trúc bảng

```bash
curl "http://localhost:8000/table/users"
```

### Truy vấn SELECT

```bash
curl "http://localhost:8000/query?sql=SELECT%20*%20FROM%20users%20LIMIT%2010"
```

### Thực thi INSERT/UPDATE/DELETE

```bash
curl -X POST "http://localhost:8000/execute?sql=INSERT%20INTO%20users%20(name)%20VALUES%20('John')"
```

## Lưu ý bảo mật

- Endpoint `/query` chỉ cho phép câu lệnh SELECT để đảm bảo an toàn
- Endpoint `/execute` cho phép tất cả các câu lệnh SQL - cần cẩn thận khi sử dụng
- Trong môi trường production, nên thêm authentication và authorization

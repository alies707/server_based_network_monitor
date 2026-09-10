# مانیتورینگ شبکه مبتنی بر سرور

سیستم مانیتورینگ شبکه Client/Server با **Python** برای مشاهده زنده مصرف اینترنت کلاینت‌ها.

## قابلیت‌ها

- نمایش زنده سرعت دانلود هر Client
- نمایش زنده سرعت آپلود هر Client
- نمایش Public IP مشاهده‌شده توسط Server
- نمایش مصرف کل دانلود، آپلود و مجموع ترافیک هر Client
- تشخیص Online / Offline
- داشبورد وب فارسی و راست‌چین
- ارتباط زنده با WebSocket
- ذخیره مصرف تجمعی در SQLite
- اتصال مجدد خودکار Client پس از قطع ارتباط
- ساخت Client ID پایدار بدون نیاز به تعریف دستی
- پشتیبانی Client از Windows، Linux و macOS
- اعتبارسنجی ورودی‌ها و Counterها
- طراحی Monitoring-only بدون اجرای فرمان روی سیستم Client
- تست خودکار و GitHub Actions

## معماری

```text
┌─────────────────────┐
│    Python Client    │
│                     │
│  Network Counters   │
│      RX / TX        │
└──────────┬──────────┘
           │ WebSocket
           ▼
┌─────────────────────┐
│   Python FastAPI    │
│       Server        │
│                     │
│ Live Rate           │
│ Public IP           │
│ Client Status       │
│ Persistence         │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  SQLite     Dashboard
```

Client فقط Counterهای تجمعی RX/TX را ارسال می‌کند. Server بر اساس اختلاف Counterها سرعت لحظه‌ای را محاسبه کرده و مصرف تجمعی را در SQLite نگهداری می‌کند.

## پیش‌نیازها

- Python 3.11 یا بالاتر
- شبکه‌ای که Client بتواند به Server دسترسی داشته باشد
- برای استفاده Production، TLS/WSS توصیه می‌شود

## نصب و اجرای Server

### Linux / macOS

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Windows PowerShell

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="."
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

سپس داشبورد را باز کنید:

```text
http://SERVER_IP:8000/
```

مثال:

```text
http://192.168.1.100:8000/
```

## نصب و اجرای Client

### Linux / macOS

```bash
cd client
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --server ws://192.168.1.100:8000/ws/client
```

### Windows PowerShell

```powershell
cd client
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main --server ws://192.168.1.100:8000/ws/client
```

`192.168.1.100` را با IP واقعی Server جایگزین کنید.

## احراز هویت

در Server:

```text
NETWORK_MONITOR_TOKEN=یک-توکن-قوی
```

در Client:

```bash
python -m app.main --server ws://192.168.1.100:8000/ws/client --token یک-توکن-قوی
```

اگر Token در Server تنظیم نشده باشد، احراز هویت برای محیط توسعه غیرفعال است.

## تنظیمات Client

```text
--server SERVER_URL
--client-id CLIENT_ID
--token TOKEN
--interval SECONDS
--reconnect-delay SECONDS
--log-level LEVEL
```

همچنین Environment Variableهای زیر پشتیبانی می‌شوند:

```text
NETWORK_MONITOR_SERVER
NETWORK_MONITOR_CLIENT_ID
NETWORK_MONITOR_TOKEN
NETWORK_MONITOR_INTERVAL
NETWORK_MONITOR_RECONNECT_DELAY
NETWORK_MONITOR_LOG_LEVEL
NETWORK_MONITOR_IDENTITY_FILE
```

اگر Client ID تعیین نشود، Client یک شناسه پایدار ایجاد می‌کند و آن را در فایل Identity نگهداری می‌کند.

## تست سریع

1. Server را روی سیستم Server اجرا کنید.
2. از سیستم Client آدرس `http://SERVER_IP:8000/` را باز کنید.
3. Client Python را اجرا کنید.
4. Client باید در داشبورد Online شود.
5. روی Client یک فایل دانلود کنید و افزایش Download را در داشبورد ببینید.
6. یک فایل آپلود کنید و افزایش Upload را بررسی کنید.
7. Client را ببندید و Offline شدن آن را بررسی کنید.
8. Client را دوباره اجرا کنید و باقی ماندن Total Traffic را بررسی کنید.

## Counter Reset

Counter شبکه سیستم ممکن است بعد از Restart سیستم یا Reset شدن Driver کاهش پیدا کند. اگر Counter جدید از Counter قبلی کمتر باشد، Server آن را Reset تشخیص داده و Counter جدید را به مصرف تجمعی اضافه می‌کند تا مصرف منفی ایجاد نشود.

## Public IP

Server IP منبع اتصال WebSocket را به‌عنوان IP مشاهده‌شده Client ثبت می‌کند. اگر Server پشت Reverse Proxy باشد، باید تنظیمات Trusted Proxy به‌درستی انجام شود؛ در غیر این صورت ممکن است IP Proxy ثبت شود.

## اجرای تست‌ها

تست Server:

```bash
PYTHONPATH=server python -m pytest -q server/tests
```

تست Client:

```bash
python -m pytest -q client/tests
```

بررسی Syntax:

```bash
python -m compileall -q client/app server/app
```

GitHub Actions تست‌های Server و Client را اجرا می‌کند و Client روی Python 3.11، 3.12 و 3.13 بررسی می‌شود.

## ساختار پروژه

```text
server_based_network_monitor/
├── client/
│   ├── app/
│   │   ├── config.py
│   │   ├── identity.py
│   │   ├── main.py
│   │   ├── network.py
│   │   └── websocket_client.py
│   ├── tests/
│   ├── requirements.txt
│   └── config.example.json
├── server/
│   ├── app/
│   ├── tests/
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
└── README.fa.md
```

## وضعیت امنیتی

این پروژه در وضعیت فعلی برای Monitoring طراحی شده است و هیچ قابلیت اجرای Remote Command یا تغییر تنظیمات سیستم Client ندارد.

برای Production:

- از `wss://` استفاده کنید.
- Token قوی تنظیم کنید.
- Server را مستقیماً بدون Firewall در اینترنت قرار ندهید.
- Reverse Proxy و Trusted Proxy را به‌درستی تنظیم کنید.
- برای تعداد زیاد Clientها، معماری ذخیره‌سازی و Broadcast باید برای Scale بهینه شود.

## مجوز

این Repository در حال توسعه است. قبل از استفاده تجاری، License مناسب پروژه را تعیین کنید.

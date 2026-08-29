# ⚡ ZenTask — Premium & Secure Task Management Web Application

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Vercel](https://img.shields.io/badge/Vercel-Deployed-black.svg?logo=vercel&logoColor=white)](https://vercel.com)
[![Render](https://img.shields.io/badge/Render-Ready-46E3B7.svg?logo=render&logoColor=white)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**ZenTask** is a modern, glassmorphic productivity and task management web application built with **Python (Flask)**, **SQLAlchemy**, and Vanilla CSS & JavaScript. It combines interactive task tracking, calendar planning, visual productivity analytics, and an AI assistant widget with enterprise-grade security.

---

## 🌟 Key Features

### 📋 1. Interactive Board View
- **Drag-and-Drop Reordering**: Smooth HTML5 drag-and-drop task positioning.
- **Categorization & Priorities**: Organize tasks by category (*Personal, Work, Shopping, Fitness, Urgent, Coding*) and priority levels (*Low, Medium, High*).
- **Search & Live Filtering**: Instant title/description search with category chips and priority dropdown filters.
- **Due Date Tracking**: Real-time overdue indicators and completion progress stats.

### 📅 2. Calendar View
- Interactive month-by-month calendar grid.
- Daily task dots and preview pills showing scheduled tasks at a glance.
- One-click date inspection.

### 📊 3. Visual Analytics & Insights
- **14-Day Productivity Graph**: Interactive line chart powered by Chart.js.
- **Priority & Category Distribution**: Real-time doughnut and bar chart breakdowns.
- Instant calculation of completion percentage and pending workload.

### 🤖 4. ZenBot AI Assistant Widget
- Lightweight built-in productivity chatbot.
- Smart suggestions on high-priority items and task status summaries.

### 🔐 5. Secure Authentication & Password Recovery
- Secure registration and login with password hashing via `Werkzeug`.
- **Forgot Password Flow**: Time-limited cryptographic password reset links generated via `itsdangerous` with 1-hour expiration.
- Password visibility reveal toggles (`eye` icons) on all auth forms.

### 📎 6. Attachments & Document Exports
- **File Attachments**: Upload supporting files (up to 16MB) directly to individual tasks.
- **Exporting**: One-click export of your full task board to **PDF** (via ReportLab) and **CSV**.

### 📱 7. Full Multi-Device Responsiveness
- **Desktop, Tablet, and Mobile**: Optimized with responsive CSS tokens, accessible 44px touch targets, and mobile bottom navigation bar.
- **Dark & Light Mode**: Instant theme switching with preference persistence in `localStorage`.

---

## 🛡️ Security Architecture

ZenTask follows defensive security best practices:

| Security Domain | Protection Measure |
|---|---|
| **CSRF Defense** | Cryptographic session-bound CSRF token validation on all mutating requests (`POST`, `PUT`, `DELETE`) and forms. |
| **Security Headers** | Enforced `Content-Security-Policy`, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, and `Referrer-Policy`. |
| **File Upload Safety** | 16MB file limit (`MAX_CONTENT_LENGTH`), strict extension allowlist (`png`, `jpg`, `pdf`, `txt`, `csv`, `docx`, `xlsx`, `zip`), randomized UUID storage, and directory traversal checks on download. |
| **Input Validation** | Strict regex validation on usernames, emails, and passwords; bounds-checking on title and description lengths. |
| **Rate Limiting** | In-memory sliding window rate limiting on authentication routes (`/login`, `/signup`, `/forgot-password`) to stop brute-force attacks. |
| **Session Hardening** | `HttpOnly`, `SameSite=Lax`, and dynamic HTTPS `Secure` cookie flags. |
| **Error Handling** | Custom error pages (`400`, `401`, `403`, `404`, `413`, `500`) that prevent stack trace leakage. |

---

## 🚀 Getting Started Locally

### Prerequisites
- Python 3.10 or higher
- pip & virtualenv

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Abhijeet0848/To-do-task-.git
   cd To-do-task-
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Linux / macOS:
   python3 -m venv venv
   source venv/bin/activate

   # Windows:
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

5. **Start the local server**:
   ```bash
   python wsgi.py
   # or
   python app.py
   ```
   Open your browser at **`http://127.0.0.1:5000`**.

---

## ☁️ Deployment

### 1. Deploying to **Vercel**
This project includes pre-configured `vercel.json` and serverless path handling.

1. Push your changes to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New Project**.
3. Import `Abhijeet0848/To-do-task-`.
4. Under **Environment Variables**, set:
   - `SECRET_KEY`: `<your-random-32-char-string>`
   - `FLASK_ENV`: `production`
   - `FLASK_DEBUG`: `false`
   - `DATABASE_URL` *(optional for remote DB)*: `postgresql://...` (e.g. from Neon / Supabase)
5. Click **Deploy**.

### 2. Deploying to **Render**
This repository includes a `Procfile` and `gunicorn.conf.py`.

1. Go to [Render Dashboard](https://render.com/) and select **New Web Service**.
2. Connect `Abhijeet0848/To-do-task-`.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn -c gunicorn.conf.py wsgi:application`
5. Set environment variable `SECRET_KEY` and click **Deploy**.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | Auto-generated | Secret key used for sessions and CSRF tokens |
| `FLASK_ENV` | `production` | Environment mode (`development` / `production`) |
| `FLASK_DEBUG` | `false` | Enable/disable Flask debug mode |
| `DATABASE_URL` | `sqlite:///todo.db` | Database connection string (SQLite, PostgreSQL, etc.) |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` in production when serving over HTTPS |
| `PORT` | `5000` | Port for the web server to listen on |

---

## 📡 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/tasks` | `GET` | Retrieve filtered tasks for authenticated user |
| `/api/tasks` | `POST` | Create a new task |
| `/api/tasks/<id>` | `PUT` | Update an existing task |
| `/api/tasks/<id>` | `DELETE` | Delete a task and its attachments |
| `/api/tasks/<id>/toggle` | `POST` | Toggle completion status |
| `/api/tasks/reorder` | `POST` | Update drag-and-drop positions |
| `/api/tasks/<id>/attachments` | `POST` | Upload file attachment to task |
| `/api/tasks/attachments/<id>/download` | `GET` | Download attachment file |
| `/api/tasks/export/csv` | `GET` | Download task board in CSV format |
| `/api/tasks/export/pdf` | `GET` | Generate and download PDF report |
| `/api/stats` | `GET` | Fetch completion metrics and productivity graph data |
| `/api/notifications` | `GET` | Fetch user notifications |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

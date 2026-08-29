# ZenTask — Premium & Secure Task Management Web Application

ZenTask is a modern, glassmorphic task management application built with **Python (Flask)**, **SQLAlchemy**, and Vanilla CSS & JavaScript. It features real-time task analytics, calendar visualization, multi-screen responsive design, and robust security protections.

---

## Features

- **Intuitive Board View**: Drag-and-drop task reordering, dynamic categories, priorities, due date tracking, and progress metrics.
- **Calendar Visualization**: Interactive month-by-month calendar view with daily task tracking.
- **Visual Analytics**: Interactive 14-day productivity graph and task distribution charts powered by Chart.js.
- **Built-in AI Assistant (ZenBot)**: Lightweight productivity assistant widget.
- **File Attachments**: Secure file attachment support (up to 16MB) with path traversal safeguards.
- **Exporting Options**: One-click export of tasks to PDF and CSV formats.
- **Customizable Themes**: Seamless toggle between dark and light themes with preference persistence.
- **Multi-Device Responsive Design**: Tailored layouts for Desktop, Tablet, and Mobile devices (including a dedicated mobile bottom navigation bar).

---

## Security Hardening

- **CSRF Protection**: Token-based validation on all state-mutating requests (`POST`, `PUT`, `DELETE`).
- **Security Headers**: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection`, and `Referrer-Policy`.
- **File Upload Restrictions**: Strict allowlist of extensions (`png`, `jpg`, `pdf`, `txt`, `csv`, `docx`, `xlsx`, `zip`) with randomized UUID storage.
- **Input Validation**: Strict regex and length validation on authentication inputs and task fields.
- **Session Hardening**: `HttpOnly`, `SameSite=Lax`, and configurable secure cookies for HTTPS.
- **Brute-Force Rate Limiting**: In-memory rate limiting on login and registration endpoints.

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Abhijeet0848/To-do-task-.git
   cd To-do-task-
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows:
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

5. **Run the application**:
   ```bash
   python wsgi.py
   # or
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5000`.

---

## Production Deployment

ZenTask is deployment-ready with **Gunicorn** and **WSGI**:

```bash
gunicorn -c gunicorn.conf.py wsgi:application
```

---

## License

This project is open source and available under the MIT License.

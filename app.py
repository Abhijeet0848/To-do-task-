from datetime import datetime, date, timedelta
import os
import re
import sqlite3
import csv
import io
import threading
import time
import secrets
import hmac
import uuid
import smtplib
from collections import defaultdict
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, g, flash, abort

# Load environment variables from .env file if available
load_dotenv()

app = Flask(__name__)

# Security & App Configuration
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

# Session Cookie Hardening
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# File Upload Security Settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'csv', 'docx', 'xlsx', 'zip', 'json', 'md'}

# Database Configuration
db_path = os.path.join(BASE_DIR, 'todo.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# ==============================================================================
# Security Utilities: CSRF, Rate Limiting & Allowed Enums
# ==============================================================================

ALLOWED_CATEGORIES = {'personal', 'work', 'shopping', 'fitness', 'urgent', 'coding'}
ALLOWED_PRIORITIES = {'low', 'medium', 'high'}
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')

# In-memory rate limiting tracker (per IP)
rate_limit_tracker = defaultdict(list)
RATE_LIMIT_MAX_ATTEMPTS = 15
RATE_LIMIT_WINDOW_SECONDS = 60

def is_rate_limited(client_ip):
    now = time.time()
    attempts = [t for t in rate_limit_tracker[client_ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
    attempts.append(now)
    rate_limit_tracker[client_ip] = attempts
    return len(attempts) > RATE_LIMIT_MAX_ATTEMPTS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

# CSRF Verification Middleware
@app.before_request
def csrf_protect():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        # Allow bypassing CSRF check for testing if explicit test mode enabled
        if app.config.get('TESTING'):
            return
        
        token = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        expected = session.get('_csrf_token')
        
        if not expected or not token or not hmac.compare_digest(str(expected), str(token)):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Invalid or expired CSRF token. Please refresh the page.'}), 403
            flash('Security token expired or invalid. Please try again.', 'danger')
            return redirect(request.referrer or url_for('login'))

# Security Headers Middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    
    # CSP permitting necessary fonts, cdnjs, and chart.js
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    return response

# ==============================================================================
# Dynamic Database Migrations / Schema Sync
# ==============================================================================
def upgrade_db():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check task table columns
        cursor.execute("PRAGMA table_info(task)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'position' not in columns:
            cursor.execute("ALTER TABLE task ADD COLUMN position INTEGER DEFAULT 0")
        if 'completed_at' not in columns:
            cursor.execute("ALTER TABLE task ADD COLUMN completed_at TIMESTAMP")
        if 'reminder_sent' not in columns:
            cursor.execute("ALTER TABLE task ADD COLUMN reminder_sent BOOLEAN DEFAULT 0")
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE task ADD COLUMN user_id INTEGER REFERENCES user(id)")
            
        # Check notification table columns
        cursor.execute("PRAGMA table_info(notification)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE notification ADD COLUMN user_id INTEGER REFERENCES user(id)")
            
        # Check system_settings table columns
        cursor.execute("PRAGMA table_info(system_settings)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE system_settings ADD COLUMN user_id INTEGER REFERENCES user(id)")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database upgrade notice: {e}")

# ==============================================================================
# Database Models
# ==============================================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    tasks = db.relationship('Task', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    settings = db.relationship('SystemSettings', backref='user', uselist=False, cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='medium')
    category = db.Column(db.String(50), default='personal')
    due_date = db.Column(db.Date, nullable=True, index=True)
    is_completed = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    position = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, nullable=True)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    attachments = db.relationship('TaskAttachment', backref='task', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description or '',
            'priority': self.priority,
            'category': self.category,
            'due_date': self.due_date.isoformat() if self.due_date else '',
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat(),
            'position': self.position,
            'completed_at': self.completed_at.isoformat() if self.completed_at else '',
            'reminder_sent': self.reminder_sent,
            'attachments': [a.to_dict() for a in self.attachments]
        }

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    user_email = db.Column(db.String(120), nullable=True)
    email_reminders_enabled = db.Column(db.Boolean, default=False)
    smtp_server = db.Column(db.String(120), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(120), nullable=True)
    smtp_password = db.Column(db.String(256), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user_email or '',
            'email_reminders_enabled': self.email_reminders_enabled,
            'smtp_server': self.smtp_server or '',
            'smtp_port': self.smtp_port or 587,
            'smtp_user': self.smtp_user or ''
        }

class TaskAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(510), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }

# ==============================================================================
# Background Scheduler & Email Dispatcher
# ==============================================================================
def run_email_scheduler(app_instance):
    with app_instance.app_context():
        while True:
            try:
                settings_list = SystemSettings.query.all()
                for settings in settings_list:
                    if settings and settings.email_reminders_enabled and settings.user_email and settings.user_id:
                        today = date.today()
                        due_tasks = Task.query.filter(
                            Task.user_id == settings.user_id,
                            Task.is_completed == False,
                            Task.due_date == today,
                            Task.reminder_sent == False
                        ).all()
                        
                        if due_tasks:
                            for task in due_tasks:
                                send_task_email(settings, task)
                                notif = Notification(
                                    user_id=settings.user_id,
                                    message=f"Email reminder sent for task: '{task.title}'",
                                    type='success'
                                )
                                db.session.add(notif)
                                task.reminder_sent = True
                            db.session.commit()
            except Exception as e:
                print(f"Scheduler notice: {e}")
            time.sleep(60)

def send_task_email(settings, task):
    log_path = os.path.join(BASE_DIR, 'sent_emails.log')
    email_content = f"""Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
To: {settings.user_email}
Subject: ZenTask Reminder - '{task.title}' is due today!
--------------------------------------------------
Hi there,

This is a reminder that your task is due today:
Task: {task.title}
Category: {task.category.capitalize()}
Priority: {task.priority.capitalize()}
Description: {task.description or 'No description provided.'}

Stay productive!
ZenTask System
--------------------------------------------------
"""
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(email_content + "\n\n")
    except Exception as e:
        print(f"Failed to write mock email log: {e}")

    if settings.smtp_server and settings.smtp_user and settings.smtp_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_user
            msg['To'] = settings.user_email
            msg['Subject'] = f"ZenTask Reminder: '{task.title}'"
            body = f"Hi, just a reminder that your task '{task.title}' (Priority: {task.priority.upper()}) is due today!"
            msg.attach(MIMEText(body, 'plain'))
            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=10)
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.user_email, msg.as_string())
            server.quit()
        except Exception as smtp_err:
            print(f"SMTP error fallback: {smtp_err}")

# ==============================================================================
# Helper Functions
# ==============================================================================
def get_task_stats(user_id):
    total = Task.query.filter_by(user_id=user_id).count()
    completed = Task.query.filter_by(user_id=user_id, is_completed=True).count()
    pending = total - completed
    completion_rate = round((completed / total) * 100) if total > 0 else 0
    
    categories = db.session.query(Task.category, db.func.count(Task.id)).filter_by(user_id=user_id).group_by(Task.category).all()
    category_counts = {cat: count for cat, count in categories}

    priorities = db.session.query(Task.priority, db.func.count(Task.id)).filter_by(user_id=user_id).group_by(Task.priority).all()
    priority_counts = {pri: count for pri, count in priorities}

    productivity = []
    today = date.today()
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        start_time = datetime.combine(day, datetime.min.time())
        end_time = datetime.combine(day, datetime.max.time())
        
        count = Task.query.filter(
            Task.user_id == user_id,
            Task.is_completed == True,
            Task.completed_at >= start_time,
            Task.completed_at <= end_time
        ).count()
        
        productivity.append({
            'date': day.strftime('%b %d'),
            'completed': count
        })

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'completion_rate': completion_rate,
        'categories': category_counts,
        'priorities': priority_counts,
        'productivity': productivity
    }

# ==============================================================================
# Authentication Middleware
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not g.user:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized access'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)
        if not g.user:
            session.clear()

# ==============================================================================
# Error Handlers
# ==============================================================================
@app.errorhandler(400)
def bad_request_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400
    return render_template('error.html', code=400, title='Bad Request', message='The request was invalid or malformed.'), 400

@app.errorhandler(401)
def unauthorized_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Unauthorized', 'message': 'Please log in to continue.'}), 401
    return redirect(url_for('login'))

@app.errorhandler(403)
def forbidden_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden', 'message': 'Access forbidden or CSRF validation failed.'}), 403
    return render_template('error.html', code=403, title='Forbidden', message='You do not have permission to access this resource.'), 403

@app.errorhandler(404)
def not_found_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found', 'message': 'Requested resource not found.'}), 404
    return render_template('error.html', code=404, title='Page Not Found', message='The page you are looking for does not exist or has been moved.'), 404

@app.errorhandler(413)
def payload_too_large_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'File Too Large', 'message': 'Uploaded file exceeds the maximum 16MB limit.'}), 413
    return render_template('error.html', code=413, title='File Too Large', message='The file you tried to upload exceeds the 16MB maximum limit.'), 413

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected server error occurred.'}), 500
    return render_template('error.html', code=500, title='Server Error', message='An internal error occurred. Please try again in a few moments.'), 500

# ==============================================================================
# Authentication Routes
# ==============================================================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if g.user:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'
        if is_rate_limited(client_ip):
            flash('Too many attempts. Please wait a minute before trying again.', 'danger')
            return render_template('signup.html'), 429
            
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Strict Input Validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('signup.html'), 400
            
        if not USERNAME_REGEX.match(username):
            flash('Username must be 3-30 characters long and contain only letters, numbers, and underscores.', 'danger')
            return render_template('signup.html'), 400
            
        if not EMAIL_REGEX.match(email) or len(email) > 120:
            flash('Please provide a valid email address.', 'danger')
            return render_template('signup.html'), 400
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('signup.html'), 400
            
        if User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'danger')
            return render_template('signup.html'), 400
            
        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'danger')
            return render_template('signup.html'), 400
            
        # Create user
        password_hash = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        
        # Create default system settings
        user_settings = SystemSettings(
            user_id=user.id,
            user_email=email,
            email_reminders_enabled=False,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            smtp_user="",
            smtp_password=""
        )
        db.session.add(user_settings)
        
        # Welcome notification
        welcome_notif = Notification(
            user_id=user.id,
            message="Welcome to ZenTask! Organize your life with clarity and focus.",
            type="success"
        )
        db.session.add(welcome_notif)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'
        if is_rate_limited(client_ip):
            flash('Too many login attempts. Please wait a minute before trying again.', 'danger')
            return render_template('login.html'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please provide both username and password.', 'danger')
            return render_template('login.html'), 400
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session.permanent = True
            generate_csrf_token()  # Regenerate token on fresh session
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out safely.', 'success')
    return redirect(url_for('login'))

# ==============================================================================
# Core Views & Dashboard
# ==============================================================================
@app.route('/')
@login_required
def index():
    tasks = Task.query.filter_by(user_id=g.user.id).order_by(
        Task.is_completed.asc(),
        Task.position.asc(),
        Task.due_date.asc(),
        Task.id.desc()
    ).all()
    stats = get_task_stats(g.user.id)
    return render_template('index.html', tasks=tasks, stats=stats, date=date)

# ==============================================================================
# Task API Endpoints
# ==============================================================================
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    query = Task.query.filter_by(user_id=g.user.id)
    
    category = request.args.get('category')
    priority = request.args.get('priority')
    is_completed = request.args.get('is_completed')
    search = request.args.get('search')
    
    if category and category in ALLOWED_CATEGORIES:
        query = query.filter(Task.category == category)
    if priority and priority in ALLOWED_PRIORITIES:
        query = query.filter(Task.priority == priority)
    if is_completed is not None:
        completed_bool = is_completed.lower() == 'true'
        query = query.filter(Task.is_completed == completed_bool)
    if search:
        clean_search = search.strip()[:100]
        if clean_search:
            # Escape wildcards safely
            escaped_search = clean_search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.filter((Task.title.ilike(f"%{escaped_search}%")) | (Task.description.ilike(f"%{escaped_search}%")))
        
    tasks = query.order_by(Task.is_completed.asc(), Task.position.asc(), Task.due_date.asc(), Task.id.desc()).all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    if len(title) > 100:
        return jsonify({'error': 'Title must be under 100 characters'}), 400
        
    description = (data.get('description') or '').strip()
    if len(description) > 2000:
        return jsonify({'error': 'Description must be under 2000 characters'}), 400

    priority = data.get('priority', 'medium')
    if priority not in ALLOWED_PRIORITIES:
        priority = 'medium'

    category = data.get('category', 'personal')
    if category not in ALLOWED_CATEGORIES:
        category = 'personal'
        
    due_date_str = data.get('due_date')
    due_date = None
    if due_date_str:
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            pass

    pos = Task.query.filter_by(user_id=g.user.id).count()

    task = Task(
        user_id=g.user.id,
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        is_completed=False,
        position=pos
    )
    
    db.session.add(task)
    db.session.commit()
    
    return jsonify({
        'task': task.to_dict(),
        'stats': get_task_stats(g.user.id)
    }), 201

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    task.is_completed = not task.is_completed
    if task.is_completed:
        task.completed_at = datetime.now()
    else:
        task.completed_at = None
    db.session.commit()
    
    return jsonify({
        'task': task.to_dict(),
        'stats': get_task_stats(g.user.id)
    })

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    data = request.get_json() or {}
    
    title = data.get('title', '').strip()
    if title:
        if len(title) > 100:
            return jsonify({'error': 'Title must be under 100 characters'}), 400
        task.title = title
        
    if 'description' in data:
        desc = (data.get('description') or '').strip()
        if len(desc) > 2000:
            return jsonify({'error': 'Description must be under 2000 characters'}), 400
        task.description = desc
        
    priority = data.get('priority')
    if priority and priority in ALLOWED_PRIORITIES:
        task.priority = priority
        
    category = data.get('category')
    if category and category in ALLOWED_CATEGORIES:
        task.category = category
    
    if 'due_date' in data:
        due_date_str = data.get('due_date')
        if due_date_str:
            try:
                task.due_date = date.fromisoformat(due_date_str)
            except ValueError:
                task.due_date = None
        else:
            task.due_date = None
        
    db.session.commit()
    
    return jsonify({
        'task': task.to_dict(),
        'stats': get_task_stats(g.user.id)
    })

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    
    # Remove all physical attachment files
    for att in task.attachments:
        if os.path.exists(att.filepath):
            try:
                os.remove(att.filepath)
            except Exception as e:
                print(f"Error removing attachment file: {e}")
                
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'stats': get_task_stats(g.user.id)
    })

@app.route('/api/tasks/reorder', methods=['POST'])
@login_required
def reorder_tasks():
    data = request.get_json() or {}
    orders = data.get('orders', [])
    if isinstance(orders, list):
        for item in orders:
            task_id = item.get('id')
            pos = item.get('position')
            if isinstance(task_id, int) and isinstance(pos, int):
                task = Task.query.filter_by(id=task_id, user_id=g.user.id).first()
                if task:
                    task.position = pos
        db.session.commit()
    return jsonify({'success': True, 'stats': get_task_stats(g.user.id)})

# ==============================================================================
# Attachments API (Secure Upload & Download)
# ==============================================================================
@app.route('/api/tasks/<int:task_id>/attachments', methods=['POST'])
@login_required
def upload_attachment(task_id):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    if 'file' not in request.files:
        return jsonify({'error': 'No file was provided in request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file was selected'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(sorted(ALLOWED_EXTENSIONS))}'}), 400
        
    original_name = secure_filename(file.filename)
    if not original_name:
        original_name = f"attachment_{int(time.time())}"
        
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    
    attachment = TaskAttachment(
        task_id=task.id,
        filename=original_name,
        filepath=filepath,
        file_size=file_size
    )
    db.session.add(attachment)
    
    notif = Notification(
        user_id=g.user.id,
        message=f"Attached file '{original_name}' to task: '{task.title}'",
        type='info'
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({
        'attachment': attachment.to_dict(),
        'task': task.to_dict()
    }), 201

@app.route('/api/tasks/attachments/<int:attachment_id>', methods=['DELETE'])
@login_required
def delete_attachment(attachment_id):
    attachment = TaskAttachment.query.get_or_404(attachment_id)
    task = Task.query.filter_by(id=attachment.task_id, user_id=g.user.id).first_or_404()
    
    # Path traversal safety check
    safe_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
    target_path = os.path.abspath(attachment.filepath)
    if target_path.startswith(safe_dir) and os.path.exists(target_path):
        try:
            os.remove(target_path)
        except Exception as e:
            print(f"Error removing file: {e}")
            
    db.session.delete(attachment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'task': task.to_dict()
    })

@app.route('/api/tasks/attachments/<int:attachment_id>/download', methods=['GET'])
@login_required
def download_attachment(attachment_id):
    attachment = TaskAttachment.query.get_or_404(attachment_id)
    task = Task.query.filter_by(id=attachment.task_id, user_id=g.user.id).first_or_404()
    
    safe_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
    target_path = os.path.abspath(attachment.filepath)
    if not target_path.startswith(safe_dir) or not os.path.exists(target_path):
        return jsonify({'error': 'File not found on server'}), 404
        
    return send_file(target_path, as_attachment=True, download_name=attachment.filename)

# ==============================================================================
# Notifications API
# ==============================================================================
@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=g.user.id).order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    })

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=g.user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'success': True})

# ==============================================================================
# System Settings & Export APIs
# ==============================================================================
@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    settings = SystemSettings.query.filter_by(user_id=g.user.id).first()
    return jsonify(settings.to_dict() if settings else {})

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json() or {}
    settings = SystemSettings.query.filter_by(user_id=g.user.id).first()
    if not settings:
        settings = SystemSettings(user_id=g.user.id)
        db.session.add(settings)
        
    user_email = (data.get('user_email') or '').strip()
    if user_email and not EMAIL_REGEX.match(user_email):
        return jsonify({'error': 'Invalid email address format'}), 400
        
    settings.user_email = user_email
    settings.email_reminders_enabled = bool(data.get('email_reminders_enabled', False))
    settings.smtp_server = (data.get('smtp_server') or '').strip()[:120]
    
    try:
        settings.smtp_port = int(data.get('smtp_port', 587))
    except (ValueError, TypeError):
        settings.smtp_port = 587
        
    settings.smtp_user = (data.get('smtp_user') or '').strip()[:120]
    if data.get('smtp_password'):
        settings.smtp_password = str(data.get('smtp_password'))[:120]
        
    db.session.commit()
    return jsonify({'success': True, 'settings': settings.to_dict()})

@app.route('/api/settings/email-logs', methods=['GET'])
@login_required
def get_email_logs():
    log_path = os.path.join(BASE_DIR, 'sent_emails.log')
    logs = ""
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = f.read()
        except Exception as e:
            logs = f"Error reading log: {e}"
    else:
        logs = "No email logs found yet. Once a reminder triggers, it will appear here."
    return jsonify({'logs': logs})

@app.route('/api/tasks/export/csv', methods=['GET'])
@login_required
def export_csv():
    tasks = Task.query.filter_by(user_id=g.user.id).order_by(Task.is_completed.asc(), Task.due_date.asc(), Task.id.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Description', 'Priority', 'Category', 'Due Date', 'Completed', 'Created At', 'Completed At'])
    
    for t in tasks:
        writer.writerow([
            t.id,
            t.title,
            t.description or '',
            t.priority,
            t.category,
            t.due_date.isoformat() if t.due_date else '',
            t.is_completed,
            t.created_at.isoformat(),
            t.completed_at.isoformat() if t.completed_at else ''
        ])
        
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"zentask_export_{date.today().isoformat()}.csv"
    )

@app.route('/api/tasks/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    tasks = Task.query.filter_by(user_id=g.user.id).order_by(Task.is_completed.asc(), Task.due_date.asc(), Task.id.desc()).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=9,
        leading=11
    )
    
    cell_bold_style = ParagraphStyle(
        'CellBoldText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        leading=12
    )

    story.append(Paragraph("ZenTask - Task Report", title_style))
    story.append(Paragraph(f"User: {g.user.username} | Generated on {datetime.now().strftime('%b %d, %Y at %I:%M %p')} | Total Tasks: {len(tasks)}", meta_style))
    story.append(Spacer(1, 10))
    
    table_data = [[
        Paragraph("Status", header_style),
        Paragraph("Title & Description", header_style),
        Paragraph("Priority", header_style),
        Paragraph("Category", header_style),
        Paragraph("Due Date", header_style)
    ]]
    
    for t in tasks:
        status_text = "Completed" if t.is_completed else "Pending"
        status_color = "#10b981" if t.is_completed else "#f59e0b"
        
        status_p = Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", cell_bold_style)
        desc_text = f"<br/><font color='#6b7280'>{t.description}</font>" if t.description else ""
        title_p = Paragraph(f"<b>{t.title}</b>{desc_text}", cell_style)
        priority_p = Paragraph(t.priority.upper(), cell_bold_style)
        category_p = Paragraph(t.category.capitalize(), cell_style)
        due_p = Paragraph(t.due_date.strftime('%b %d, %Y') if t.due_date else '-', cell_style)
        
        table_data.append([status_p, title_p, priority_p, category_p, due_p])
        
    col_widths = [70, 242, 65, 75, 80]
    task_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#11131c')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ])
    
    task_table.setStyle(t_style)
    story.append(task_table)
    doc.build(story)
    
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"zentask_report_{date.today().isoformat()}.pdf"
    )

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    return jsonify(get_task_stats(g.user.id))

# ==============================================================================
# App Startup & Background Worker
# ==============================================================================
with app.app_context():
    upgrade_db()
    db.create_all()

scheduler_thread = threading.Thread(target=run_email_scheduler, args=(app,), daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])

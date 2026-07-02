from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
# Use environment variable for secret key, with fallback for development
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# Disable debug mode in production
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
# Security headers
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    complete = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    due_date = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(50), default='General')
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Todo {self.id} - {self.title}>'

@app.route("/", methods=["GET", "POST"])
def input():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        complete = request.form.get("complete") == "on"
        priority = request.form.get("priority", "medium")
        due_date_str = request.form.get("due_date")
        category = request.form.get("category", "General")
        
        # Validate priority
        if priority not in ['high', 'medium', 'low']:
            priority = 'medium'
        
        # Sanitize and validate category
        category = category.strip()[:50] if category else 'General'
        
        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
        
        if not title:
            flash('Title is required!', 'danger')
        else:
            # Sanitize title and description
            title = title.strip()[:100]
            description = description.strip()[:200] if description else None
            
            new_todo = Todo(
                title=title, 
                description=description, 
                complete=complete,
                priority=priority,
                due_date=due_date,
                category=category
            )
            db.session.add(new_todo)
            db.session.commit()
            flash('Task added successfully!', 'success')
        
        return redirect(url_for("input"))

    # Get filter parameters
    filter_status = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    search_query = request.args.get('search', '')
    
    # Build query
    query = Todo.query
    
    # Apply filters
    if filter_status == 'completed':
        query = query.filter_by(complete=True)
    elif filter_status == 'pending':
        query = query.filter_by(complete=False)
    
    if filter_priority != 'all':
        query = query.filter_by(priority=filter_priority)
    
    if search_query:
        query = query.filter(
            (Todo.title.contains(search_query)) | 
            (Todo.description.contains(search_query))
        )
    
    # Order by date (newest first)
    todos = query.order_by(Todo.date.desc()).all()
    
    return render_template("index.html", todos=todos, now=datetime.now)

@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    flash('Task deleted successfully!', 'info')
    return redirect(url_for("input"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    todo = Todo.query.get_or_404(id)
    if request.method == "POST":
        # Sanitize and validate inputs
        title = request.form.get("title", "").strip()[:100]
        description = request.form.get("description", "").strip()[:200] if request.form.get("description") else None
        todo.complete = request.form.get("complete") == "on"
        
        # Validate priority
        priority = request.form.get("priority", "medium")
        if priority not in ['high', 'medium', 'low']:
            priority = 'medium'
        todo.priority = priority
        
        # Sanitize category
        category = request.form.get("category", "General")
        todo.category = category.strip()[:50] if category else 'General'
        
        due_date_str = request.form.get("due_date")
        if due_date_str:
            try:
                todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format', 'danger')
        
        if not title:
            flash('Title cannot be empty!', 'danger')
            return render_template("edit.html", todo=todo)
        
        todo.title = title
        todo.description = description
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for("input"))
    return render_template("edit.html", todo=todo)

@app.route("/delete_all")
def delete_all():
    db.session.query(Todo).delete()
    db.session.commit()
    flash('All tasks deleted!', 'info')
    return redirect(url_for("input"))

@app.route("/toggle/<int:id>")
def toggle(id):
    todo = Todo.query.get_or_404(id)
    todo.complete = not todo.complete
    db.session.commit()
    status = "completed" if todo.complete else "pending"
    flash(f'Task marked as {status}!', 'success')
    return redirect(url_for("input"))

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    # Only enable debug mode if explicitly set
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)
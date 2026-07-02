# 📝 To-Do Application

A modern, feature-rich task management web application built with Flask and SQLAlchemy. This project demonstrates best practices in web development including security, user experience, and clean code architecture.
## ✨ Features

### Core Functionality
- ✅ **CRUD Operations** - Create, read, update, and delete tasks
- 🔄 **Quick Toggle** - One-click task completion status change
- 🗑️ **Bulk Delete** - Remove all tasks with confirmation
- 💾 **Persistent Storage** - SQLite database for data persistence

<img width="1896" height="816" alt="Screenshot 2026-07-02 222741" src="https://github.com/user-attachments/assets/fc68ebcf-28e6-48e2-b24b-895ad7076b67" />
<img width="1892" height="607" alt="Screenshot 2026-07-02 222801" src="https://github.com/user-attachments/assets/60123318-a11a-461d-93b0-013ed39a7fb8" />
<img width="1888" height="447" alt="Screenshot 2026-07-02 222837" src="https://github.com/user-attachments/assets/a880cfbb-7b20-4ae1-96d1-4035e75207d4" />
### Task Management
- 🎯 **Priority Levels** - High, Medium, Low with color-coded badges
- 📅 **Due Dates** - Set deadlines with overdue highlighting
- 🏷️ **Categories** - Organize tasks by custom categories
- ✔️ **Status Tracking** - Visual distinction between completed and pending tasks
<img width="1897" height="867" alt="Screenshot 2026-07-02 222900" src="https://github.com/user-attachments/assets/e43cb73c-5d08-46fb-bf55-8cb33d5e6435" />
### Search & Filter
- 🔍 **Smart Search** - Search across titles and descriptions
- 📊 **Advanced Filters** - Filter by status (All/Pending/Completed) and priority
- 🔄 **Quick Navigation** - One-click access to completed tasks
- 🧹 **Clear Filters** - Reset all filters instantly

### User Experience
- 💬 **Flash Messages** - Real-time feedback for all actions
- 🎨 **Modern UI** - Bootstrap 5 responsive design
- 📱 **Mobile Friendly** - Fully responsive layout
- ⚡ **Confirmation Dialogs** - Prevent accidental deletions
- 🎯 **Empty States** - Helpful messages when no tasks exist

### Security
- 🔒 **Input Validation** - All inputs sanitized and validated
- 🛡️ **SQL Injection Protection** - ORM with parameterized queries
- 🔐 **XSS Prevention** - Auto-escaping enabled
- 🍪 **Secure Sessions** - HTTPOnly and SameSite cookies
- 🔑 **Environment-based Config** - Secret keys via environment variables

## 🛠️ Technologies Used

- **Backend**: Python, Flask 2.3.3
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, Bootstrap 5.3.0, Jinja2
- **Security**: Flask session management, input sanitization

## 📦 Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd todo-app
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open browser and navigate to:
```
http://127.0.0.1:5000
```

## 🚀 Usage

### Adding Tasks
1. Fill in the task title (required)
2. Add description (optional)
3. Select priority level
4. Set due date (optional)
5. Choose category (optional)
6. Click "Add Task"

### Managing Tasks
- **Edit**: Click the yellow Edit button
- **Delete**: Click the red Delete button (with confirmation)
- **Toggle Status**: Click the blue checkmark button to mark complete/incomplete

### Searching & Filtering
- Use the search bar to find tasks by title or description
- Filter by status (All/Pending/Completed)
- Filter by priority (High/Medium/Low)
- Click "Clear" to reset all filters

## 🔒 Security Features

- **Input Sanitization**: All user inputs are stripped and length-limited
- **SQL Injection Prevention**: Uses SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Jinja2 auto-escaping enabled
- **CSRF Ready**: Session cookies configured with HTTPOnly and SameSite flags
- **Environment Configuration**: Sensitive data via environment variables
- **Debug Mode Protection**: Disabled by default in production

## 📁 Project Structure

```
todo-app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
├── instance/
│   └── todo.db           # SQLite database (auto-created)
└── templates/
    ├── index.html        # Main page template
    └── edit.html         # Edit task template
```

## 🎯 Key Highlights

- **Clean Code**: Well-structured, commented, and follows PEP 8
- **Security First**: Multiple layers of protection against common vulnerabilities
- **User-Friendly**: Intuitive interface with helpful feedback
- **Responsive**: Works seamlessly on desktop, tablet, and mobile
- **Production Ready**: Environment-based configuration and security best practices


## 📝 License

This project is open source and available for educational and commercial use.

## 👨‍💻 Author

**Abhijeet**
- LinkedIn: [https://www.linkedin.com/in/abhijeetkumar-gautam/]
- GitHub: [https://github.com/Abhijeet0848]

---

⭐ Star this repository if you found it helpful!

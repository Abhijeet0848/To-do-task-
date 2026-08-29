"""
MongoDB Atlas Complete Data Access Layer for ZenTask
"""
import os
import re
from datetime import datetime, date, timedelta
from bson.objectid import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING

client = None
db = None

def get_mongo_db():
    global client, db
    if db is not None:
        return db
        
    uri = os.environ.get('MONGODB_URI') or os.environ.get('DATABASE_URL')
    if not uri or not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
        return None
        
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Parse db name
        db_name = 'zentask'
        db = client[db_name]
        
        # Ensure Indexes
        db.users.create_index([("username", ASCENDING)], unique=True)
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.tasks.create_index([("user_id", ASCENDING), ("is_completed", ASCENDING)])
        db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        return db
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None

# ==============================================================================
# User Operations
# ==============================================================================
class MongoUser:
    def __init__(self, doc):
        if not doc:
            return
        self.id = str(doc.get('_id'))
        self._doc_id = doc.get('_id')
        self.username = doc.get('username')
        self.email = doc.get('email')
        self.password_hash = doc.get('password_hash')
        self.created_at = doc.get('created_at', datetime.now())

    @property
    def settings(self):
        mdb = get_mongo_db()
        doc = mdb.system_settings.find_one({"user_id": self.id})
        return MongoSettings(doc) if doc else None

    @staticmethod
    def find_by_id(user_id):
        mdb = get_mongo_db()
        try:
            doc = mdb.users.find_one({"_id": ObjectId(user_id)})
            return MongoUser(doc) if doc else None
        except Exception:
            return None

    @staticmethod
    def find_by_username(username):
        mdb = get_mongo_db()
        doc = mdb.users.find_one({"username": username})
        return MongoUser(doc) if doc else None

    @staticmethod
    def find_by_email(email):
        mdb = get_mongo_db()
        doc = mdb.users.find_one({"email": email.lower().strip()})
        return MongoUser(doc) if doc else None

    @staticmethod
    def create(username, email, password_hash):
        mdb = get_mongo_db()
        now = datetime.now()
        res = mdb.users.insert_one({
            "username": username,
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "created_at": now
        })
        user_id = str(res.inserted_id)
        
        # Create default system settings
        mdb.system_settings.insert_one({
            "user_id": user_id,
            "user_email": email.lower().strip(),
            "email_reminders_enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": ""
        })
        
        # Add welcome notification
        mdb.notifications.insert_one({
            "user_id": user_id,
            "message": "Welcome to ZenTask! Your tasks are now securely backed up to MongoDB Atlas.",
            "type": "success",
            "is_read": False,
            "created_at": now
        })
        
        return MongoUser.find_by_id(user_id)

    def update_password(self, new_password_hash):
        mdb = get_mongo_db()
        mdb.users.update_one({"_id": self._doc_id}, {"$set": {"password_hash": new_password_hash}})
        self.password_hash = new_password_hash

# ==============================================================================
# Settings Operations
# ==============================================================================
class MongoSettings:
    def __init__(self, doc):
        self.id = str(doc.get('_id')) if doc else None
        self.user_id = doc.get('user_id', '') if doc else ''
        self.user_email = doc.get('user_email', '') if doc else ''
        self.email_reminders_enabled = doc.get('email_reminders_enabled', False) if doc else False
        self.smtp_server = doc.get('smtp_server', 'smtp.gmail.com') if doc else 'smtp.gmail.com'
        self.smtp_port = doc.get('smtp_port', 587) if doc else 587
        self.smtp_user = doc.get('smtp_user', '') if doc else ''
        self.smtp_password = doc.get('smtp_password', '') if doc else ''

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'email_reminders_enabled': self.email_reminders_enabled,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_user': self.smtp_user
        }

    @staticmethod
    def get_or_create(user_id, email=""):
        mdb = get_mongo_db()
        doc = mdb.system_settings.find_one({"user_id": str(user_id)})
        if not doc:
            res = mdb.system_settings.insert_one({
                "user_id": str(user_id),
                "user_email": email,
                "email_reminders_enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": ""
            })
            doc = mdb.system_settings.find_one({"_id": res.inserted_id})
        return MongoSettings(doc)

    @staticmethod
    def update(user_id, data):
        mdb = get_mongo_db()
        update_fields = {}
        if 'user_email' in data: update_fields['user_email'] = data['user_email']
        if 'email_reminders_enabled' in data: update_fields['email_reminders_enabled'] = bool(data['email_reminders_enabled'])
        if 'smtp_server' in data: update_fields['smtp_server'] = data['smtp_server']
        if 'smtp_port' in data: update_fields['smtp_port'] = int(data['smtp_port'])
        if 'smtp_user' in data: update_fields['smtp_user'] = data['smtp_user']
        if 'smtp_password' in data and data['smtp_password']: update_fields['smtp_password'] = data['smtp_password']
        
        mdb.system_settings.update_one({"user_id": str(user_id)}, {"$set": update_fields}, upsert=True)
        return MongoSettings.get_or_create(user_id)

def parse_flexible_date(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    val_str = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(val_str, fmt).date()
        except (ValueError, TypeError):
            pass
    return None

# ==============================================================================
# Task Operations
# ==============================================================================
class MongoTask:
    def __init__(self, doc):
        self.id = str(doc.get('_id'))
        self._doc_id = doc.get('_id')
        self.user_id = str(doc.get('user_id'))
        self.title = doc.get('title', '')
        self.description = doc.get('description', '')
        self.priority = doc.get('priority', 'medium')
        self.category = doc.get('category', 'personal')
        
        raw_due = doc.get('due_date')
        self.due_date = parse_flexible_date(raw_due)
            
        self.is_completed = doc.get('is_completed', False)
        self.created_at = doc.get('created_at', datetime.now())
        self.position = doc.get('position', 0)
        self.completed_at = doc.get('completed_at')
        self.reminder_sent = doc.get('reminder_sent', False)
        self.attachments = [MongoAttachment(a) for a in doc.get('attachments', [])]

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
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            'position': self.position,
            'completed_at': self.completed_at.isoformat() if isinstance(self.completed_at, datetime) else (self.completed_at or ''),
            'reminder_sent': self.reminder_sent,
            'attachments': [a.to_dict() for a in self.attachments]
        }

    @staticmethod
    def find_by_user(user_id, category=None, priority=None, is_completed=None, search=None):
        mdb = get_mongo_db()
        query = {"user_id": str(user_id)}
        if category:
            query["category"] = category
        if priority:
            query["priority"] = priority
        if is_completed is not None:
            query["is_completed"] = bool(is_completed)
        if search:
            escaped = re.escape(search.strip())
            query["$or"] = [
                {"title": {"$regex": escaped, "$options": "i"}},
                {"description": {"$regex": escaped, "$options": "i"}}
            ]
            
        docs = mdb.tasks.find(query).sort([
            ("is_completed", ASCENDING),
            ("position", ASCENDING),
            ("due_date", ASCENDING),
            ("_id", DESCENDING)
        ])
        return [MongoTask(d) for d in docs]

    @staticmethod
    def find_by_id(task_id, user_id):
        mdb = get_mongo_db()
        try:
            doc = mdb.tasks.find_one({"_id": ObjectId(task_id), "user_id": str(user_id)})
            return MongoTask(doc) if doc else None
        except Exception:
            return None

    @staticmethod
    def create(user_id, title, description, priority, category, due_date):
        mdb = get_mongo_db()
        parsed_due = parse_flexible_date(due_date)
        due_iso = parsed_due.isoformat() if parsed_due else ""
        count = mdb.tasks.count_documents({"user_id": str(user_id)})
        
        doc = {
            "user_id": str(user_id),
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "due_date": due_iso,
            "is_completed": False,
            "created_at": datetime.now(),
            "position": count,
            "completed_at": None,
            "reminder_sent": False,
            "attachments": []
        }
        res = mdb.tasks.insert_one(doc)
        doc['_id'] = res.inserted_id
        return MongoTask(doc)

    @staticmethod
    def toggle(task_id, user_id):
        mdb = get_mongo_db()
        task = MongoTask.find_by_id(task_id, user_id)
        if not task:
            return None
        new_status = not task.is_completed
        completed_at = datetime.now() if new_status else None
        mdb.tasks.update_one(
            {"_id": ObjectId(task_id), "user_id": str(user_id)},
            {"$set": {"is_completed": new_status, "completed_at": completed_at}}
        )
        return MongoTask.find_by_id(task_id, user_id)

    @staticmethod
    def update(task_id, user_id, data):
        mdb = get_mongo_db()
        updates = {}
        if 'title' in data and data['title'].strip():
            updates['title'] = data['title'].strip()
        if 'description' in data:
            updates['description'] = (data['description'] or '').strip()
        if 'priority' in data:
            updates['priority'] = data['priority']
        if 'category' in data:
            updates['category'] = data['category']
        if 'due_date' in data:
            updates['due_date'] = data['due_date'] or ''
            
        mdb.tasks.update_one({"_id": ObjectId(task_id), "user_id": str(user_id)}, {"$set": updates})
        return MongoTask.find_by_id(task_id, user_id)

    @staticmethod
    def delete(task_id, user_id):
        mdb = get_mongo_db()
        res = mdb.tasks.delete_one({"_id": ObjectId(task_id), "user_id": str(user_id)})
        return res.deleted_count > 0

    @staticmethod
    def reorder(user_id, orders):
        mdb = get_mongo_db()
        for item in orders:
            tid = item.get('id')
            pos = item.get('position')
            try:
                mdb.tasks.update_one(
                    {"_id": ObjectId(tid), "user_id": str(user_id)},
                    {"$set": {"position": pos}}
                )
            except Exception:
                pass

    @staticmethod
    def add_attachment(task_id, user_id, filename, filepath, file_size):
        mdb = get_mongo_db()
        att_id = str(ObjectId())
        att = {
            "_id": att_id,
            "task_id": str(task_id),
            "filename": filename,
            "filepath": filepath,
            "file_size": file_size,
            "created_at": datetime.now()
        }
        mdb.tasks.update_one(
            {"_id": ObjectId(task_id), "user_id": str(user_id)},
            {"$push": {"attachments": att}}
        )
        return MongoAttachment(att)

    @staticmethod
    def remove_attachment(att_id, user_id):
        mdb = get_mongo_db()
        # Find task containing attachment
        task_doc = mdb.tasks.find_one({"user_id": str(user_id), "attachments._id": str(att_id)})
        if not task_doc:
            return None, None
            
        removed_file = None
        for a in task_doc.get('attachments', []):
            if a.get('_id') == str(att_id):
                removed_file = a.get('filepath')
                break
                
        mdb.tasks.update_one(
            {"_id": task_doc['_id']},
            {"$pull": {"attachments": {"_id": str(att_id)}}}
        )
        return MongoTask.find_by_id(task_doc['_id'], user_id), removed_file

# ==============================================================================
# Attachment Helper
# ==============================================================================
class MongoAttachment:
    def __init__(self, doc):
        self.id = str(doc.get('_id'))
        self.task_id = str(doc.get('task_id'))
        self.filename = doc.get('filename')
        self.filepath = doc.get('filepath')
        self.file_size = doc.get('file_size', 0)
        self.created_at = doc.get('created_at', datetime.now())

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at)
        }

# ==============================================================================
# Notification Operations
# ==============================================================================
class MongoNotification:
    def __init__(self, doc):
        self.id = str(doc.get('_id'))
        self.user_id = str(doc.get('user_id'))
        self.message = doc.get('message')
        self.type = doc.get('type', 'info')
        self.is_read = doc.get('is_read', False)
        self.created_at = doc.get('created_at', datetime.now())

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at)
        }

    @staticmethod
    def get_user_notifications(user_id, limit=50):
        mdb = get_mongo_db()
        docs = mdb.notifications.find({"user_id": str(user_id)}).sort("created_at", DESCENDING).limit(limit)
        unread = mdb.notifications.count_documents({"user_id": str(user_id), "is_read": False})
        return [MongoNotification(d) for d in docs], unread

    @staticmethod
    def mark_read(notif_id, user_id):
        mdb = get_mongo_db()
        try:
            mdb.notifications.update_one({"_id": ObjectId(notif_id), "user_id": str(user_id)}, {"$set": {"is_read": True}})
            return True
        except Exception:
            return False

    @staticmethod
    def mark_all_read(user_id):
        mdb = get_mongo_db()
        mdb.notifications.update_many({"user_id": str(user_id), "is_read": False}, {"$set": {"is_read": True}})

    @staticmethod
    def create(user_id, message, msg_type="info"):
        mdb = get_mongo_db()
        mdb.notifications.insert_one({
            "user_id": str(user_id),
            "message": message,
            "type": msg_type,
            "is_read": False,
            "created_at": datetime.now()
        })

# ==============================================================================
# Stats Aggregation
# ==============================================================================
def get_mongo_stats(user_id):
    mdb = get_mongo_db()
    uid = str(user_id)
    
    total = mdb.tasks.count_documents({"user_id": uid})
    completed = mdb.tasks.count_documents({"user_id": uid, "is_completed": True})
    pending = total - completed
    rate = round((completed / total) * 100) if total > 0 else 0
    
    # Categories count
    categories = ['personal', 'work', 'shopping', 'fitness', 'urgent', 'coding']
    cat_counts = {}
    for c in categories:
        cat_counts[c] = mdb.tasks.count_documents({"user_id": uid, "category": c})
        
    # Priorities count
    priorities = ['low', 'medium', 'high']
    pri_counts = {}
    for p in priorities:
        pri_counts[p] = mdb.tasks.count_documents({"user_id": uid, "priority": p})
        
    # 14 day productivity
    productivity = []
    today = date.today()
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        
        count = mdb.tasks.count_documents({
            "user_id": uid,
            "is_completed": True,
            "completed_at": {"$gte": start_dt, "$lte": end_dt}
        })
        productivity.append({
            'date': day.strftime('%b %d'),
            'completed': count
        })

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'completion_rate': rate,
        'categories': cat_counts,
        'priorities': pri_counts,
        'productivity': productivity
    }

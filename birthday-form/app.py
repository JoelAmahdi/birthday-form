import os
import sqlite3
import datetime
import urllib.parse
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from werkzeug.utils import secure_filename
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_me' # Change in production
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
DATABASE = 'birthdays.db'
DATABASE_URL = os.environ.get('DATABASE_URL')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Initialize Supabase client if credentials are provided
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Simple admin credentials
ADMIN_USERNAME = 'JoelAmahdi'
ADMIN_PASSWORD = 'Joelcozy*7'

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    if DATABASE_URL:
        # Use PostgreSQL
        db = getattr(g, '_database', None)
        if db is None:
            # Connect using the psycopg2 connection string
            db = g._database = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return db
    else:
        # Fallback to SQLite
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row
        return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor() if DATABASE_URL else db
        if DATABASE_URL:
            # PostgreSQL syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    synced BOOLEAN NOT NULL DEFAULT FALSE
                )
            ''')
        else:
            # SQLite syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    synced BOOLEAN NOT NULL DEFAULT 0
                )
            ''')
        db.commit()
        if DATABASE_URL:
            cursor.close()

# Initialize DB on startup
init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_calendar_service():
    """Shows basic usage of the Google Calendar API."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

def upload_to_supabase(file_obj, filename, content_type):
    """Uploads a file to Supabase Storage."""
    file_bytes = file_obj.read()
    # Upload the file
    response = supabase.storage.from_("Birthdays").upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type}
    )
    # Get the public URL for the file
    public_url = supabase.storage.from_("Birthdays").get_public_url(filename)
    return public_url

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit_birthday():
    if 'picture' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['picture']
    name = request.form.get('name')
    date_str = request.form.get('date')

    if not name or not date_str:
        return jsonify({'error': 'Name and date are required'}), 400

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if file:
        filename = secure_filename(f"{int(datetime.datetime.now().timestamp())}_{file.filename}")
        
        if supabase:
            try:
                # Upload to Supabase Storage
                image_path = upload_to_supabase(file, filename, file.content_type)
            except Exception as e:
                print(f"Supabase Upload Error: {e}")
                return jsonify({'error': 'Failed to upload image to cloud storage.'}), 500
        else:
            # Fallback to local storage
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_path = filename

        db = get_db()
        cursor = db.cursor() if DATABASE_URL else db
        
        # Insert into database using parameterization appropriate for the DB type
        if DATABASE_URL:
            # psycopg2 uses %s
            cursor.execute(
                'INSERT INTO submissions (name, date, image_path) VALUES (%s, %s, %s)', 
                (name, date_str, image_path)
            )
        else:
            # sqlite uses ?
            cursor.execute(
                'INSERT INTO submissions (name, date, image_path) VALUES (?, ?, ?)', 
                (name, date_str, image_path)
            )
            
        db.commit()
        if DATABASE_URL:
            cursor.close()

        return jsonify({'message': 'Successfully submitted birthday!'}), 200

    return jsonify({'error': 'Unknown error occurred.'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    db = get_db()
    cursor = db.cursor() if DATABASE_URL else db
    
    cursor.execute('SELECT * FROM submissions ORDER BY id DESC')
    submissions = cursor.fetchall()
    
    if DATABASE_URL:
        cursor.close()
        
    return render_template('admin.html', submissions=submissions)

@app.route('/api/sync-birthday/<int:sub_id>', methods=['POST'])
@login_required
def sync_birthday(sub_id):
    db = get_db()
    cursor = db.cursor() if DATABASE_URL else db
    
    if DATABASE_URL:
        cursor.execute('SELECT * FROM submissions WHERE id = %s', (sub_id,))
    else:
        cursor.execute('SELECT * FROM submissions WHERE id = ?', (sub_id,))
        
    sub = cursor.fetchone()
    
    if not sub:
        if DATABASE_URL: cursor.close()
        return jsonify({'error': 'Submission not found'}), 404

    try:
        birthday_date = datetime.datetime.strptime(sub['date'], "%Y-%m-%d").date()
        service = get_calendar_service()
        
        if not service:
            # Simulate calendar sync if credentials.json is missing
            if DATABASE_URL:
                cursor.execute('UPDATE submissions SET synced = TRUE WHERE id = %s', (sub_id,))
            else:
                cursor.execute('UPDATE submissions SET synced = 1 WHERE id = ?', (sub_id,))
            db.commit()
            if DATABASE_URL: cursor.close()
            return jsonify({
                'message': 'Simulated sync (credentials.json missing)'
            }), 200

        event = {
            'summary': f"🎂 {sub['name']}'s Birthday",
            'description': f"Don't forget to wish {sub['name']} a happy birthday!",
            'start': {
                'date': str(birthday_date),
                'timeZone': 'UTC',
            },
            'end': {
                'date': str(birthday_date + datetime.timedelta(days=1)),
                'timeZone': 'UTC',
            },
            'recurrence': [
                'RRULE:FREQ=YEARLY'
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        service.events().insert(calendarId='primary', body=event).execute()
        
        if DATABASE_URL:
            cursor.execute('UPDATE submissions SET synced = TRUE WHERE id = %s', (sub_id,))
        else:
            cursor.execute('UPDATE submissions SET synced = 1 WHERE id = ?', (sub_id,))
        db.commit()
        if DATABASE_URL: cursor.close()

        return jsonify({'message': 'Successfully synced to calendar'}), 200

    except Exception as e:
        print(e)
        if DATABASE_URL: cursor.close()
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    from flask import send_from_directory, redirect
    # If using Supabase Storage, the frontend might request the URL directly
    # But if they hit this endpoint with a full URL, redirect them
    if filename.startswith('http://') or filename.startswith('https://'):
        return redirect(filename)
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

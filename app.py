from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os
from blockchain import Blockchain
from config import Config
from datetime import datetime
import hashlib
import PyPDF2
from docx import Document

app = Flask(__name__)
app.config.from_object(Config)
blockchain = Blockchain()

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

# Home route
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Redirecting to login...', 'success')
            return redirect(url_for('register'))  # Redirect to show flash message briefly
        except mysql.connector.Error:
            flash('Username already exists', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

# Dashboard route
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_hash = calculate_file_hash(file_path, file.filename.rsplit('.', 1)[1].lower())
            prev_hash = blockchain.get_previous_hash()
            block_hash = blockchain.add_block(session['user_id'], filename, file_path, prev_hash)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO records (user_id, file_name, file_type, file_path, block_hash, prev_hash) VALUES (%s, %s, %s, %s, %s, %s)',
                (session['user_id'], filename, file.filename.rsplit('.', 1)[1].lower(), file_path, block_hash, prev_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('File uploaded and added to blockchain!', 'success')
        else:
            flash('Invalid file type', 'danger')
    return render_template('dashboard.html')

# Records route
@app.route('/records')
def records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT file_name, file_type, file_path, block_hash, prev_hash, timestamp FROM records WHERE user_id = %s', (session['user_id'],))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    processed_records = []
    for record in records:
        if os.path.exists(record[2]):  # Verify file exists
            relative_path = os.path.relpath(record[2], os.path.dirname(app.config['UPLOAD_FOLDER']))
            static_url = url_for('static', filename=relative_path)
            print(f"File Path: {record[2]}, Relative Path: {relative_path}, Static URL: {static_url}")
            processed_records.append((record[0], record[1], relative_path, record[3], record[4], record[5]))
        else:
            print(f"File not found: {record[2]}")
    return render_template('records.html', records=processed_records, upload_folder=app.config['UPLOAD_FOLDER'])

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def calculate_file_hash(file_path, file_type):
    sha256_hash = hashlib.sha256()
    if file_type in ['txt', 'pdf', 'doc', 'docx']:
        try:
            if file_type == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_type == 'pdf':
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    content = ''
                    for page in pdf.pages:
                        content += page.extract_text() or ''
            elif file_type in ['doc', 'docx']:
                doc = Document(file_path)
                content = '\n'.join([para.text for para in doc.paragraphs])
            else:
                content = ''
            sha256_hash.update(content.encode('utf-8'))
        except Exception:
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(byte_block)
    else:
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

if __name__ == '__main__':
    app.run(debug=True)
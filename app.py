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

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB Connection
def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error:
            flash('Username already exists.', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

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
            file_hash = calculate_file_hash(file_path, filename.rsplit('.', 1)[1].lower())
            prev_hash = blockchain.get_previous_hash()
            block_hash = blockchain.add_block(session['user_id'], filename, file_path, prev_hash)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO records (user_id, file_name, file_type, file_path, block_hash, prev_hash) VALUES (%s, %s, %s, %s, %s, %s)',
                (session['user_id'], filename, filename.rsplit('.', 1)[1].lower(), file_path, block_hash, prev_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('File uploaded and added to blockchain!', 'success')
        else:
            flash('Invalid file type.', 'danger')
    return render_template('dashboard.html')

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
        if os.path.exists(record[2]):
            processed_records.append((record[0], record[1], record[2], record[3], record[4], record[5]))
    return render_template('records.html', records=processed_records)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def calculate_file_hash(file_path, file_type):
    sha256_hash = hashlib.sha256()
    try:
        if file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            sha256_hash.update(content.encode('utf-8'))
        elif file_type == 'pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''.join([page.extract_text() or '' for page in reader.pages])
                sha256_hash.update(text.encode('utf-8'))
        elif file_type in ['doc', 'docx']:
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            sha256_hash.update(text.encode('utf-8'))
        else:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)
    except Exception as e:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

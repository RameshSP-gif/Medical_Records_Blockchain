import os

class Config:
    SECRET_KEY = 'your-secret-key-here'
    MYSQL_HOST = 'ballast.proxy.rlwy.net'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'WjJmOBrxBYatyqzmPKEgtWUKLlfjfXNR'
    MYSQL_DB = 'medical_records'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'dcm', 'mp3', 'wav', 'mp4', 'avi'}
    PORT = 25822

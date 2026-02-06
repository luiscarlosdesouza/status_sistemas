import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-this')
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'instance', 'sites.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # USP Senha Unica
    USP_CLIENT_KEY = os.environ.get('USP_CLIENT_KEY')
    USP_CLIENT_SECRET = os.environ.get('USP_CLIENT_SECRET')
    USP_CALLBACK_ID = os.environ.get('USP_CALLBACK_ID')

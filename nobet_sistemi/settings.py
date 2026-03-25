from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'yerel-gelistirme-icin-guvensiz-anahtar-bu-degisebilir')
DEBUG = 'RENDER' not in os.environ

# --- ALLOWED_HOSTS (GÜNCELLENDİ) ---
# Canlı sunucu adresini her zaman listeye ekle
ALLOWED_HOSTS = ['doktor-nobet-sistemi.onrender.com']

# Render'ın otomatik atadığı host adını da ekle (eğer varsa)
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# EĞER YERELDE ÇALIŞIYORSAK (DEBUG=True), '127.0.0.1' adresini de ekle
if DEBUG:
    ALLOWED_HOSTS.append('127.0.0.1')
# --- DEĞİŞİKLİK SONU ---

INSTALLED_APPS = [ 'core.apps.CoreConfig', 'hastane','django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'whitenoise.runserver_nostatic', 'django.contrib.staticfiles' ]
MIDDLEWARE = [ 'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware' ]
ROOT_URLCONF = 'nobet_sistemi.urls'
TEMPLATES = [ { 'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': { 'context_processors': [ 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages' ], }, }, ]
WSGI_APPLICATION = 'nobet_sistemi.wsgi.application'

# --- VERİTABANI ---
if 'RENDER' in os.environ:
    DATABASES = { 'default': dj_database_url.config(conn_max_age=600) } 
else:
    DATABASES = { 'default': { 'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3', } }

LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'doktor_paneli_redirect'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'
# GİRİŞ VE ÇIKIŞ YÖNLENDİRMELERİ
# GİRİŞ VE ÇIKIŞ YÖNLENDİRMELERİ
LOGIN_REDIRECT_URL = 'doktor_paneli' # Giriş yapınca kendi hastane panelimize git
LOGOUT_REDIRECT_URL = 'login'        # Çıkış yapınca şık giriş ekranımıza dön
LOGIN_URL = 'login'                  # Yetkisiz girişte şık ekrana yönlendir
# --- E-POSTA (GMAIL) AYARLARI ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'orkunozdemir526@gmail.com'  # BURAYA KENDİ GMAIL ADRESİNİ YAZ
EMAIL_HOST_PASSWORD = 'oupg fvcm odhs uejb'       # GMAIL "UYGULAMA ŞİFRENİ" YAZ
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Bu satırı en üste, listenin başına aldık:
    path('giris/', auth_views.LoginView.as_view(template_name='hastane/login.html'), name='login'),
    
    path('panel/', views.doktor_paneli, name='doktor_paneli'),
    path('takas-olustur/', views.takas_olustur, name='takas_olustur'),
    path('ajax/load-nobetler/', views.load_nobetler, name='ajax_load_nobetler'),
    path('takas-cevapla/<int:talep_id>/<str:cevap>/', views.takas_cevapla, name='takas_cevapla'),
    # urls.py içine ekleyin:
path('nobet-verileri-json/', views.nobet_verileri_json, name='nobet_verileri_json'),
path('planla/', views.nobet_planla, name='nobet_planla'),
# urlpatterns listesinin içine ekleyin:
path('izin-sil/<int:izin_id>/', views.izin_sil, name='izin_sil'),
]
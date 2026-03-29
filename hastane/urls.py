from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Bu satırı en üste, listenin başına aldık:
    path('giris/', auth_views.LoginView.as_view(template_name='hastane/login.html'), name='login'),
    path('yarin-uyari/', views.yarin_nobetcilerini_uyar, name='yarin_uyari'),
    path('panel/', views.doktor_paneli, name='doktor_paneli'),
    path('takas-olustur/', views.takas_olustur, name='takas_olustur'),
    path('ajax/load-nobetler/', views.load_nobetler, name='ajax_load_nobetler'),
    path('takas-cevapla/<int:talep_id>/<str:cevap>/', views.takas_cevapla, name='takas_cevapla'),
    # ŞİFRE SIFIRLAMA ROTALARI
    path('sifre-sifirla/', auth_views.PasswordResetView.as_view(
        template_name='hastane/sifre_sifirla.html',
        email_template_name='hastane/sifre_sifirla_email.txt',
        subject_template_name='hastane/sifre_sifirla_subject.txt'
    ), name='password_reset'),
    path('sifre-sifirla/gonderildi/', auth_views.PasswordResetDoneView.as_view(template_name='hastane/sifre_sifirla_done.html'), name='password_reset_done'),
    path('sifre-sifirla/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='hastane/sifre_sifirla_confirm.html'), name='password_reset_confirm'),
    path('sifre-sifirla/tamamlandi/', auth_views.PasswordResetCompleteView.as_view(template_name='hastane/sifre_sifirla_complete.html'), name='password_reset_complete'),
    # urls.py içine ekleyin:
path('nobet-verileri-json/', views.nobet_verileri_json, name='nobet_verileri_json'),
path('sistem-loglari/', views.sistem_loglari, name='sistem_loglari'),
path('planla/', views.nobet_planla, name='nobet_planla'),
path('manifest.json', views.manifest_json, name='manifest'),
path('sw.js', views.service_worker, name='service_worker'),
path('ucret-raporu/', views.nobet_ucret_raporu, name='nobet_ucret_raporu'),
path('bildirim-okundu/', views.bildirimleri_okundu_isaretle, name='bildirim_okundu'),
# urlpatterns listesinin içine ekleyin:
path('izin-sil/<int:izin_id>/', views.izin_sil, name='izin_sil'),
path('analiz/', views.nobet_analiz_merkezi, name='nobet_analiz'),
path('resmi-cikti/', views.resmi_pdf_cikti, name='resmi_pdf_cikti'),
path('nobet-havuzu/', views.nobet_havuzu, name='nobet_havuzu'),
    path('havuza-ekle/<int:nobet_id>/', views.havuza_ekle, name='havuza_ekle'),
    path('havuzdan-al/<int:havuz_id>/', views.havuzdan_al, name='havuzdan_al'),
    
]
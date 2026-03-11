from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- Giriş/Çıkış URL'leri ---
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Doktor Paneli URL'leri ---
    path('panel/', views.doktor_paneli_redirect, name='doktor_paneli_redirect'), 
    path('panel/<int:yil>/<int:ay>/', views.doktor_paneli, name='doktor_paneli'),
    path('panel/izin-sil/<int:izin_id>/', views.izin_sil, name='izin_sil'),

    # --- Takvim URL'leri ---
    path('takvim/', views.takvim_redirect, name='takvim_redirect'),
    path('takvim/<int:yil>/<int:ay>/', views.takvim_gorunumu, name='takvim_gorunumu'),
    path('takvim/export/<int:yil>/<int:ay>/', views.export_takvim_excel, name='export_takvim_excel'),

    # --- Yönetim Paneli URL'si ---
    path('yonetim/', views.yonetim_paneli, name='yonetim_paneli'),

    # --- Ana Sayfa URL'si ---
    path('', views.doktor_paneli_redirect, name='home'),
]
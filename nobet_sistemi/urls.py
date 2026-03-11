from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView  # Yönlendirme işlemi için bunu ekledik

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hastane/', include('hastane.urls')),
    path('cikis/', auth_views.LogoutView.as_view(), name='cikis'),
    
    # SİHRİ YAPAN SATIR: Ana sayfaya ('/') girenleri otomatik olarak hastane paneline yönlendir
    path('', RedirectView.as_view(url='/hastane/panel/')),
]
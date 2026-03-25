from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView  # Yönlendirme işlemi için bunu ekledik
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/logout/', LogoutView.as_view(next_page='/admin/login/')),
    path('admin/', admin.site.urls),
    path('hastane/', include('hastane.urls')),
    path('cikis/', auth_views.LogoutView.as_view(), name='cikis'),
    
    # SİHRİ YAPAN SATIR: Ana sayfaya ('/') girenleri otomatik olarak hastane paneline yönlendir
    path('', RedirectView.as_view(url='/hastane/panel/')),
]
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Çıkış işlemi için bunu ekledik

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hastane/', include('hastane.urls')),
    # Çıkış yapıldığında kullanıcıyı login sayfasına yönlendir
    # Ana urls.py içindeki ilgili satırı bu şekilde sadeleştirin:
path('cikis/', auth_views.LogoutView.as_view(), name='cikis'),
]
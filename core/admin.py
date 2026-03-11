from django.contrib import admin
# Burada senin models.py dosyanın içindeki class isimlerini tam olarak yazman lazım.
# Eğer hata alırsan bu satırı kontrol et!
from .models import Doktor, Nobet, IzinTalebi 

admin.site.register(Doktor)
admin.site.register(Nobet)
admin.site.register(IzinTalebi)
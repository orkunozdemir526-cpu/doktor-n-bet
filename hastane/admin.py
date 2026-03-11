from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Poliklinik, Doktor, Nobet, NobetTakas

@admin.register(Poliklinik)
class PoliklinikAdmin(admin.ModelAdmin):
    list_display = ('isim',)
    search_fields = ('isim',)

@admin.register(Doktor)
class DoktorAdmin(admin.ModelAdmin):
    # Admin panelinde hangi sütunların görüneceği
    list_display = ('kullanici', 'poliklinik', 'telefon')
    # Sağ tarafta filtreleme seçenekleri
    list_filter = ('poliklinik',)
    # Arama çubuğunda kullanıcının adına/soyadına göre arama yapma
    search_fields = ('kullanici__first_name', 'kullanici__last_name', 'kullanici__username')

@admin.register(Nobet)
class NobetAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'baslangic_saati', 'bitis_saati')
    list_filter = ('tarih', 'doktor__poliklinik')
    # Üst kısımda tarihe göre gezinme menüsü
    date_hierarchy = 'tarih'

@admin.register(NobetTakas)
class NobetTakasAdmin(admin.ModelAdmin):
    list_display = ('talep_eden_doktor', 'hedef_doktor', 'durum', 'olusturulma_tarihi')
    list_filter = ('durum', 'olusturulma_tarihi')

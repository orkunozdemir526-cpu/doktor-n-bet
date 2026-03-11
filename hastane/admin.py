from django.contrib import admin
from .models import Poliklinik, Doktor, Nobet, NobetTakas, IzinTalebi

@admin.register(Poliklinik)
class PoliklinikAdmin(admin.ModelAdmin):
    list_display = ('isim',)
    search_fields = ('isim',)

@admin.register(Doktor)
class DoktorAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'poliklinik', 'kidem', 'telefon')
    list_filter = ('poliklinik', 'kidem')
    search_fields = ('kullanici__first_name', 'kullanici__last_name')

@admin.register(Nobet)
class NobetAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'bolum', 'baslangic_saati', 'bitis_saati')
    list_filter = ('tarih', 'bolum', 'doktor__poliklinik')
    date_hierarchy = 'tarih'
    change_list_template = "admin/hastane/nobet_changelist.html"

@admin.register(NobetTakas)
class NobetTakasAdmin(admin.ModelAdmin):
    list_display = ('talep_eden_doktor', 'hedef_doktor', 'durum', 'olusturulma_tarihi')
    list_filter = ('durum', 'olusturulma_tarihi')

@admin.action(description='Seçili izin taleplerini ONAYLA')
def izin_onayla(modeladmin, request, queryset):
    queryset.update(durum='onaylandi')

@admin.action(description='Seçili izin taleplerini REDDET')
def izin_reddet(modeladmin, request, queryset):
    queryset.update(durum='reddedildi')

@admin.register(IzinTalebi)
class IzinTalebiAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'durum')
    list_filter = ('durum', 'tarih', 'doktor__poliklinik')
    actions = [izin_onayla, izin_reddet] # Admin panelindeki eylemler menüsüne butonları ekler
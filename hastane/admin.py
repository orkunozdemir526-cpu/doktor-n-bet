from django.contrib import admin
from .models import Poliklinik, Doktor, Nobet, NobetTakas, IzinTalebi
from django.contrib.admin.models import LogEntry


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


# ==============================================================================
# ANA PANEL BİLGİ KARTLARI İÇİN DİNAMİK VERİ ÇEKME İŞLEMİ
# ==============================================================================

# Django'nun orijinal admin ana sayfasını yakalıyoruz
orijinal_index = admin.site.index

def gelismis_index(request, extra_context=None):
    extra_context = extra_context or {}
    
    # Kendi doğru model isimlerimizle veritabanından sayıları çekiyoruz
    try:
        extra_context['gercek_doktor_sayisi'] = Doktor.objects.count()
        extra_context['gercek_poliklinik_sayisi'] = Poliklinik.objects.count()
        extra_context['gercek_nobet_sayisi'] = Nobet.objects.count()
        extra_context['gercek_takas_sayisi'] = NobetTakas.objects.count() # Senin model adın!
    except Exception as e:
        pass # Veritabanı henüz hazır değilse çökmesini engeller
    
    # İçine gerçek verilerimizi koyduğumuz paketi orijinal sayfaya gönderiyoruz
    return orijinal_index(request, extra_context)

# Django'ya "Artık benim gelişmiş ana sayfamı kullan" diyoruz
admin.site.index = gelismis_index

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # Ekranda hangi sütunlar görünecek?
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    
    # Sağ taraftaki "SÜZ" (Filtre) menüsü neleri içerecek?
    list_filter = ('action_time', 'user', 'content_type')
    
    # Arama çubuğu nelerde arama yapacak?
    search_fields = ('object_repr', 'change_message')
    
    # Başhekim dahil KİMSE geçmişi değiştiremesin diye her şeyi salt-okunur (readonly) yapıyoruz
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')

    # Güvenlik Kilidi 1: Kimse sahte log ekleyemez
    def has_add_permission(self, request):
        return False

    # Güvenlik Kilidi 2: Kimse geçmiş logları düzenleyemez (örtbas edemez)
    def has_change_permission(self, request, obj=None):
        return False

    # Güvenlik Kilidi 3: Kimse geçmişi silemez (kanıt yok etme engeli)
    def has_delete_permission(self, request, obj=None):
        return False
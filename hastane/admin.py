from django.contrib import admin
from .models import Poliklinik, Doktor, Nobet, NobetTakas, IzinTalebi ,ResmiTatil , NobetHavuzu, NobetTercihi, Duyuru
from django.contrib.admin.models import LogEntry
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
# 🌟 İŞTE KRİTİK DEĞİŞİKLİK BURADA: UserCreationForm yerine AdminUserCreationForm kullanıyoruz 🌟
from django.contrib.auth.forms import AdminUserCreationForm
from django import forms

# =========================================================
# 🌟 DOKTOR (KULLANICI) EKLEME EKRANI ÖZELLEŞTİRMESİ 🌟
# =========================================================

# 1. Yeni Kayıt Formunu Hazırlıyoruz
class GelismisKullaniciEklemeFormu(AdminUserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="Adı")
    last_name = forms.CharField(max_length=30, required=True, label="Soyadı")
    email = forms.EmailField(max_length=254, required=True, label="E-posta adresi")

    class Meta(AdminUserCreationForm.Meta):
        model = User
        # Django'nun admin alanlarını koruyup üzerine bizimkileri ekliyoruz:
        fields = AdminUserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')


# 2. Django'nun Varsayılan Kullanıcı Panelini Yeniden Tasarlıyoruz
class GelismisUserAdmin(UserAdmin):
    add_form = GelismisKullaniciEklemeFormu
    
    # Yeni eklediğimiz alanları admin paneline (add_view) yerleştiriyoruz
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Kişisel Bilgiler (Zorunlu)', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
    )

# 3. Eski (Eksik) Paneli Silip, Yeni Jilet Gibi Panelimizi Kaydediyoruz
admin.site.unregister(User)
admin.site.register(User, GelismisUserAdmin)

@admin.register(NobetTercihi)
class NobetTercihiAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'olusturulma_tarihi')
    list_filter = ('tarih', 'doktor')
    search_fields = ('doktor__kullanici__first_name', 'doktor__kullanici__last_name')

@admin.register(NobetHavuzu)
class NobetHavuzuAdmin(admin.ModelAdmin):
    list_display = ('nobet', 'olusturan_doktor', 'durum', 'olusturulma_tarihi')
    list_filter = ('durum', 'olusturulma_tarihi')
    search_fields = ('olusturan_doktor__kullanici__first_name',)

@admin.register(ResmiTatil)
class ResmiTatilAdmin(admin.ModelAdmin):
    list_display = ('isim', 'tarih', 'carpan_etkisi')
    list_filter = ('carpan_etkisi',)
    search_fields = ('isim',)
    date_hierarchy = 'tarih'

@admin.register(Poliklinik)
class PoliklinikAdmin(admin.ModelAdmin):
    list_display = ('isim',)
    search_fields = ('isim',)

@admin.register(Doktor)
class DoktorAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'poliklinik', 'kidem', 'telefon', 'telegram_chat_id', 'kalan_izin_hakki') # Telegram ve izin hakkı alanlarını da ekledik
    list_filter = ('poliklinik', 'kidem')
    search_fields = ('kullanici__first_name', 'kullanici__last_name')

@admin.register(Nobet)
class NobetAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'bolum', 'baslangic_saati', 'bitis_saati')
    list_filter = ('tarih', 'bolum', 'doktor__poliklinik')
    date_hierarchy = 'tarih'
    change_list_template = "admin/hastane/nobet_changelist.html"
    # 🌟 YENİ EKLENEN: MANUEL EKLENTİLERDE MAİL ATMA 🌟
    def save_model(self, request, obj, form, change):
        # Kayıt veritabanına yazılmadan önce, bunun "Yeni" bir kayıt mı yoksa 
        # sadece bir "Güncelleme" mi olduğunu anlıyoruz:
        yeni_kayit_mi = obj.pk is None 
        
        # Önce Django'nun kendi normal kaydetme işlemini yapmasına izin veriyoruz:
        super().save_model(request, obj, form, change)
        
        # Eğer bu yepyeni bir kayıt ise ve doktorun mail adresi varsa:
        if yeni_kayit_mi and obj.doktor.kullanici.email:
            giris_linki = "http://127.0.0.1:8000/hastane/giris/"
            mesaj = f"Merhaba Dr. {obj.doktor.kullanici.first_name},\n\n"
            mesaj += f"Başhekimlik tarafından {obj.tarih.strftime('%d.%m.%Y')} tarihi için [{obj.get_bolum_display()}] bölümüne manuel olarak yeni bir nöbetiniz eklenmiştir.\n\n"
            mesaj += f"Sisteme Giriş Yapmak İçin Tıklayın:\n{giris_linki}\n\n"
            mesaj += "İyi çalışmalar dileriz,\nHastane Yönetimi"

            try:
                send_mail(
                    subject='⚠️ Yeni Nöbet Ataması (Başhekimlik)',
                    message=mesaj,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.doktor.kullanici.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Manuel nöbet maili gönderilirken hata: {e}")

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
    

    # =========================================================
# 🏖️ İZİN TALEPLERİ AKILLI YÖNETİM PANELİ VE BUTONLARI 🏖️
# =========================================================
@admin.register(IzinTalebi)
class IzinTalebiAdmin(admin.ModelAdmin):
    list_display = ('doktor', 'tarih', 'durum')
    list_filter = ('durum', 'tarih')
    
    # Kendi yazdığımız akıllı butonları Eylemler menüsüne ekliyoruz
    actions = ['secilenleri_onayla', 'secilenleri_reddet']

    @admin.action(description='✔️ Seçili İzin Taleplerini Onayla')
    def secilenleri_onayla(self, request, queryset):
        basarili_islem = 0
        for izin in queryset:
            if izin.durum != 'onaylandi': 
                izin.durum = 'onaylandi'
                izin.save() 
                basarili_islem += 1
        
        # Başarı mesajını da resmi bir dile çevirdik
        self.message_user(request, f"✅ {basarili_islem} adet izin talebi başarıyla onaylandı ve ilgili personellerin yıllık izin hakları güncellendi.")

    @admin.action(description='❌ Seçili İzin Taleplerini Reddet / İptal Et')
    def secilenleri_reddet(self, request, queryset):
        basarili_islem = 0
        for izin in queryset:
            if izin.durum != 'reddedildi':
                izin.durum = 'reddedildi'
                izin.save() 
                basarili_islem += 1
                
        # Başarı mesajını resmi bir dile çevirdik
        self.message_user(request, f"⚠️ {basarili_islem} adet izin talebi reddedildi ve yıllık izin hakları yeniden düzenlendi.")

        # 📢 DUYURU PANELİ KAYDI
@admin.register(Duyuru)
class DuyuruAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'oncelik', 'tarih', 'aktif_mi')
    list_filter = ('aktif_mi', 'oncelik')
    search_fields = ('baslik', 'mesaj')
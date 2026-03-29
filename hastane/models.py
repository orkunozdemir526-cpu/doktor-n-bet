from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.db.models import F

# 1. Poliklinik (Bölüm) Modeli
class Poliklinik(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Poliklinik Adı")
    
    class Meta:
        verbose_name = "Poliklinik"
        verbose_name_plural = "Poliklinikler"

    def __str__(self):
        return self.isim

# 2. Doktor Modeli (Kıdem eklendi!)
class Doktor(models.Model):
    class Kidem(models.TextChoices):
        ACEMI = 'ACEMI', 'Acemi'
        ORTA_KIDEMLI = 'ORTA_KIDEMLI', 'Orta Kıdemli'
        KIDEMLI = 'KIDEMLI', 'Kıdemli'

        

    kullanici = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hastane_doktor_profili')
    poliklinik = models.ForeignKey(Poliklinik, on_delete=models.SET_NULL, null=True, verbose_name="Bölümü")
    telefon = models.CharField(max_length=15, blank=True, null=True)
    kidem = models.CharField(max_length=20, choices=Kidem.choices, default=Kidem.ACEMI, verbose_name="Kıdem")
    
    class Meta:
        verbose_name = "Doktor"
        verbose_name_plural = "Doktorlar"
# 🌟 YENİ EKLENEN TELEGRAM ALANI 🌟
    telegram_chat_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Telegram bildirimleri için doktorun Chat ID numarası"
    )

    # 🌟 YENİ EKLENEN İZİN BAKİYESİ 🌟
    kalan_izin_hakki = models.IntegerField(
        default=20, 
        verbose_name="Kalan İzin Hakkı (Gün)",
        help_text="Doktorun bu yıl kullanabileceği toplam izin günü sayısı"
    )


    def __str__(self):
        ad_soyad = f"{self.kullanici.first_name} {self.kullanici.last_name}".strip()
        if ad_soyad:
            return f"Dr. {ad_soyad} ({self.get_kidem_display()})"
        return f"Dr. {self.kullanici.username}"

# 3. Nöbet Modeli (Alan/Bölüm eklendi!)
class Nobet(models.Model):
    class Bolum(models.TextChoices):
        YESIL = 'YESIL', 'Yeşil Alan'
        SARI = 'SARI', 'Sarı Alan'
        KIRMIZI = 'KIRMIZI', 'Kırmızı Alan'
        YEDEK = 'YEDEK', 'Yedek/Diğer'

    doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name='nobetler')
    tarih = models.DateField(verbose_name="Nöbet Tarihi")
    baslangic_saati = models.TimeField(default="08:00")
    bitis_saati = models.TimeField(default="08:00")
    bolum = models.CharField(max_length=20, choices=Bolum.choices, default=Bolum.YESIL, verbose_name="Atandığı Bölüm")
    
    class Meta:
        verbose_name = "Nöbet"
        verbose_name_plural = "Nöbetler"

    def __str__(self):
        return f"{self.doktor} | {self.tarih} [{self.get_bolum_display()}]"
    def clean(self):
        super().clean() # Önce Django'nun kendi temel kontrollerini çalıştır

        # Eğer tarih veya doktor seçilmemişse boşuna kontrol etme (zaten hata verecektir)
        if not self.doktor or not self.tarih:
            return

        # KURAL 1: AYNI GÜN ÇİFTE NÖBET KONTROLÜ
        # Bu doktorun aynı gün başka bir nöbeti var mı? (Kendisi hariç - güncelleme yapıyorsak diye)
        ayni_gun_nobet = Nobet.objects.filter(doktor=self.doktor, tarih=self.tarih).exclude(pk=self.pk)
        if ayni_gun_nobet.exists():
            raise ValidationError(f"⛔ İŞLEM İPTAL EDİLDİ: {self.doktor.kullanici.get_full_name()} adlı doktorun {self.tarih} tarihinde zaten bir nöbeti bulunuyor!")

        # KURAL 2: İZİNLİ GÜNE NÖBET YAZMA KONTROLÜ
        # İzinTalebi modelini kontrol et (Eğer senin izin modelinin adı farklıysa burayı düzelt)
        from .models import IzinTalebi # Dosya içinden modeli çağırıyoruz
        izinli_mi = IzinTalebi.objects.filter(doktor=self.doktor, tarih=self.tarih, durum='onaylandi').exists()
        if izinli_mi:
            raise ValidationError(f"⛔ İŞLEM İPTAL EDİLDİ: {self.doktor.kullanici.get_full_name()} adlı doktor {self.tarih} tarihinde İZİNLİ olduğu için nöbet yazılamaz!")

        # KURAL 3: DİNLENME KURALI (ÜST ÜSTE NÖBET)
        dun = self.tarih - timedelta(days=1)
        yarin = self.tarih + timedelta(days=1)
        ardisik_nobet = Nobet.objects.filter(doktor=self.doktor, tarih__in=[dun, yarin]).exclude(pk=self.pk).exists()
        
        if ardisik_nobet:
            raise ValidationError(f"⚠️ DİKKAT (DİNLENME KURALI): {self.doktor.kullanici.get_full_name()} adlı doktorun bir gün önce veya bir gün sonra zaten nöbeti var! Üst üste nöbet yazılamaz.")

# ... (Aşağıdaki NobetTakas modeli kodlarınız aynen kalabilir) ...

# 4. Nöbet Takas Modülü
class NobetTakas(models.Model):
    DURUM_SECENEKLERI = (
        ('beklemede', 'Beklemede'),
        ('onaylandi', 'Onaylandı'),
        ('reddedildi', 'Reddedildi'),
        ('iptal', 'İptal Edildi'),
    )
    aciklama = models.TextField(blank=True, null=True, help_text="Takas için mazeret veya not")

    class Meta:
        verbose_name = "Nöbet Takas Talebi"
        verbose_name_plural = "Nöbet Takas Talepleri"

    def __str__(self):
        return f"Takas: {self.talep_eden_doktor} -> {self.hedef_doktor} ({self.get_durum_display()})"

    # Takası başlatan kişi ve vermek istediği nöbet
    talep_eden_doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name='yaptigim_talepler')
    verilecek_nobet = models.ForeignKey(Nobet, on_delete=models.CASCADE, related_name='takasa_cikan_nobet')
    
    # Takas teklif edilen kişi ve (eğer karşılığında nöbet alınacaksa) o kişinin nöbeti
    hedef_doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name='bana_gelen_talepler')
    alinacak_nobet = models.ForeignKey(Nobet, on_delete=models.CASCADE, related_name='karsilik_istenen_nobet', null=True, blank=True)
    
    # Talebin durumu ve ne zaman oluşturulduğu
    durum = models.CharField(max_length=15, choices=DURUM_SECENEKLERI, default='beklemede')
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    aciklama = models.TextField(blank=True, null=True, help_text="Takas için mazeret veya not")

    def __str__(self):
        return f"Takas: {self.talep_eden_doktor} -> {self.hedef_doktor} ({self.get_durum_display()})"
    def clean(self):
        super().clean()
        if self.talep_eden_doktor and self.hedef_doktor:
            if self.talep_eden_doktor.poliklinik != self.hedef_doktor.poliklinik:
                raise ValidationError("HATA: Sadece kendi polikliniğinizdeki doktorlarla nöbet takası yapabilirsiniz!")
        
        # KURAL 1: Verilecek nöbet, talep eden doktora mı ait?
        if self.verilecek_nobet and self.talep_eden_doktor:
            if self.verilecek_nobet.doktor != self.talep_eden_doktor:
                raise ValidationError({
                    'verilecek_nobet': 'HATA: Sadece kendi nöbetinizi takasa sunabilirsiniz!'
                })

        # KURAL 2: Alınacak nöbet, hedef doktora mı ait? (Eğer bir nöbet seçilmişse)
        if self.alinacak_nobet and self.hedef_doktor:
            if self.alinacak_nobet.doktor != self.hedef_doktor:
                raise ValidationError({
                    'alinacak_nobet': 'HATA: Almak istediğiniz nöbet, seçtiğiniz hedef doktora ait olmalıdır!'
                })
    class Meta:
        verbose_name = "Nöbet Takas Talebi"
        verbose_name_plural = "Nöbet Takas Talepleri"

    def __str__(self):
        return f"Takas: {self.talep_eden_doktor} -> {self.hedef_doktor} ({self.get_durum_display()})"
    # hastane/models.py dosyasının en altına ekleyin:

class IzinTalebi(models.Model):
    DURUM_SECENEKLERI = (
        ('beklemede', 'Beklemede (Onay Bekliyor)'),
        ('onaylandi', 'Onaylandı'),
        ('reddedildi', 'Reddedildi'),
    )
    
    doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name="izin_talepleri")
    tarih = models.DateField(verbose_name="İzin İstenen Tarih")
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='beklemede', verbose_name="Durum")

    class Meta:
        verbose_name = "İzin Talebi"
        verbose_name_plural = "İzin Talepleri"
        unique_together = ('doktor', 'tarih')

    def __str__(self):
        return f"{self.doktor} - İzin: {self.tarih} ({self.get_durum_display()})"

    # 🌟 1. AŞAMA: KONTROL MERKEZİ 🌟
    def clean(self):
        eski_durum = None
        if self.pk:
            eski_durum = IzinTalebi.objects.get(pk=self.pk).durum
            
        if self.durum == 'onaylandi' and eski_durum != 'onaylandi':
            guncel_doktor = Doktor.objects.get(pk=self.doktor.pk)
            if guncel_doktor.kalan_izin_hakki <= 0:
                raise ValidationError({'durum': f"⚠️ Dr. {guncel_doktor.kullanici.get_full_name()} için yeterli izin hakkı bulunmamaktadır! (Kalan Bakiye: 0 Gün)"})
        super().clean()

    # 🌟 2. AŞAMA: MATEMATİK MERKEZİ (Doğrudan SQL Müdahalesi) 🌟
    # IzinTalebi modeli içindeki save() fonksiyonunun güncellenmiş hali:
    def save(self, *args, **kwargs):
        eski_durum = None
        if self.pk:
            eski_durum = IzinTalebi.objects.get(pk=self.pk).durum

        # 1. Önce izin kaydını veritabanına kaydediyoruz
        super().save(*args, **kwargs)

        # 2. Eğer durum değişmişse işlemleri tetikle
        if eski_durum != self.durum:
            
            # SENARYO A: İzin Yeni Onaylandıysa (Bakiyeden Düş ve Bildirim At)
            if self.durum == 'onaylandi':
                Doktor.objects.filter(pk=self.doktor.pk).update(kalan_izin_hakki=F('kalan_izin_hakki') - 1)
                Bildirim.objects.create(doktor=self.doktor, mesaj=f"🏖️ {self.tarih.strftime('%d.%m.%Y')} tarihli yıllık izin talebiniz Başhekimlik tarafından ONAYLANDI.")
                
            # SENARYO B: Önceden Onaylı Bir İzin İptal/Red Ediliyorsa (Bakiyeyi Geri Ver)
            elif eski_durum == 'onaylandi':
                Doktor.objects.filter(pk=self.doktor.pk).update(kalan_izin_hakki=F('kalan_izin_hakki') + 1)
                
            # SENARYO C: İzin Reddedildiyse (Nereden gelirse gelsin Red Bildirimi At)
            if self.durum == 'reddedildi':
                Bildirim.objects.create(doktor=self.doktor, mesaj=f"❌ {self.tarih.strftime('%d.%m.%Y')} tarihli yıllık izin talebiniz REDDEDİLDİ.")

    # 🌟 3. AŞAMA: GÜVENLİK (Silinirse Hakkı İade Et) 🌟
    def delete(self, *args, **kwargs):
        if self.durum == 'onaylandi':
            Doktor.objects.filter(pk=self.doktor.pk).update(kalan_izin_hakki=F('kalan_izin_hakki') + 1)
        super().delete(*args, **kwargs)
    
     # =========================================================
# 🌟 YENİ SİSTEM: RESMİ TATİL VE ADALET MODÜLÜ 🌟
# =========================================================
class ResmiTatil(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Tatil Adı (Örn: Ramazan Bayramı 1. Gün)")
    tarih = models.DateField(unique=True, verbose_name="Tatil Tarihi")
    # %25 zamlı hak ediş ve x2 yıpranma puanı için bu günler referans alınacak
    carpan_etkisi = models.BooleanField(default=True, verbose_name="Maaş/Puan Çarpanı Uygulansın mı?")

    class Meta:
        verbose_name = "Resmi Tatil"
        verbose_name_plural = "Resmi Tatiller"
        ordering = ['tarih'] # Tarihe göre sıralı gelsin

    def __str__(self):
        return f"{self.isim} ({self.tarih.strftime('%d.%m.%Y')})"
    
    # =========================================================
# 🌟 YENİ SİSTEM: NÖBET HAVUZU (AÇIK PAZAR) 🌟
# =========================================================
class NobetHavuzu(models.Model):
    # Bir nöbet sadece bir kez havuza konabilir (OneToOneField)
    nobet = models.OneToOneField('Nobet', on_delete=models.CASCADE, verbose_name="Havuzdaki Nöbet")
    olusturan_doktor = models.ForeignKey('Doktor', on_delete=models.CASCADE, verbose_name="İlana Koyan Doktor")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Neden Devrediyor?")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    
    DURUM_CHOICES = (
        ('aktif', 'Havuza Açık (Bekliyor)'),
        ('alindi', 'Biri Tarafından Alındı'),
    )
    durum = models.CharField(max_length=10, choices=DURUM_CHOICES, default='aktif')

    class Meta:
        verbose_name = "Havuz İlanı"
        verbose_name_plural = "Nöbet Havuzu İlanları"
        ordering = ['-olusturulma_tarihi']

    def __str__(self):
        return f"İlan: {self.nobet.tarih} - {self.olusturan_doktor.kullanici.get_full_name()}"
    
    # =========================================================
# 🌟 AŞAMA 4: DOKTOR TERCİH (KISITLAMA) SİSTEMİ 🌟
# =========================================================
class NobetTercihi(models.Model):
    doktor = models.ForeignKey('Doktor', on_delete=models.CASCADE, verbose_name="Doktor")
    tarih = models.DateField(verbose_name="İstenmeyen Nöbet Tarihi")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nöbet Tercihi (İstenmeyen Gün)"
        verbose_name_plural = "Nöbet Tercihleri"
        ordering = ['-tarih']
        # Bir doktor aynı günü iki defa "istemiyorum" diye ekleyemesin
        unique_together = ('doktor', 'tarih')

    def __str__(self):
        return f"{self.doktor.kullanici.get_full_name()} - {self.tarih} (Nöbet İstemiyor)"

        # =========================================================
# 📢 İLETİŞİM VE BİLDİRİM SİSTEMİ MODELLERİ 🔔
# =========================================================

class Duyuru(models.Model):
    ONCELIK_SECENEKLERI = (
        ('info', 'ℹ️ Bilgi (Mavi)'),
        ('warning', '⚠️ Uyarı (Sarı)'),
        ('danger', '🚨 Acil / Önemli (Kırmızı)'),
    )
    
    baslik = models.CharField(max_length=150, verbose_name="Duyuru Başlığı")
    mesaj = models.TextField(verbose_name="Duyuru İçeriği")
    oncelik = models.CharField(max_length=20, choices=ONCELIK_SECENEKLERI, default='info', verbose_name="Önem Derecesi")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Yayınlanma Tarihi")
    aktif_mi = models.BooleanField(default=True, verbose_name="Yayında mı?")

    class Meta:
        verbose_name = "Başhekimlik Duyurusu"
        verbose_name_plural = "Başhekimlik Duyuruları"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.get_oncelik_display()} - {self.baslik}"

class Bildirim(models.Model):
    doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name="bildirimler")
    mesaj = models.CharField(max_length=255)
    okundu_mu = models.BooleanField(default=False)
    tarih = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.doktor} - {self.mesaj}"
    
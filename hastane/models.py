from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta

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
    
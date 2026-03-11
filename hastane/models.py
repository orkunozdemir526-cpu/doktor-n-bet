from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# 1. Poliklinik (Bölüm) Modeli
class Poliklinik(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Poliklinik Adı")
    
    class Meta:
        verbose_name = "Poliklinik"
        verbose_name_plural = "Poliklinikler" # Sol menüde görünecek çoğul isim

    def __str__(self):
        return self.isim

# 2. Doktor Modeli (Django'nun varsayılan User modeli ile eşleşir)
class Doktor(models.Model):
    kullanici = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hastane_doktor_profili')
    poliklinik = models.ForeignKey(Poliklinik, on_delete=models.SET_NULL, null=True, verbose_name="Bölümü")
    telefon = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        verbose_name = "Doktor"
        verbose_name_plural = "Doktorlar"

    def __str__(self):
        ad_soyad = f"{self.kullanici.first_name} {self.kullanici.last_name}".strip()
        if ad_soyad:
            return f"Dr. {ad_soyad}"
        return f"Dr. {self.kullanici.username}"
# 3. Nöbet Modeli
class Nobet(models.Model):
    doktor = models.ForeignKey(Doktor, on_delete=models.CASCADE, related_name='nobetler')
    tarih = models.DateField(verbose_name="Nöbet Tarihi")
    baslangic_saati = models.TimeField(default="08:00")
    bitis_saati = models.TimeField(default="08:00")
    
    class Meta:
        verbose_name = "Nöbet"
        verbose_name_plural = "Nöbetler"

    def __str__(self):
        return f"{self.doktor} | {self.tarih}"

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
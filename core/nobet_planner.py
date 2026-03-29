import calendar
from collections import defaultdict
from datetime import date, timedelta
import random

from .models import Doktor, Nobet, IzinTalebi, HastaneAyarlari, ResmiTatil # ResmiTatil eklendi

class NobetPlanlayici:
    def __init__(self, yil, ay):
        self.yil = yil
        self.ay = ay
        self.ay_gun_sayisi = calendar.monthrange(yil, ay)[1]
        self.plan_tarihleri = [date(yil, ay, gun) for gun in range(1, self.ay_gun_sayisi + 1)]

        self.ayarlar = HastaneAyarlari.get_solo()
        self.doktorlar = list(Doktor.objects.all())
        self.izinler = self._get_izinler()
        
        # O ayki resmi tatilleri alıyoruz (Örn: [date(2026,4,23), date(2026,4,24)])
        self.resmi_tatiller = list(ResmiTatil.objects.filter(tarih__year=yil, tarih__month=ay).values_list('tarih', flat=True))
        
        self.hedef_nobet_sayisi = 7

        self.nobet_gecmisi = defaultdict(list)
        self.nobet_sayilari = defaultdict(int)
        
        # Yeni: Kim kaç kere tatil nöbeti tutmuş? (Sene başından beri sayar)
        self.tatil_nobet_sayilari = self._get_gecmis_tatil_nobetleri()
        
        self.zorunlu_atama_kaydi = defaultdict(list)

    def _get_izinler(self):
        izinler = defaultdict(list)
        qs = IzinTalebi.objects.filter(tarih__year=self.yil, tarih__month=self.ay)
        for izin in qs:
            izinler[izin.tarih].append(izin.doktor_id)
        return izinler

    # Yeni Fonksiyon: Doktorların sene başından beri tuttukları tatil nöbetlerini hesaplar
    def _get_gecmis_tatil_nobetleri(self):
        tatil_nobeti_sayaci = defaultdict(int)
        gecmis_tatiller = ResmiTatil.objects.filter(tarih__year=self.yil).values_list('tarih', flat=True)
        gecmis_nobetler = Nobet.objects.filter(tarih__in=gecmis_tatiller)
        
        for nobet in gecmis_nobetler:
            tatil_nobeti_sayaci[nobet.doktor_id] += 1
        return tatil_nobeti_sayaci

    def _get_gunun_uygun_doktorlari(self, gunun_tarihi, havuz):
        uygun_doktorlar = []
        izinli_doktor_idler = self.izinler.get(gunun_tarihi, [])
        for dr in havuz:
            if dr.id in izinli_doktor_idler and havuz is self.doktorlar: continue
            son_nobet_tarihi = self.nobet_gecmisi.get(dr.id, [])[-1] if self.nobet_gecmisi.get(dr.id) else None
            if son_nobet_tarihi:
                gun_farki = (gunun_tarihi - son_nobet_tarihi).days
                if gun_farki <= self.ayarlar.minimum_dinlenme_gunu: continue
            uygun_doktorlar.append(dr)
        return uygun_doktorlar
    
    # Skorlama sistemi Tatil günlerine göre akıllandı!
    def _takim_skorla(self, takim, gunun_tarihi):
        skor = 0
        bugun_tatil_mi = gunun_tarihi in self.resmi_tatiller

        for dr in takim:
            # EĞER BUGÜN RESMİ TATİLSE:
            if bugun_tatil_mi:
                tatil_skoru = self.tatil_nobet_sayilari.get(dr.id, 0)
                # Geçmişte tatil nöbeti tutanlara DEVASA bir ceza puanı ver ki algoritma onları seçmesin
                skor += tatil_skoru * 10000 
            
            # NORMAL NÖBET SKORLAMASI
            nobet_sayisi = self.nobet_sayilari.get(dr.id, 0)
            if nobet_sayisi < self.hedef_nobet_sayisi:
                skor += nobet_sayisi * 10
            else:
                skor += 1000 + (nobet_sayisi * 10)
            
            # DİNLENME BONUSU (Çok dinlenen öne çıksın)
            son_nobet = self.nobet_gecmisi.get(dr.id, [])[-1] if self.nobet_gecmisi.get(dr.id) else None
            if son_nobet:
                gun_farki = (gunun_tarihi - son_nobet).days
                skor -= gun_farki
        return skor

    def _takim_gecerli_mi(self, takim):
        kidemler = [dr.kidem for dr in takim]
        if Doktor.Kidem.ACEMI in kidemler and Doktor.Kidem.KIDEMLI not in kidemler: return False
        return True

    def plani_olustur(self):
        olusturulan_plan = []
        for gunun_tarihi in self.plan_tarihleri:
            normal_adaylar = self._get_gunun_uygun_doktorlari(gunun_tarihi, self.doktorlar)
            aday_havuzu = normal_adaylar
            eksik_doktor_sayisi = self.ayarlar.gunluk_doktor_sayisi - len(aday_havuzu)

            if eksik_doktor_sayisi > 0:
                print(f"UYARI: {gunun_tarihi} için {eksik_doktor_sayisi} doktor eksik. Zorunlu atama denenecek.")
                izinli_doktorlar = [dr for dr in self.doktorlar if dr.id in self.izinler.get(gunun_tarihi, [])]
                acil_durum_adaylari = self._get_gunun_uygun_doktorlari(gunun_tarihi, izinli_doktorlar)
                if len(acil_durum_adaylari) >= eksik_doktor_sayisi:
                    zorunlu_atananlar = random.sample(acil_durum_adaylari, eksik_doktor_sayisi)
                    aday_havuzu.extend(zorunlu_atananlar)
                    self.zorunlu_atama_kaydi[gunun_tarihi] = [dr.id for dr in zorunlu_atananlar]
                else:
                    print(f"KRİTİK HATA: {gunun_tarihi} için izinliler dahil yeterli doktor yok!")
                    continue

            if len(aday_havuzu) < self.ayarlar.gunluk_doktor_sayisi:
                print(f"KRİTİK HATA: {gunun_tarihi} için aday havuzu hala yetersiz!")
                continue

            gecerli_takimlar = []
            for _ in range(500): 
                aday_takim = random.sample(aday_havuzu, self.ayarlar.gunluk_doktor_sayisi)
                if self._takim_gecerli_mi(aday_takim):
                    # Skorlama fonksiyonuna artık 'gunun_tarihi' bilgisini de gönderiyoruz ki tatil mi bilsin
                    skor = self._takim_skorla(aday_takim, gunun_tarihi)
                    gecerli_takimlar.append((skor, aday_takim))
            
            if not gecerli_takimlar:
                print(f"UYARI: {gunun_tarihi} için geçerli bir takım oluşturulamadı!")
                continue

            gecerli_takimlar.sort(key=lambda x: x[0])
            en_iyi_takim = gecerli_takimlar[0][1]

            olusturulan_plan.append((gunun_tarihi, en_iyi_takim))
            for dr in en_iyi_takim:
                self.nobet_sayilari[dr.id] += 1
                self.nobet_gecmisi[dr.id].append(gunun_tarihi)
                # Eğer bugün tatilse, tatil sayacını da 1 artır
                if gunun_tarihi in self.resmi_tatiller:
                    self.tatil_nobet_sayilari[dr.id] += 1

        return olusturulan_plan
    
    def _bolumlere_ata(self, takim):
        kidem_siralamasi = {Doktor.Kidem.KIDEMLI: 3, Doktor.Kidem.ORTA_KIDEMLI: 2, Doktor.Kidem.ACEMI: 1}
        takim.sort(key=lambda dr: kidem_siralamasi[dr.kidem], reverse=True)
        
        atama = {
            Nobet.Bolum.KIRMIZI: [],
            Nobet.Bolum.SARI: [],
            Nobet.Bolum.YESIL: [],
        }

        k_sayi = self.ayarlar.kirmizi_alan_doktor_sayisi
        s_sayi = self.ayarlar.sari_alan_doktor_sayisi

        atama[Nobet.Bolum.KIRMIZI] = takim[0:k_sayi]
        atama[Nobet.Bolum.SARI] = takim[k_sayi : k_sayi + s_sayi]
        atama[Nobet.Bolum.YESIL] = takim[k_sayi + s_sayi :]
        
        return atama

    def plani_kaydet(self, plan):
        Nobet.objects.filter(tarih__year=self.yil, tarih__month=self.ay).delete()
        print(f"{self.yil}-{self.ay} dönemine ait eski nöbetler silindi.")

        nobet_listesi = []
        for tarih, takim in plan:
            atama = self._bolumlere_ata(takim)
            for bolum, doktorlar_listesi in atama.items():
                for dr in doktorlar_listesi: 
                    if not dr: continue
                    is_zorunlu = dr.id in self.zorunlu_atama_kaydi.get(tarih, [])
                    nobet_listesi.append(Nobet(doktor=dr, tarih=tarih, bolum=bolum, izin_iptal_edildi=is_zorunlu))

        Nobet.objects.bulk_create(nobet_listesi)
        print(f"{len(nobet_listesi)} adet yeni nöbet başarıyla veritabanına kaydedildi.")
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse # HttpResponse eklendi
from datetime import datetime, timedelta, time
import pandas as pd # Excel için eklendi
import io           # Excel için eklendi
from .models import Doktor, Nobet, NobetTakas, Poliklinik, IzinTalebi, NobetHavuzu, NobetTercihi, Duyuru, Bildirim, ResmiTatil
from .forms import TakasTalebiForm
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
import requests
import math
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from decimal import Decimal
import threading

# 🌟 SİHİRLİ ASİSTAN: Mailleri arka planda (doktoru bekletmeden) gönderir
def arka_planda_mail_gonder(subject, message, recipient_list):
    def mail_motoru():
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Arka plan mail hatası: {e}")

    # İşlemi ana sistemden ayırıp arka planda bağımsız bir iş parçacığı (Thread) olarak başlat
    t = threading.Thread(target=mail_motoru)
    t.start()

# 1. DOKTOR KONTROL PANELİ
@login_required(login_url='/hastane/giris/')
def doktor_paneli(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
        bugun = timezone.now().date() # Sistemin şu anki tarihini alıyoruz
        
        # --- İzin ve Tercih ekleme kısmı ---
        if request.method == 'POST':
            if 'izin_tarih' in request.POST:
                tarih_str = request.POST.get('izin_tarih')
                izin_tarihi = datetime.strptime(tarih_str, '%Y-%m-%d').date()
                
                # 🌟 GEÇMİŞ ZAMAN KONTROLÜ
                if izin_tarihi < bugun:
                    messages.error(request, "❌ Hata: Geçmiş bir tarih için izin talebinde bulunamazsınız!")
                elif not IzinTalebi.objects.filter(doktor=doktor, tarih=izin_tarihi).exists():
                    IzinTalebi.objects.create(doktor=doktor, tarih=izin_tarihi)
                    messages.success(request, "🏖️ İzin talebiniz Başhekime iletildi!")
                return redirect('doktor_paneli')
                
            # YENİ EKLENEN TERCİH KISMI
            elif 'tercih_tarih' in request.POST:
                tarih_str = request.POST.get('tercih_tarih')
                tercih_tarihi = datetime.strptime(tarih_str, '%Y-%m-%d').date()
                
                # 🌟 GEÇMİŞ ZAMAN KONTROLÜ
                if tercih_tarihi < bugun:
                    messages.error(request, "❌ Hata: Geçmiş bir tarihi kısıtlayamazsınız!")
                elif not NobetTercihi.objects.filter(doktor=doktor, tarih=tercih_tarihi).exists():
                    NobetTercihi.objects.create(doktor=doktor, tarih=tercih_tarihi)
                    messages.success(request, f"🛑 {tarih_str} tarihi için nöbet kısıtlamanız kaydedildi.")
                return redirect('doktor_paneli')

        # 🌟 YENİ: ZAMAN FİLTRESİ - SADECE BUGÜN VE GELECEKTEKİ NÖBET/TAKASLARI GETİR
        nobetler = Nobet.objects.filter(doktor=doktor, tarih__gte=bugun).order_by('tarih')
        giden_talepler = NobetTakas.objects.filter(talep_eden_doktor=doktor, verilecek_nobet__tarih__gte=bugun).order_by('-olusturulma_tarihi')
        gelen_talepler = NobetTakas.objects.filter(hedef_doktor=doktor, verilecek_nobet__tarih__gte=bugun).order_by('-olusturulma_tarihi')
        
        izinler = IzinTalebi.objects.filter(doktor=doktor).order_by('tarih')
        tercihler = NobetTercihi.objects.filter(doktor=doktor).order_by('tarih')

        # --- İSTATİSTİK HESAPLAMA ---
        yesil_sayisi = nobetler.filter(bolum='YESIL').count()
        sari_sayisi = nobetler.filter(bolum='SARI').count()
        kirmizi_sayisi = nobetler.filter(bolum='KIRMIZI').count()
        toplam_nobet = yesil_sayisi + sari_sayisi + kirmizi_sayisi

        duyurular = Duyuru.objects.filter(aktif_mi=True)
        bildirimler = Bildirim.objects.filter(doktor=doktor, okundu_mu=False)
        bildirim_sayisi = bildirimler.count()

    except Doktor.DoesNotExist:
        # Eğer giren kişi doktor değilse (Örn: Süper Admin) çökmeyi engellemek için boş değerler atıyoruz
        doktor, nobetler, giden_talepler, gelen_talepler, izinler, tercihler = None, [], [], [], [], []
        yesil_sayisi = sari_sayisi = kirmizi_sayisi = toplam_nobet = 0
        duyurular = Duyuru.objects.filter(aktif_mi=True) # Admin de duyuruları görsün
        bildirimler = []
        bildirim_sayisi = 0

    context = {
        'doktor': doktor, 
        'nobetler': nobetler, 
        'giden_talepler': giden_talepler, 
        'gelen_talepler': gelen_talepler, 
        'izinler': izinler,
        'tercihler': tercihler, 
        'yesil_sayisi': yesil_sayisi,
        'sari_sayisi': sari_sayisi,
        'kirmizi_sayisi': kirmizi_sayisi,
        'toplam_nobet': toplam_nobet,
        'duyurular': duyurular,             
        'bildirimler': bildirimler,         
        'bildirim_sayisi': bildirim_sayisi, 
    }
    return render(request, 'hastane/doktor_paneli.html', context)

@login_required(login_url='/hastane/giris/')
def izin_sil(request, izin_id):
    # Sadece kendi iznini silebilmesi için güvenlik önlemi
    izin = get_object_or_404(IzinTalebi, id=izin_id, doktor__kullanici=request.user)
    izin.delete()
    return redirect('doktor_paneli')

# 2. YENİ TAKAS TALEBİ OLUŞTURMA
# 2. YENİ TAKAS TALEBİ OLUŞTURMA
@login_required(login_url='/hastane/giris/')
def takas_olustur(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
    except Doktor.DoesNotExist:
        return redirect('doktor_paneli')

    if request.method == 'POST':
        form = TakasTalebiForm(request.POST, doktor=doktor)
        
        form.instance.talep_eden_doktor = doktor 
        
        if form.is_valid():
            yeni_takas = form.save(commit=False)
            yeni_takas.durum = 'beklemede'
            yeni_takas.save()
            
            # 🌟 ÇÖZÜM: HTML KODU İÇERMEYEN, TEMİZ VE KISA BİLDİRİM
            istenen = f" ({yeni_takas.alinacak_nobet.tarih.strftime('%d.%m')})" if yeni_takas.alinacak_nobet else ""
            Bildirim.objects.create(
                doktor=yeni_takas.hedef_doktor, 
                mesaj=f"🔄 Dr. {doktor.kullanici.last_name} sizden takas istiyor{istenen}. Lütfen paneldeki 'Bana Gelen Talepler' kısmından yanıtlayın."
            )
            
            # --- Mail Kodları ---
            hedef_email = yeni_takas.hedef_doktor.kullanici.email
            if hedef_email: 
                giris_linki = "http://127.0.0.1:8000/hastane/giris/"
                mesaj = (f"Merhaba Dr. {yeni_takas.hedef_doktor.kullanici.first_name},\n\n"
                         f"Dr. {doktor.kullanici.first_name} {doktor.kullanici.last_name} size bir nöbet takas talebi gönderdi.\n"
                         "Lütfen doktor paneline girerek talebi onaylayın veya reddedin.\n\n"
                         f"Sisteme Giriş Yapmak İçin Tıklayın:\n{giris_linki}\n\n"
                         "İyi çalışmalar.")
                # 🌟 HIZLANDIRICI: Eski yavaş 'send_mail' yerine kendi arka plan asistanımızı çağırıyoruz!
                arka_planda_mail_gonder(
                    subject='🔔 Yeni Nöbet Takas Talebi',
                    message=mesaj,
                    recipient_list=[hedef_email]
                )
                
            messages.success(request, "🔄 Takas talebiniz başarıyla gönderildi!")
            return redirect('doktor_paneli')
        else:
            messages.error(request, "⚠️ Takas talebi oluşturulurken hata oluştu. Seçimlerinizi kontrol edin.")
    else:
        form = TakasTalebiForm(doktor=doktor)   

    return render(request, 'hastane/takas_olustur.html', {'form': form, 'doktor': doktor})

# 3. AJAX: HEDEF DOKTORUN NÖBETLERİNİ GETİRME
@login_required(login_url='/hastane/giris/')
def load_nobetler(request):
    doktor_id = request.GET.get('doktor_id')
    bugun = timezone.now().date()
    # 🌟 ZAMAN KİLİDİ EKLENDİ (tarih__gte=bugun)
    nobetler = Nobet.objects.filter(doktor_id=doktor_id, tarih__gte=bugun).order_by('tarih')
    return render(request, 'hastane/nobet_dropdown_list_options.html', {'nobetler': nobetler})

# 4. TAKAS TALEBİNE CEVAP VERME (ONAY/RED)
@login_required(login_url='/hastane/giris/')
def takas_cevapla(request, talep_id, cevap):
    doktor = get_object_or_404(Doktor, kullanici=request.user)
    talep = get_object_or_404(NobetTakas, id=talep_id, hedef_doktor=doktor)

    if talep.durum != 'beklemede':
        return redirect('doktor_paneli')

    if cevap == 'onayla':
        verilen_nobet = talep.verilecek_nobet
        verilen_nobet.doktor = talep.hedef_doktor
        verilen_nobet.save()
        messages.success(request, "✅ Takas talebini onayladınız!")

        if talep.alinacak_nobet:
            alinan_nobet = talep.alinacak_nobet
            alinan_nobet.doktor = talep.talep_eden_doktor
            alinan_nobet.save()

        talep.durum = 'onaylandi'
        talep.save()
        
        # 🌟 BİLDİRİM: Takas onaylandığında karşı tarafa bildir
        Bildirim.objects.create(
            doktor=talep.talep_eden_doktor, 
            mesaj=f"🤝 Dr. {doktor.kullanici.last_name} takas talebinizi KABUL ETTİ. ({talep.verilecek_nobet.tarih.strftime('%d.%m')})"
        )

    elif cevap == 'reddet':
        talep.durum = 'reddedildi'
        talep.save()
        messages.error(request, "❌ Takas talebini reddettiniz!") 
        
        # 🌟 BİLDİRİM: Takas reddedildiğinde karşı tarafa bildir
        Bildirim.objects.create(
            doktor=talep.talep_eden_doktor, 
            mesaj=f"❌ Dr. {doktor.kullanici.last_name} takas talebinizi REDDETTİ."
        )

    # --- MAİL GÖNDERME KISMI ---
    talep_eden_email = talep.talep_eden_doktor.kullanici.email
    if talep_eden_email:
        giris_linki = "http://127.0.0.1:8000/hastane/giris/"
        durum_yazisi = "ONAYLADI ✅" if cevap == 'onayla' else "REDDETTİ ❌"
        mesaj = f"Merhaba Dr. {talep.talep_eden_doktor.kullanici.first_name},\n\n"
        mesaj += f"Dr. {doktor.kullanici.first_name} {doktor.kullanici.last_name} nöbet takas talebinizi {durum_yazisi}.\n\n"
        mesaj += f"Sisteme Giriş Yapmak İçin Tıklayın:\n{giris_linki}\n\n"
        mesaj += "Bilginize sunar, iyi çalışmalar dileriz."
        
        send_mail(
            subject=f'Takas Talebiniz {durum_yazisi}',
            message=mesaj,
            from_email=None,
            recipient_list=[talep_eden_email],
            fail_silently=True,
        )

    return redirect('doktor_paneli')

# 5. TAKVİM İÇİN AKILLI VE RENKLİ JSON VERİSİ (SADECE KİŞİSEL NÖBETLER)
@login_required(login_url='/hastane/giris/')
def nobet_verileri_json(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
        nobetler = Nobet.objects.filter(doktor=doktor)
    except Doktor.DoesNotExist:
        nobetler = []

    nobet_listesi = []
    for nobet in nobetler:
        renk = '#007bff' 
        bolum_baslik = 'Nöbet'
        
        if hasattr(nobet, 'bolum'):
            if nobet.bolum == 'YESIL':
                renk = '#28a745'
                bolum_baslik = '🟢 Yeşil Alan'
            elif nobet.bolum == 'SARI':
                renk = '#ffc107'
                bolum_baslik = '🟡 Sarı Alan'
            elif nobet.bolum == 'KIRMIZI':
                renk = '#dc3545'
                bolum_baslik = '🔴 Kırmızı Alan'
        
        saat = nobet.baslangic_saati.strftime('%H:%M')
        aciklama = f"⏰ Saat: {saat}"

        nobet_listesi.append({
            'title': bolum_baslik,
            'start': f"{nobet.tarih.isoformat()}T{nobet.baslangic_saati.isoformat()}",
            'end': f"{nobet.tarih.isoformat()}T{nobet.bitis_saati.isoformat()}",
            'color': renk,
            'textColor': '#000' if hasattr(nobet, 'bolum') and nobet.bolum == 'SARI' else '#fff',
            'description': aciklama
        })
        
    return JsonResponse(nobet_listesi, safe=False)

# 6. OTOMATİK NÖBET PLANLAYICI ALGORİTMASI
@staff_member_required
def nobet_planla(request):
    poliklinikler = Poliklinik.objects.all()

    if request.method == 'POST':
        secilen_poliklinik_id = request.POST.get('poliklinik_id')
        baslangic_str = request.POST.get('baslangic_tarihi')
        bitis_str = request.POST.get('bitis_tarihi')
        
        meslektaslar = list(Doktor.objects.filter(poliklinik_id=secilen_poliklinik_id))
        doktor_sayisi = len(meslektaslar)

        if doktor_sayisi == 0:
             return render(request, 'hastane/nobet_planla.html', {'error': 'Bu poliklinikte kayıtlı doktor bulunamadı!', 'poliklinikler': poliklinikler})

        try:
            baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
            bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return render(request, 'hastane/nobet_planla.html', {'error': 'Geçersiz tarih.', 'poliklinikler': poliklinikler})
        
        Nobet.objects.filter(
            tarih__range=[baslangic, bitis], 
            doktor__poliklinik_id=secilen_poliklinik_id
        ).delete()
        
        gun_sayisi = (bitis - baslangic).days + 1
        current_date = baslangic
        
        doktor_nobet_sayilari = {dr: 0 for dr in meslektaslar}
        doktor_son_nobet = {dr: None for dr in meslektaslar}
        doktor_puanlari = {dr: 0.0 for dr in meslektaslar} 

        for i in range(gun_sayisi):
            musait_doktorlar = []
            izinli_doktorlar = []
            
            for dr in meslektaslar:
                if IzinTalebi.objects.filter(doktor=dr, tarih=current_date, durum='onaylandi').exists():
                    izinli_doktorlar.append(dr)
                    continue
                    
                son_nobet_tarihi = doktor_son_nobet[dr]
                if son_nobet_tarihi is None or (current_date - son_nobet_tarihi).days > 1:
                    musait_doktorlar.append(dr)
            
            if len(musait_doktorlar) < 3:
                musait_doktorlar = [dr for dr in meslektaslar if dr not in izinli_doktorlar]
            
            istenmeyen_doktorlar = [dr for dr in meslektaslar if NobetTercihi.objects.filter(doktor=dr, tarih=current_date).exists()]
            
            is_haftasonu = current_date.weekday() >= 5
            bugun_tatil_mi = ResmiTatil.objects.filter(tarih=current_date, carpan_etkisi=True).exists()
            
            if bugun_tatil_mi:
                gunun_baz_puani = 2.0  
            elif is_haftasonu:
                gunun_baz_puani = 1.5  
            else:
                gunun_baz_puani = 1.0  
            
            musait_doktorlar.sort(key=lambda x: (
                1 if x in istenmeyen_doktorlar else 0, 
                doktor_puanlari[x],                    
                doktor_nobet_sayilari[x]               
            ))
            
            kidemliler = [dr for dr in musait_doktorlar if dr.kidem == Doktor.Kidem.KIDEMLI]
            ortalar = [dr for dr in musait_doktorlar if dr.kidem == Doktor.Kidem.ORTA_KIDEMLI]
            acemiler = [dr for dr in musait_doktorlar if dr.kidem == Doktor.Kidem.ACEMI]
            
            secilen_kidemli = kidemliler[0] if kidemliler else None
            secilen_orta = ortalar[0] if ortalar else None
            secilen_acemi = acemiler[0] if acemiler else None
            
            atanan_doktorlar = []
            for secilen in [secilen_kidemli, secilen_orta, secilen_acemi]:
                if secilen:
                    atanan_doktorlar.append(secilen)
                    musait_doktorlar.remove(secilen)
                else:
                    if musait_doktorlar:
                        yedek = musait_doktorlar[0]
                        atanan_doktorlar.append(yedek)
                        musait_doktorlar.remove(yedek)
                    else:
                        atanan_doktorlar.append(None)
                    
            bolumler = [Nobet.Bolum.KIRMIZI, Nobet.Bolum.SARI, Nobet.Bolum.YESIL]
            
            for idx, secilen_doktor in enumerate(atanan_doktorlar):
                if not secilen_doktor:
                    continue
                    
                bolum = bolumler[idx]
                Nobet.objects.create(
                    doktor=secilen_doktor,
                    tarih=current_date,
                    baslangic_saati=time(8, 0),
                    bitis_saati=time(8, 0),
                    bolum=bolum
                )
                
                doktor_nobet_sayilari[secilen_doktor] += 1
                doktor_son_nobet[secilen_doktor] = current_date
                
                ekstra_kirmizi_puani = 0.5 if bolum == Nobet.Bolum.KIRMIZI else 0.0
                doktor_puanlari[secilen_doktor] += (gunun_baz_puani + ekstra_kirmizi_puani)
            
            current_date += timedelta(days=1)
            
        yeni_nobetler = Nobet.objects.filter(
            tarih__range=[baslangic, bitis], 
            doktor__poliklinik_id=secilen_poliklinik_id
        ).order_by('tarih', 'bolum')
        
        data = []
        for n in yeni_nobetler:
            ad_soyad = f"{n.doktor.kullanici.first_name} {n.doktor.kullanici.last_name}".strip()
            if not ad_soyad:
                ad_soyad = n.doktor.kullanici.username
                
            data.append({
                'Tarih': n.tarih.strftime("%d.%m.%Y"),
                'Bölüm / Alan': n.get_bolum_display(),
                'Doktor Adı Soyadı': ad_soyad,
                'Kıdemi': n.doktor.get_kidem_display(),
            })
        
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Nöbet Planı')
            worksheet = writer.sheets['Nöbet Planı']
            worksheet.column_dimensions['A'].width = 15
            worksheet.column_dimensions['B'].width = 20
            worksheet.column_dimensions['C'].width = 30
            worksheet.column_dimensions['D'].width = 15
            
        output.seek(0)
        secilen_poli = Poliklinik.objects.get(id=secilen_poliklinik_id)
        temiz_isim = secilen_poli.isim.replace(" ", "_")
        filename = f"{temiz_isim}_Otomatik_Nobet.xlsx"

        try:
            alici_listesi = [dr.kullanici.email for dr in meslektaslar if dr.kullanici.email]
            
            if alici_listesi:
                giris_linki = "http://127.0.0.1:8000/hastane/giris/"
                mesaj_icerigi = f"""Merhaba,\n\n{baslangic_str} ile {bitis_str} tarihleri arasındaki yeni nöbet programınız sisteme yüklenmiştir.\n\nLütfen sisteme giriş yaparak kendi nöbet günlerinizi kontrol ediniz.\n\nSisteme Giriş Yapmak İçin Tıklayın:\n{giris_linki}\n\nİyi çalışmalar dileriz,\nHastane Yönetimi"""

                send_mail(
                    subject=f'{secilen_poli.isim} Nöbet Programı Yayınlandı 📅',
                    message=mesaj_icerigi,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=alici_listesi,
                    fail_silently=True, 
                )
        except Exception as e:
            print(f"Toplu nöbet maili gönderilirken hata oluştu: {e}")
        
        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return render(request, 'hastane/nobet_planla.html', {'poliklinikler': poliklinikler})

# =========================================================
# 🌟 AŞAMA 1: NÖBET HAVUZU (AÇIK PAZAR) VİDEWLARI 🌟
# =========================================================

# 1. Havuzu Görüntüleme Sayfası
@login_required(login_url='/hastane/giris/')
def nobet_havuzu(request):
    doktor = get_object_or_404(Doktor, kullanici=request.user)
    bugun = timezone.now().date()
    
    # 🌟 ZAMAN FİLTRESİ: Günü geçmiş nöbetleri havuzdan gizle (nobet__tarih__gte=bugun)
    acik_ilanlar = NobetHavuzu.objects.filter(durum='aktif', nobet__tarih__gte=bugun).exclude(olusturan_doktor=doktor).order_by('nobet__tarih')
    kendi_ilanlarim = NobetHavuzu.objects.filter(olusturan_doktor=doktor, durum='aktif', nobet__tarih__gte=bugun).order_by('nobet__tarih')
    
    return render(request, 'hastane/nobet_havuzu.html', {
        'acik_ilanlar': acik_ilanlar, 
        'kendi_ilanlarim': kendi_ilanlarim,
        'doktor': doktor
    })

# 2. Doktorun Kendi Nöbetini Havuza Bırakması (Havuz fonksiyonu)
@login_required(login_url='/hastane/giris/')
def havuza_ekle(request, nobet_id):
    doktor = get_object_or_404(Doktor, kullanici=request.user)
    nobet = get_object_or_404(Nobet, id=nobet_id, doktor=doktor)
    
    if not hasattr(nobet, 'nobethavuzu'):
        NobetHavuzu.objects.create(nobet=nobet, olusturan_doktor=doktor)
        messages.success(request, "📢 Nöbetiniz başarıyla havuza ilan olarak bırakıldı!")
        
        meslektaslar = Doktor.objects.filter(poliklinik=doktor.poliklinik).exclude(pk=doktor.pk)
        
        for dr in meslektaslar:
            # 🌟 ÇÖZÜM: KISA VE HTML İÇERMEYEN BİLDİRİM
            Bildirim.objects.create(
                doktor=dr, 
                mesaj=f"🌊 Nöbet Havuzuna yeni bir nöbet düştü! ({nobet.tarih.strftime('%d.%m')}) Hemen 'Nöbet Havuzu' sayfasına giderek alabilirsiniz."
            )
    else:
        messages.warning(request, "⚠️ Bu nöbet zaten havuzda bekliyor!")
        
    return redirect('doktor_paneli')
    
# 3. Başka Bir Doktorun Havuzdan Nöbeti Alması (Ve Sihirli Mail)
@login_required(login_url='/hastane/giris/')
def havuzdan_al(request, havuz_id):
    yeni_doktor = get_object_or_404(Doktor, kullanici=request.user)
    ilan = get_object_or_404(NobetHavuzu, id=havuz_id, durum='aktif')
    
    if ilan.olusturan_doktor == yeni_doktor:
        messages.error(request, "❌ Kendi ilanınızı alamazsınız!")
        return redirect('nobet_havuzu')
        
    eski_doktor = ilan.nobet.doktor
    
    ilan.nobet.doktor = yeni_doktor
    ilan.nobet.save()
    
    ilan.durum = 'alindi'
    ilan.save()
    
    # 🌟 BİLDİRİM: Nöbeti devreden doktora sistem içi bildirim at
    Bildirim.objects.create(
        doktor=eski_doktor,
        mesaj=f"🏊‍♂️ {ilan.nobet.tarih.strftime('%d.%m.%Y')} tarihli nöbetiniz havuzdan Dr. {yeni_doktor.kullanici.last_name} tarafından ALINDI."
    )
    
    try:
        if eski_doktor.kullanici.email:
            send_mail(
                subject='🎉 Nöbetiniz Havuzdan Alındı!',
                message=f"Merhaba Dr. {eski_doktor.kullanici.first_name},\n\n{ilan.nobet.tarih.strftime('%d.%m.%Y')} tarihindeki nöbetiniz Dr. {yeni_doktor.kullanici.get_full_name()} tarafından havuzdan alınmıştır.\n\nİyi dinlenmeler dileriz!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[eski_doktor.kullanici.email],
                fail_silently=True,
            )
    except Exception as e:
        print(f"Havuz maili hatası: {e}")
        
    messages.success(request, f"🎉 {ilan.nobet.tarih.strftime('%d.%m.%Y')} tarihli nöbeti başarıyla üstünüze aldınız!")
    return redirect('doktor_paneli')   

# =========================================================
# 🌟 AŞAMA 2: PWA (MOBİL UYGULAMA) AYARLARI 🌟
# =========================================================

def manifest_json(request):
    manifest = {
        "name": "Doktor Nöbet Sistemi",
        "short_name": "Nöbet Paneli",
        "start_url": "/hastane/giris/",
        "display": "standalone",
        "background_color": "#121212",
        "theme_color": "#0056b3",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/3063/3063206.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(manifest)

def service_worker(request):
    sw_code = """
    self.addEventListener('install', (e) => {
        console.log('[Service Worker] Kurulum Başarılı');
    });
    self.addEventListener('fetch', (e) => {
        e.respondWith(fetch(e.request));
    });
    """
    return HttpResponse(sw_code, content_type='application/javascript')

# =========================================================
# 🌟 AŞAMA 3: RESMİ PDF ÇIKTISI (YAZDIRMA) 🌟
# =========================================================
from datetime import datetime

@staff_member_required
def resmi_pdf_cikti(request):
    bugun = datetime.today()
    yil = int(request.GET.get('yil', bugun.year))
    ay = int(request.GET.get('ay', bugun.month))
    
    nobetler = Nobet.objects.filter(tarih__year=yil, tarih__month=ay).order_by('tarih', 'bolum')
    
    aylar = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
    
    context = {
        'nobetler': nobetler,
        'yil': yil,
        'ay_adi': aylar.get(ay, ""),
        'bashekim_adi': request.user.get_full_name() or "Başhekim",
    }
    return render(request, 'hastane/resmi_pdf.html', context)

# =========================================================
# 🌟 CİLA 1 & 3: YARININ NÖBETÇİLERİNİ UYAR (MAİL + TELEGRAM) 🌟
# =========================================================
@staff_member_required
def yarin_nobetcilerini_uyar(request):
    yarin = datetime.today().date() + timedelta(days=1)
    yarin_nobetleri = Nobet.objects.filter(tarih=yarin)
    
    if not yarin_nobetleri.exists():
        messages.warning(request, "⚠️ Yarın için planlanmış herhangi bir nöbet bulunamadı.")
        return redirect('nobet_planla')
        
    gonderilen_mail = 0
    gonderilen_telegram = 0
    
    for nobet in yarin_nobetleri:
        doktor = nobet.doktor
        
        email = doktor.kullanici.email
        if email:
            try:
                baslik = f"⏰ Hatırlatma: Yarın Nöbetiniz Var! ({nobet.get_bolum_display()})"
                mesaj = f"Merhaba Dr. {doktor.kullanici.first_name},\n\nYarın ({yarin.strftime('%d.%m.%Y')}) tarihi itibariyle hastanemizin {nobet.get_bolum_display()} bölümünde nöbetçi olduğunuzu hatırlatırız.\n\nİyi nöbetler dileriz!\n\nMerkez Hastanesi Başhekimliği"
                
                send_mail(
                    subject=baslik,
                    message=mesaj,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                gonderilen_mail += 1
            except Exception as e:
                print(f"Mail gönderme hatası: {e}")

        if doktor.telegram_chat_id:
            try:
                telegram_mesaj = f"🏥 *Merkez Hastanesi Nöbet Hatırlatması*\n\nMerhaba Dr. {doktor.kullanici.first_name},\n\nYarın ({yarin.strftime('%d.%m.%Y')}) *{nobet.get_bolum_display()}* bölümünde nöbetiniz bulunmaktadır.\n\nİyi çalışmalar dileriz! 🩺"
                telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                
                requests.post(telegram_url, data={
                    'chat_id': doktor.telegram_chat_id, 
                    'text': telegram_mesaj, 
                    'parse_mode': 'Markdown'
                })
                gonderilen_telegram += 1
            except Exception as e:
                print(f"Telegram gönderme hatası: {e}")
                
    messages.success(request, f"✅ Başarılı! {gonderilen_mail} doktora Mail, {gonderilen_telegram} doktora Telegram mesajı gönderildi.")
    return redirect('nobet_planla') 

# =========================================================
# 🌟 CİLA 5: NÖBET ÜCRETİ / FİNANS RAPORU 🌟
# =========================================================
@staff_member_required
def nobet_ucret_raporu(request):
    bugun = timezone.now().date()
    yil = bugun.year
    ay = bugun.month

    aylar = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
    donem_ismi = f"{aylar[ay]} {yil}"

    birim_ucret = Decimal(str(getattr(settings, 'NOBET_BIRIM_UCRETI', 2500)))

    def nobet_zam_katsayisini_bul(tarih):
        if ResmiTatil.objects.filter(tarih=tarih, carpan_etkisi=True).exists():
            return Decimal('1.25') 
        return Decimal('1.00')     

    doktorlar = Doktor.objects.all()
    dr_ucretleri = []
    hastane_toplam_ucret = Decimal('0.00')

    for dr in doktorlar:
        dr_rapor_nobetleri = Nobet.objects.filter(doktor=dr, tarih__year=yil, tarih__month=ay)
        dr_toplam_nobet_sayisi = dr_rapor_nobetleri.count()
        
        if dr_toplam_nobet_sayisi == 0: 
            continue 

        dr_toplam_ucret = Decimal('0.00')
        for nobet in dr_rapor_nobetleri:
            zam_katsayisi = nobet_zam_katsayisini_bul(nobet.tarih)
            dr_toplam_ucret += birim_ucret * zam_katsayisi

        dr_ucretleri.append({
            'doktor_adi': dr.kullanici.get_full_name() or dr.kullanici.username,
            'toplam_nobet': dr_toplam_nobet_sayisi,
            'toplam_ucret': dr_toplam_ucret
        })
        
        hastane_toplam_ucret += dr_toplam_ucret

    context = {
        'donem_ismi': donem_ismi,
        'birim_ucret': birim_ucret,
        'dr_ucretleri': dr_ucretleri,
        'hastane_toplam_ucret': hastane_toplam_ucret,
        'tarih_imza': bugun.strftime("%d.%m.%Y")
    }

    return render(request, 'hastane/nobet_ucret_raporu.html', context)

# =========================================================
# 📊 CİLA 2: İSTATİSTİK VE VARYANS ANALİZ MERKEZİ 📊
# =========================================================
@staff_member_required
def nobet_analiz_merkezi(request):
    yil = int(request.GET.get('yil', datetime.today().year))
    ay = int(request.GET.get('ay', datetime.today().month))
    
    doktorlar = Doktor.objects.all()
    nobetler = Nobet.objects.filter(tarih__year=yil, tarih__month=ay)
    toplam_nobet_sayisi = nobetler.count()
    
    if toplam_nobet_sayisi == 0:
        messages.warning(request, "Seçili ayda analiz yapılacak veri bulunamadı.")
        return redirect('nobet_planla')

    veriler = []
    for dr in doktorlar:
        aylik_sayi = nobetler.filter(doktor=dr).count()
        haftasonu_sayi = nobetler.filter(doktor=dr, tarih__week_day__in=[1, 7]).count()
        veriler.append({
            'doktor': dr,
            'sayi': aylik_sayi,
            'haftasonu': haftasonu_sayi
        })

    n = len(veriler)
    ortalama = toplam_nobet_sayisi / n
    
    kareler_toplami = sum((v['sayi'] - ortalama)**2 for v in veriler)
    varyans = kareler_toplami / n
    standart_sapma = math.sqrt(varyans)

    adalet_skoru = max(0, 100 - (standart_sapma * 20)) 

    context = {
        'veriler': sorted(veriler, key=lambda x: x['sayi'], reverse=True),
        'ortalama': round(ortalama, 2),
        'standart_sapma': round(standart_sapma, 2),
        'adalet_skoru': round(adalet_skoru, 1),
        'yil': yil,
        'ay': ay,
    }
    return render(request, 'hastane/nobet_analiz.html', context)


# =========================================================
# 🕵️‍♂️ CİLA 3: SİSTEM HAREKETLERİ (LOG / GÜVENLİK) 🕵️‍♂️
# =========================================================
@staff_member_required
def sistem_loglari(request):
    loglar = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:100]
    
    context = {
        'loglar': loglar,
    }
    return render(request, 'hastane/sistem_loglari.html', context)

@login_required
def bildirimleri_okundu_isaretle(request):
    try:
        aktif_doktor = Doktor.objects.get(kullanici=request.user)
        Bildirim.objects.filter(doktor=aktif_doktor, okundu_mu=False).update(okundu_mu=True)
    except Doktor.DoesNotExist:
        pass 
        
    return redirect('doktor_paneli')
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse # HttpResponse eklendi
from datetime import datetime, timedelta, time
import pandas as pd # Excel için eklendi
import io           # Excel için eklendi
from .models import Doktor, Nobet, NobetTakas, Poliklinik, IzinTalebi
from .forms import TakasTalebiForm
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings


# 1. DOKTOR KONTROL PANELİ
@login_required(login_url='/hastane/giris/')
def doktor_paneli(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
        
        # --- İzin ekleme/silme kısmı ---
        if request.method == 'POST' and 'izin_tarih' in request.POST:
            tarih_str = request.POST.get('izin_tarih')
            izin_tarihi = datetime.strptime(tarih_str, '%Y-%m-%d').date()
            if not IzinTalebi.objects.filter(doktor=doktor, tarih=izin_tarihi).exists():
                IzinTalebi.objects.create(doktor=doktor, tarih=izin_tarihi)
                # Yeni eklenen mesaj kısmı
                messages.success(request, "🏖️ İzin talebiniz Başhekime iletildi!")
            return redirect('doktor_paneli')

        nobetler = Nobet.objects.filter(doktor=doktor).order_by('tarih')
        giden_talepler = NobetTakas.objects.filter(talep_eden_doktor=doktor).order_by('-olusturulma_tarihi')
        gelen_talepler = NobetTakas.objects.filter(hedef_doktor=doktor).order_by('-olusturulma_tarihi')
        izinler = IzinTalebi.objects.filter(doktor=doktor).order_by('tarih')

        # --- İSTATİSTİK HESAPLAMA ---
        yesil_sayisi = nobetler.filter(bolum='YESIL').count()
        sari_sayisi = nobetler.filter(bolum='SARI').count()
        kirmizi_sayisi = nobetler.filter(bolum='KIRMIZI').count()
        toplam_nobet = yesil_sayisi + sari_sayisi + kirmizi_sayisi

    except Doktor.DoesNotExist:
        doktor, nobetler, giden_talepler, gelen_talepler, izinler = None, [], [], [], []
        yesil_sayisi = sari_sayisi = kirmizi_sayisi = toplam_nobet = 0

    context = {
        'doktor': doktor, 
        'nobetler': nobetler, 
        'giden_talepler': giden_talepler, 
        'gelen_talepler': gelen_talepler, 
        'izinler': izinler,
        'yesil_sayisi': yesil_sayisi,
        'sari_sayisi': sari_sayisi,
        'kirmizi_sayisi': kirmizi_sayisi,
        'toplam_nobet': toplam_nobet,
        
    }
    return render(request, 'hastane/doktor_paneli.html', context)

@login_required(login_url='/hastane/giris/')
def izin_sil(request, izin_id):
    # Sadece kendi iznini silebilmesi için güvenlik önlemi
    izin = get_object_or_404(IzinTalebi, id=izin_id, doktor__kullanici=request.user)
    izin.delete()
    return redirect('doktor_paneli')

# 2. YENİ TAKAS TALEBİ OLUŞTURMA
@login_required(login_url='/hastane/giris/')
def takas_olustur(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
    except Doktor.DoesNotExist:
        return redirect('doktor_paneli')

    if request.method == 'POST':
        form = TakasTalebiForm(request.POST, doktor=doktor)
        
        # Form kuralları denetlemeden önce talebi kimin yaptığını forma fısıldıyoruz:
        form.instance.talep_eden_doktor = doktor 
        
        if form.is_valid():
            yeni_takas = form.save(commit=False)
            yeni_takas.durum = 'beklemede'
            yeni_takas.save()
            
            # --- YENİ EKLENEN MAİL GÖNDERME KISMI ---
            hedef_email = yeni_takas.hedef_doktor.kullanici.email
            if hedef_email: # Eğer doktorun sistemde kayıtlı bir maili varsa
                mesaj = f"Merhaba Dr. {yeni_takas.hedef_doktor.kullanici.first_name},\n\n"
                mesaj += f"Dr. {doktor.kullanici.first_name} {doktor.kullanici.last_name} size bir nöbet takas talebi gönderdi.\n"
                mesaj += "Lütfen doktor paneline girerek talebi onaylayın veya reddedin.\n\nİyi çalışmalar."
                
                from django.core.mail import send_mail
                send_mail(
                    subject='🔔 Yeni Nöbet Takas Talebi',
                    message=mesaj,
                    from_email=None, 
                    recipient_list=[hedef_email],
                    fail_silently=True, 
                )
            # -----------------------------------------
            # ... (Mail gönderme kodları burada duruyor) ...
                
                # YENİ EKLENEN SATIR:
                messages.success(request, "🔄 Takas talebiniz başarıyla gönderildi!")
                return redirect('doktor_paneli')
            return redirect('doktor_paneli')
    else:
        form = TakasTalebiForm(doktor=doktor)

    # İŞTE KAYBOLAN O HAYATİ SATIR BURADA:
    return render(request, 'hastane/takas_olustur.html', {'form': form, 'doktor': doktor})

# 3. AJAX: HEDEF DOKTORUN NÖBETLERİNİ GETİRME
@login_required(login_url='/hastane/giris/')
def load_nobetler(request):
    doktor_id = request.GET.get('doktor_id')
    nobetler = Nobet.objects.filter(doktor_id=doktor_id).order_by('tarih')
    return render(request, 'hastane/nobet_dropdown_list_options.html', {'nobetler': nobetler})

# 4. TAKAS TALEBİNE CEVAP VERME (ONAY/RED)
@login_required(login_url='/hastane/giris/')
def takas_cevapla(request, talep_id, cevap):
    doktor = get_object_or_404(Doktor, kullanici=request.user)
    talep = get_object_or_404(NobetTakas, id=talep_id, hedef_doktor=doktor)

    if talep.durum != 'beklemede':
        return redirect('doktor_paneli')

    if cevap == 'onayla':
        # Nöbetleri yer değiştirme mantığı
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

    elif cevap == 'reddet':
        talep.durum = 'reddedildi'
        talep.save()
        messages.error(request, "❌ Takas talebini reddettiniz!") 

    # --- YENİ EKLENEN MAİL GÖNDERME KISMI ---
    talep_eden_email = talep.talep_eden_doktor.kullanici.email
    if talep_eden_email:
        durum_yazisi = "ONAYLADI ✅" if cevap == 'onayla' else "REDDETTİ ❌"
        mesaj = f"Merhaba Dr. {talep.talep_eden_doktor.kullanici.first_name},\n\n"
        mesaj += f"Dr. {doktor.kullanici.first_name} {doktor.kullanici.last_name} nöbet takas talebinizi {durum_yazisi}.\n\n"
        mesaj += "Bilginize sunar, iyi çalışmalar dileriz."
        
        send_mail(
            subject=f'Takas Talebiniz {durum_yazisi}',
            message=mesaj,
            from_email=None,
            recipient_list=[talep_eden_email],
            fail_silently=True,
        )
    # -----------------------------------------

    return redirect('doktor_paneli')

    

# 5. TAKVİM İÇİN JSON VERİSİ
# 5. TAKVİM İÇİN AKILLI VE RENKLİ JSON VERİSİ
# 5. TAKVİM İÇİN AKILLI VE RENKLİ JSON VERİSİ (SADECE KİŞİSEL NÖBETLER)
@login_required(login_url='/hastane/giris/')
def nobet_verileri_json(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
        # SİHİRLİ SATIR: Sadece sisteme giren doktorun kendi nöbetlerini çekiyoruz
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
            # Artık doktorun ismi yerine "Yeşil Alan" gibi bölüm başlıkları yazacak
            'title': bolum_baslik,
            'start': f"{nobet.tarih.isoformat()}T{nobet.baslangic_saati.isoformat()}",
            'end': f"{nobet.tarih.isoformat()}T{nobet.bitis_saati.isoformat()}",
            'color': renk,
            'textColor': '#000' if hasattr(nobet, 'bolum') and nobet.bolum == 'SARI' else '#fff',
            'description': aciklama
        })
        
    return JsonResponse(nobet_listesi, safe=False)

# 6. OTOMATİK NÖBET PLANLAYICI ALGORİTMASI
from django.contrib.admin.views.decorators import staff_member_required

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
        
        # --- ÖNEMLİ DÜZELTME 1: ESKİ NÖBETLERİ SİL ---
        # Aynı tarihlere tekrar planlama yapılıyorsa, üst üste binmemesi için eskileri temizle
        Nobet.objects.filter(
            tarih__range=[baslangic, bitis], 
            doktor__poliklinik_id=secilen_poliklinik_id
        ).delete()
        
        gun_sayisi = (bitis - baslangic).days + 1
        current_date = baslangic
        
        doktor_nobet_sayilari = {dr: 0 for dr in meslektaslar}
        doktor_son_nobet = {dr: None for dr in meslektaslar}
        bolum_sirasi = [Nobet.Bolum.YESIL, Nobet.Bolum.SARI, Nobet.Bolum.KIRMIZI]
        
        for i in range(gun_sayisi):
            musait_doktorlar = []
            izinli_doktorlar = [] # İzinlileri ayrı bir kara listeye alıyoruz
            
            for dr in meslektaslar:
        
                if IzinTalebi.objects.filter(doktor=dr, tarih=current_date, durum='onaylandi').exists():
                    izinli_doktorlar.append(dr)
                    continue
                    
                son_nobet_tarihi = doktor_son_nobet[dr]
                if son_nobet_tarihi is None or (current_date - son_nobet_tarihi).days > 1:
                    musait_doktorlar.append(dr)
            
            # --- ÖNEMLİ DÜZELTME 2: KURAL ESNETME MANTIĞI ---
            # Eğer doktor yetmiyorsa dinlenme kuralını boşver (dün tutan bugün de tutsun) 
            # AMA İZİNLİ OLANLARA ASLA DOKUNMA!
            if len(musait_doktorlar) < 3:
                musait_doktorlar = [dr for dr in meslektaslar if dr not in izinli_doktorlar]
            
            # ADALET KURALI: O anki nöbet sayısı en az olanları öne al
            musait_doktorlar.sort(key=lambda x: doktor_nobet_sayilari[x])
            
            # Müsait olanlardan ilk 3'ünü seç (Eğer 3'ten az kişi varsa olanları seç)
            gunluk_secilenler = musait_doktorlar[:3]
            
            for idx, secilen_doktor in enumerate(gunluk_secilenler):
                bolum = bolum_sirasi[idx % len(bolum_sirasi)]
                
                Nobet.objects.create(
                    doktor=secilen_doktor,
                    tarih=current_date,
                    baslangic_saati=time(8, 0),
                    bitis_saati=time(8, 0),
                    bolum=bolum
                )
                
                doktor_nobet_sayilari[secilen_doktor] += 1
                doktor_son_nobet[secilen_doktor] = current_date
            
            current_date += timedelta(days=1)
            
        # --- EXCEL ÇIKTISI OLUŞTURMA ---
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


        # 🌟 YENİ EKLENEN: OTOMATİK E-POSTA BİLDİRİMİ 🌟
        # =================================================================
        try:
            # Sadece bu poliklinikteki (meslektaslar listesindeki) e-postası olan doktorları al
            alici_listesi = [dr.kullanici.email for dr in meslektaslar if dr.kullanici.email]
            
            if alici_listesi:
                send_mail(
                    subject=f'{secilen_poli.isim} Nöbet Programı Yayınlandı 📅',
                    message=f'Merhaba,\n\n{baslangic_str} ile {bitis_str} tarihleri arasındaki yeni nöbet programınız sisteme yüklenmiştir.\n\nLütfen sisteme giriş yaparak kendi nöbet günlerinizi kontrol ediniz.\n\nİyi çalışmalar dileriz.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=alici_listesi,
                    fail_silently=True, # Hata verirse Excel indirmeyi bozmasın diye True yapıyoruz
                )
        except Exception as e:
            print(f"Toplu nöbet maili gönderilirken hata oluştu: {e}")
        # =================================================================
        
        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return render(request, 'hastane/nobet_planla.html', {'poliklinikler': poliklinikler})   
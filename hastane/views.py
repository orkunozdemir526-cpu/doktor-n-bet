from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import datetime, timedelta, time
from .models import Doktor, Nobet, NobetTakas
from .forms import TakasTalebiForm

# 1. DOKTOR KONTROL PANELİ
@login_required(login_url='/hastane/giris/')
def doktor_paneli(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
        nobetler = Nobet.objects.filter(doktor=doktor).order_by('tarih')
        
        # Doktorun yaptığı ve ona gelen takas taleplerini çekiyoruz
        giden_talepler = NobetTakas.objects.filter(talep_eden_doktor=doktor).order_by('-olusturulma_tarihi')
        gelen_talepler = NobetTakas.objects.filter(hedef_doktor=doktor).order_by('-olusturulma_tarihi')
        
    except Doktor.DoesNotExist:
        doktor = None
        nobetler = []
        giden_talepler = []
        gelen_talepler = []

    context = {
        'doktor': doktor,
        'nobetler': nobetler,
        'giden_talepler': giden_talepler,
        'gelen_talepler': gelen_talepler,
    }
    return render(request, 'hastane/doktor_paneli.html', context)

# 2. YENİ TAKAS TALEBİ OLUŞTURMA
@login_required(login_url='/hastane/giris/')
def takas_olustur(request):
    try:
        doktor = Doktor.objects.get(kullanici=request.user)
    except Doktor.DoesNotExist:
        return redirect('doktor_paneli')

    if request.method == 'POST':
        form = TakasTalebiForm(request.POST, doktor=doktor)
        if form.is_valid():
            yeni_takas = form.save(commit=False)
            yeni_takas.talep_eden_doktor = doktor
            yeni_takas.durum = 'beklemede'
            yeni_takas.save()
            return redirect('doktor_paneli')
    else:
        form = TakasTalebiForm(doktor=doktor)

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

        if talep.alinacak_nobet:
            alinan_nobet = talep.alinacak_nobet
            alinan_nobet.doktor = talep.talep_eden_doktor
            alinan_nobet.save()

        talep.durum = 'onaylandi'
        talep.save()

    elif cevap == 'reddet':
        talep.durum = 'reddedildi'
        talep.save()

    return redirect('doktor_paneli')

# 5. TAKVİM İÇİN JSON VERİSİ
@login_required(login_url='/hastane/giris/')
def nobet_verileri_json(request):
    nobetler = Nobet.objects.all()
    nobet_listesi = []
    for nobet in nobetler:
        nobet_listesi.append({
            'title': f"{nobet.doktor}",
            'start': f"{nobet.tarih.isoformat()}T{nobet.baslangic_saati.isoformat()}",
            'end': f"{nobet.tarih.isoformat()}T{nobet.bitis_saati.isoformat()}",
            'color': '#007bff' if nobet.doktor.kullanici == request.user else '#6c757d',
        })
    return JsonResponse(nobet_listesi, safe=False)

# 6. OTOMATİK NÖBET PLANLAYICI ALGORİTMASI
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required # Sadece Admin yetkisi olanlar girebilir
def nobet_planla(request):
    # Admin tüm poliklinikleri görebilsin
    poliklinikler = Doktor.objects.values_list('poliklinik', flat=True).distinct()

    if request.method == 'POST':
        secilen_poliklinik = request.POST.get('poliklinik')
        baslangic_str = request.POST.get('baslangic_tarihi')
        bitis_str = request.POST.get('bitis_tarihi')
        
        meslektaslar = Doktor.objects.filter(poliklinik=secilen_poliklinik)
        doktor_sayisi = meslektaslar.count()

        if doktor_sayisi == 0:
             return render(request, 'hastane/nobet_planla.html', {'error': 'Bu poliklinikte doktor bulunamadı.', 'poliklinikler': poliklinikler})

        try:
            baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
            bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return render(request, 'hastane/nobet_planla.html', {'error': 'Geçersiz tarih.', 'poliklinikler': poliklinikler})
        
        gun_sayisi = (bitis - baslangic).days + 1
        current_date = baslangic
        
        for i in range(gun_sayisi):
            secilen_doktor = meslektaslar[i % doktor_sayisi]
            if not Nobet.objects.filter(tarih=current_date, doktor=secilen_doktor).exists():
                Nobet.objects.create(
                    doktor=secilen_doktor,
                    tarih=current_date,
                    baslangic_saati=time(8, 0),
                    bitis_saati=time(0, 0)
                )
            current_date += timedelta(days=1)
            
        return redirect('/admin/hastane/nobet/') # İşlem bitince admin paneline geri dön

    return render(request, 'hastane/nobet_planla.html', {'poliklinikler': poliklinikler})
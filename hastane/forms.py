from django import forms
from django.utils import timezone
from .models import NobetTakas, Nobet, Doktor

# 🌟 Nöbet listesini jilet gibi gösteren özel formatlayıcı
class CustomNobetChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        aylar = {1:"Oca", 2:"Şub", 3:"Mar", 4:"Nis", 5:"May", 6:"Haz", 7:"Tem", 8:"Ağu", 9:"Eyl", 10:"Eki", 11:"Kas", 12:"Ara"}
        ay_adi = aylar.get(obj.tarih.month, "")
        tarih_str = f"{obj.tarih.day:02d} {ay_adi} {obj.tarih.year}"
        baslangic = obj.baslangic_saati.strftime('%H:%M')
        bitis = obj.bitis_saati.strftime('%H:%M')
        return f"{tarih_str} | Saat: {baslangic} - {bitis} [{obj.get_bolum_display()}]"

class TakasTalebiForm(forms.ModelForm):
    verilecek_nobet = CustomNobetChoiceField(
        queryset=Nobet.objects.none(), 
        label="Verilecek Nöbet (Sizin Nöbetiniz)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    alinacak_nobet = forms.ModelChoiceField(
        queryset=Nobet.objects.none(), 
        required=False, 
        label="Alınacak Nöbet (Hedef Doktorun Nöbeti)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = NobetTakas
        fields = ['verilecek_nobet', 'hedef_doktor', 'alinacak_nobet', 'aciklama']
        widgets = {
            'hedef_doktor': forms.Select(attrs={'class': 'form-control'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Opsiyonel mazeretiniz...'}),
        }

    # 🌟 İşte silinen ve sistemi çökerten o kritik fonksiyon:
    def __init__(self, *args, **kwargs):
        self.doktor = kwargs.pop('doktor', None)
        super(TakasTalebiForm, self).__init__(*args, **kwargs)
        
        bugun = timezone.now().date()
        
        if self.doktor:
            # Senin nöbetlerin ve diğer doktorlar listesi
            self.fields['verilecek_nobet'].queryset = Nobet.objects.filter(doktor=self.doktor, tarih__gte=bugun).order_by('tarih')
            self.fields['hedef_doktor'].queryset = Doktor.objects.exclude(id=self.doktor.id)

        # 🌟 İŞTE ÇÖZÜM BURADA: GÜVENLİK KİLİDİNİ AÇIYORUZ
        # Eğer form "Gönder" butonuna basılarak gelmişse (self.data içinde hedef_doktor varsa)
        if 'hedef_doktor' in self.data:
            try:
                # Ekranda seçilen hedef doktorun kimliğini (ID) al
                hedef_id = int(self.data.get('hedef_doktor'))
                # Django'nun güvenlik polisine: "Bu doktorun gelecek nöbetlerini kabul et" emrini ver
                self.fields['alinacak_nobet'].queryset = Nobet.objects.filter(doktor_id=hedef_id, tarih__gte=bugun).order_by('tarih')
            except (ValueError, TypeError):
                pass
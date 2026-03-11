from django import forms
from .models import NobetTakas, Nobet, Doktor

class TakasTalebiForm(forms.ModelForm):
    class Meta:
        model = NobetTakas
        fields = ['verilecek_nobet', 'hedef_doktor', 'alinacak_nobet', 'aciklama']
        
        widgets = {
            'verilecek_nobet': forms.Select(attrs={'class': 'form-control'}),
            'hedef_doktor': forms.Select(attrs={'class': 'form-control'}),
            'alinacak_nobet': forms.Select(attrs={'class': 'form-control'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Neden takas yapmak istiyorsunuz?'}),
        }

    def __init__(self, *args, **kwargs):
        doktor = kwargs.pop('doktor', None)
        super(TakasTalebiForm, self).__init__(*args, **kwargs)
        
        if doktor:
            # 1. Sadece benim nöbetlerim
            self.fields['verilecek_nobet'].queryset = Nobet.objects.filter(doktor=doktor)
            
            # 2. Sadece AYNI poliklinikteki diğer doktorlar
            self.fields['hedef_doktor'].queryset = Doktor.objects.filter(
                poliklinik=doktor.poliklinik
            ).exclude(id=doktor.id)
            
            # 3. Benim nöbetlerim hariç tüm nöbetler
            self.fields['alinacak_nobet'].queryset = Nobet.objects.exclude(doktor=doktor)
            self.fields['alinacak_nobet'].required = False
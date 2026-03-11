from django.core.management.base import BaseCommand
from core.nobet_planner import NobetPlanlayici

class Command(BaseCommand):
    help = 'Belirtilen ay ve yıl için otomatik nöbet planı oluşturur.'

    def add_arguments(self, parser):
        parser.add_argument('yil', type=int, help='Nöbet planı oluşturulacak yıl (örn: 2025)')
        parser.add_argument('ay', type=int, help='Nöbet planı oluşturulacak ay (örn: 11)')

    def handle(self, *args, **options):
        yil = options['yil']
        ay = options['ay']

        self.stdout.write(self.style.SUCCESS(f'{yil} yılının {ay}. ayı için nöbet planı oluşturuluyor...'))
        
        try:
            planlayici = NobetPlanlayici(yil, ay)
            plan = planlayici.plani_olustur()
            
            if not plan:
                self.stdout.write(self.style.ERROR('Plan oluşturulamadı. Lütfen logları kontrol edin.'))
                return

            planlayici.plani_kaydet(plan)
            
            self.stdout.write(self.style.SUCCESS('Nöbet planı başarıyla oluşturuldu ve veritabanına kaydedildi.'))
            self.stdout.write(self.style.WARNING('Sonuçları kontrol etmek için Admin panelini ziyaret edebilirsiniz.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Bir hata oluştu: {e}'))
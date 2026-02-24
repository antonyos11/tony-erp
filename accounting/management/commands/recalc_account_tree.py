from django.core.management.base import BaseCommand
from accounting.services import AccountService

class Command(BaseCommand):
    help = 'إعادة حساب مستويات ومسارات شجرة الحسابات (level/path) آمنة.'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعادة الحساب...')
        AccountService.recalc_paths()
        self.stdout.write(self.style.SUCCESS('اكتملت إعادة الحساب بنجاح.'))

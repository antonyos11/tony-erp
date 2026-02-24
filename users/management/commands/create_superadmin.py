from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from users.models import UserRole, UserProfile


class Command(BaseCommand):
    help = 'إنشاء مستخدم مدير عام للنظام'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='اسم المستخدم')
        parser.add_argument('--email', required=True, help='البريد الإلكتروني')
        parser.add_argument('--arabic-name', required=True, help='الاسم بالعربية')
        parser.add_argument('--employee-id', required=True, help='رقم الموظف')
        parser.add_argument('--password', help='كلمة المرور (اختيارية)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        arabic_name = options['arabic_name']
        employee_id = options['employee_id']
        password = options.get('password', None)

        self.stdout.write(f'إنشاء مستخدم مدير عام: {username}')

        # فحص إذا كان المستخدم موجود
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'المستخدم {username} موجود بالفعل!')
            )
            return

        # فحص إذا كان رقم الموظف موجود
        if UserProfile.objects.filter(employee_id=employee_id).exists():
            self.stdout.write(
                self.style.ERROR(f'رقم الموظف {employee_id} مستخدم بالفعل!')
            )
            return

        try:
            with transaction.atomic():
                # الحصول على دور المدير العام
                super_admin_role = UserRole.objects.get(name='super_admin')

                # إنشاء المستخدم
                if password:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                else:
                    import secrets as _secrets
                    import string as _string
                    _tmp_pw = ''.join(
                        _secrets.choice(_string.ascii_letters + _string.digits + '!@#$')
                        for _ in range(16)
                    )
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=_tmp_pw  # كلمة مرور مولّدة تلقائياً
                    )
                    self.stdout.write(f'  ⚠️  كلمة المرور المؤقتة: {_tmp_pw} (غيّرها فوراً!)')

                # تعيين الصلاحيات الأساسية
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()

                # إنشاء ملف التعريف
                profile = UserProfile.objects.create(
                    user=user,
                    arabic_name=arabic_name,
                    employee_id=employee_id,
                    role=super_admin_role,
                    is_approved=True,
                    must_change_password=not bool(password)
                )

                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء المستخدم بنجاح!')
                )
                self.stdout.write(f'اسم المستخدم: {username}')
                self.stdout.write(f'البريد الإلكتروني: {email}')
                self.stdout.write(f'الاسم بالعربية: {arabic_name}')
                self.stdout.write(f'رقم الموظف: {employee_id}')
                
                if not password:
                    self.stdout.write(
                        self.style.WARNING('كلمة المرور المؤقتة: admin123')
                    )
                    self.stdout.write(
                        self.style.WARNING('يجب تغيير كلمة المرور عند تسجيل الدخول الأول')
                    )

        except UserRole.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('دور المدير العام غير موجود! قم بتشغيل setup_roles_permissions أولاً')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء المستخدم: {str(e)}')
            )
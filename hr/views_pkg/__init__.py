"""
نظام الموارد البشرية - Views
============================
تم تقسيم ملف views.py الأصلي (4178 سطر) إلى وحدات منظمة.

الوحدات:
- dashboard: لوحة التحكم الرئيسية
- employees: إدارة الموظفين والأقسام والمناصب
- attendance: نظام الحضور والانصراف
- leave: إدارة الإجازات
- payroll: إدارة الرواتب
- performance: تقييم الأداء والأهداف
- training: التدريب والتطوير
- recruitment: التوظيف
- relations_hse: العلاقات العمالية والسلامة المهنية
- reports: التقارير
- device_api: API للأجهزة الخارجية
- portal: بوابة الموظفين
- id_cards: بطاقات الهوية
- payroll_auto: الحساب التلقائي للرواتب
- payroll_items: مفردات المرتب
"""

from .dashboard import *
from .employees import *
from .attendance import *
from .leave import *
from .payroll import *
from .performance import *
from .training import *
from .recruitment import *
from .relations_hse import *
from .reports import *
from .device_api import *
from .portal import *
from .id_cards import *
from .payroll_auto import *
from .payroll_items import *

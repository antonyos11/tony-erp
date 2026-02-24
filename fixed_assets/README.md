# 🏢 نظام الأصول الثابتة (Fixed Assets)

## نظرة عامة
نظام متكامل لإدارة الأصول الثابتة يشمل التسجيل، الاستهلاك، الصيانة، والتخلص في Tony ERP.

## الميزات الرئيسية
- ✅ تسجيل الأصول مع بيانات كاملة
- ✅ حساب الاستهلاك تلقائياً (4 طرق)
- ✅ جدولة الصيانة الدورية
- ✅ تتبع الموقع والمسؤول
- ✅ إعادة التقييم والتخلص
- ✅ تقارير الأصول والاستهلاك

## طرق الاستهلاك
| الطريقة | الوصف |
|---------|-------|
| `straight_line` | القسط الثابت |
| `declining_balance` | القسط المتناقص |
| `double_declining` | القسط المتناقص المضاعف |
| `sum_of_years` | مجموع السنين |

## النماذج (Models)
| النموذج | الوصف |
|---------|-------|
| `AssetCategory` | تصنيف الأصول |
| `Asset` | الأصل الثابت |
| `DepreciationSchedule` | جدول الاستهلاك |
| `AssetMaintenance` | سجل الصيانة |
| `AssetDisposal` | التخلص من الأصل |

## كيفية الاستخدام

### 1. إضافة أصل جديد
```python
from fixed_assets.models import Asset

asset = Asset.objects.create(
    name='ماكينة طباعة',
    category=category,
    purchase_date=date.today(),
    purchase_cost=50000,
    useful_life_years=5,
    salvage_value=5000,
    depreciation_method='straight_line'
)
```

### 2. حساب الاستهلاك
```python
asset.calculate_depreciation()
# أو للكل
Asset.run_monthly_depreciation()
```

## API Endpoints
| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/assets/` | GET/POST | قائمة/إضافة أصول |
| `/api/assets/<id>/depreciate/` | POST | حساب استهلاك |
| `/api/assets/<id>/dispose/` | POST | التخلص |
| `/api/assets/reports/summary/` | GET | تقرير ملخص |

## التقارير
- 📊 سجل الأصول
- 📉 جدول الاستهلاك
- 🔧 سجل الصيانة
- 💰 القيمة الدفترية

## القيود المحاسبية
```
شراء أصل:
  من ح/ الأصول الثابتة
  إلى ح/ النقدية/الدائنون

استهلاك شهري:
  من ح/ مصروف الاستهلاك
  إلى ح/ مجمع الاستهلاك

بيع أصل:
  من ح/ النقدية
  من ح/ مجمع الاستهلاك
  إلى ح/ الأصول الثابتة
  إلى/من ح/ أرباح/خسائر بيع أصول
```

---
**آخر تحديث**: ديسمبر 2025

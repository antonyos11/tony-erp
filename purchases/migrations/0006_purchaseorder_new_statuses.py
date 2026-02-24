from django.db import migrations


def forwards(apps, schema_editor):
    PurchaseOrder = apps.get_model('purchases', 'PurchaseOrder')
    # لا حاجة لتعديل فوري للبيانات، فقط نضمن أن الحالات الحالية تبقى كما هي
    for po in PurchaseOrder.objects.filter(status__in=['confirmed','draft','cancelled']):
        pass


def backwards(apps, schema_editor):
    PurchaseOrder = apps.get_model('purchases', 'PurchaseOrder')
    # إعادة أي حالات جديدة إلى confirmed عند الرجوع
    PurchaseOrder.objects.filter(status__in=['partial','completed']).update(status='confirmed')


class Migration(migrations.Migration):
    dependencies = [
        ('purchases', '0005_purchasebill_posted_at_purchasebill_status_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

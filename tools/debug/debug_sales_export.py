from django.test import Client
from django.contrib.auth import get_user_model

u= get_user_model().objects.create_user('x1', password='p')
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
ct,_=ContentType.objects.get_or_create(app_label='reports', model='reportsmeta')
view_perm=Permission.objects.get_or_create(codename='view_reports', defaults={'name':'Can view aggregated reports','content_type':ct})[0]
# no export perm added intentionally
u.user_permissions.add(view_perm)
client=Client(); client.login(username='x1', password='p')
resp=client.get('/api/reports/sales/?format=csv')
print('Status:', resp.status_code)
print('Content-Type:', resp.headers.get('Content-Type'))
print(resp.content[:200])

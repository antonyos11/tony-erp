import os, django, sys, traceback
try:
	os.environ.setdefault('DJANGO_SETTINGS_MODULE','accountant_pro.settings')
	django.setup()
	from django.test import Client
	from django.contrib.auth import get_user_model
	from django.contrib.contenttypes.models import ContentType
	from django.contrib.auth.models import Permission
	U=get_user_model(); u=U.objects.create_user('permtest',password='p')
	ct,_=ContentType.objects.get_or_create(app_label='reports',model='reportsmeta')
	view_perm=Permission.objects.get_or_create(codename='view_reports',defaults={'name':'Can view aggregated reports','content_type':ct})[0]
	u.user_permissions.add(view_perm)
	client=Client(); client.login(username='permtest', password='p')
	resp=client.get('/api/reports/sales/?format=csv')
	print('RESPONSE STATUS:', resp.status_code, flush=True)
	print('HEADERS:', dict(resp.headers), flush=True)
	print('FIRST 60 BYTES:', resp.content[:60], flush=True)
except Exception:
	traceback.print_exc()
	sys.exit(1)

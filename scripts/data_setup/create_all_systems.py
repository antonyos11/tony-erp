import os

# تعريف جميع الأنظمة
systems = {
    'marketing_campaigns': {
        'title': 'الحملات التسويقية',
        'icon': 'bi-megaphone',
        'models': ['Campaign', 'CustomerSegment', 'CampaignMessage'],
    },
    'tender_bidding': {
        'title': 'المناقصات والعطاءات',
        'icon': 'bi-file-earmark-text',
        'models': ['Tender', 'Bid', 'TenderEvaluation'],
    },
    'warranty_management': {
        'title': 'إدارة الضمانات',
        'icon': 'bi-shield-check',
        'models': ['Warranty', 'WarrantyClaim', 'WarrantyPolicy'],
    },
    'customer_profitability': {
        'title': 'ربحية العملاء',
        'icon': 'bi-wallet2',
        'models': ['CustomerProfitabilityAnalysis', 'CustomerValueScore'],
    },
    'energy_management': {
        'title': 'إدارة الطاقة',
        'icon': 'bi-lightning-charge',
        'models': ['UtilityMeter', 'UtilityReading', 'EnergyConsumptionAnalysis'],
    },
    'complaint_management': {
        'title': 'إدارة الشكاوى',
        'icon': 'bi-headset',
        'models': ['Complaint', 'ImprovementInitiative'],
    },
    'license_management': {
        'title': 'التراخيص والتصاريح',
        'icon': 'bi-file-earmark-medical',
        'models': ['License', 'LicenseRenewal', 'GovernmentPermit'],
    },
    'competitive_intelligence': {
        'title': 'الذكاء التنافسي',
        'icon': 'bi-binoculars',
        'models': ['Competitor', 'CompetitorProduct', 'MarketTrend'],
    },
    'compliance_management': {
        'title': 'الامتثال والمراجعة',
        'icon': 'bi-check-circle',
        'models': ['ComplianceStandard', 'Audit', 'ComplianceReport'],
    },
}

for app_name, config in systems.items():
    print(f"Creating files for {app_name}...")
    
    # Create urls.py
    urls_content = f"""from django.urls import path
from . import views

app_name = '{app_name}'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.item_list, name='item_list'),
]
"""
    with open(f'{app_name}/urls.py', 'w', encoding='utf-8') as f:
        f.write(urls_content)
    
    # Create views.py
    views_content = f"""from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    context = {{
        'page_title': '{config['title']}',
        'icon': '{config['icon']}',
    }}
    return render(request, '{app_name}/dashboard.html', context)

@login_required
def item_list(request):
    context = {{
        'page_title': '{config['title']} - القائمة',
        'icon': '{config['icon']}',
    }}
    return render(request, '{app_name}/list.html', context)
"""
    with open(f'{app_name}/views.py', 'w', encoding='utf-8') as f:
        f.write(views_content)
    
    # Create templates directory
    os.makedirs(f'{app_name}/templates/{app_name}', exist_ok=True)
    
    # Create dashboard.html
    dashboard_html = """{% extends 'base.html' %}

{% block title %}{{ page_title }}{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <div class="row mb-4">
        <div class="col-12">
            <h2><i class="{{ icon }} me-2"></i>{{ page_title }}</h2>
        </div>
    </div>

    <div class="row mb-3">
        <div class="col-12">
            <a href="{% url '""" + app_name + """:item_list' %}" class="btn btn-primary">
                <i class="bi bi-list me-1"></i>عرض الكل
            </a>
            <a href="#" class="btn btn-success">
                <i class="bi bi-plus-circle me-1"></i>إضافة جديد
            </a>
        </div>
    </div>

    <div class="row">
        <div class="col-md-4">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h5>إجمالي السجلات</h5>
                    <h2>0</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5>النشطة</h5>
                    <h2>0</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <h5>قيد المراجعة</h5>
                    <h2>0</h2>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""
    with open(f'{app_name}/templates/{app_name}/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print(f"✅ Created files for {app_name}")

print("\n✅ All systems created successfully!")

# 📖 AI Quick Reference - مرجع سريع للذكاء الاصطناعي

> **للاستخدام السريع:** نسخ ولصق الأوامر والأكواد الشائعة

---

## 🔧 أوامر Django الأساسية

```bash
# التحقق من النظام
python manage.py check

# تشغيل الخادم
python manage.py runserver 0.0.0.0:8000

# إنشاء migrations
python manage.py makemigrations
python manage.py makemigrations app_name

# تطبيق migrations
python manage.py migrate

# عرض migrations معلقة
python manage.py showmigrations | grep "\[ \]"

# Shell تفاعلي
python manage.py shell

# إنشاء superuser
python manage.py createsuperuser

# جمع static files
python manage.py collectstatic --noinput

# تنظيف sessions
python manage.py clearsessions
```

---

## 📦 قوالب الموديلات

### موديل أساسي
```python
from django.db import models
from django.utils.translation import gettext_lazy as _

class MyModel(models.Model):
    """وصف الموديل"""
    
    name = models.CharField(max_length=255, verbose_name=_("الاسم"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    
    class Meta:
        verbose_name = _("الاسم المفرد")
        verbose_name_plural = _("الاسم الجمع")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

### موديل مع ForeignKey
```python
class ChildModel(models.Model):
    parent = models.ForeignKey(
        'ParentModel',
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name=_("الأب")
    )
    name = models.CharField(max_length=255, verbose_name=_("الاسم"))
```

### موديل مع Choices
```python
class StatusChoices(models.TextChoices):
    DRAFT = 'draft', _('مسودة')
    PENDING = 'pending', _('قيد الانتظار')
    APPROVED = 'approved', _('معتمد')
    REJECTED = 'rejected', _('مرفوض')

class MyModel(models.Model):
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name=_("الحالة")
    )
```

### موديل مالي
```python
class FinancialModel(models.Model):
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name=_("المبلغ")
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        verbose_name=_("نسبة الضريبة")
    )
```

---

## 🌐 قوالب Views

### ListView
```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

class MyListView(LoginRequiredMixin, ListView):
    model = MyModel
    template_name = 'app/my_list.html'
    context_object_name = 'items'
    paginate_by = 25
    
    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs
```

### CreateView
```python
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages

class MyCreateView(LoginRequiredMixin, CreateView):
    model = MyModel
    form_class = MyForm
    template_name = 'app/my_form.html'
    success_url = reverse_lazy('app:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "تم الإنشاء بنجاح")
        return super().form_valid(form)
```

### UpdateView
```python
from django.views.generic import UpdateView

class MyUpdateView(LoginRequiredMixin, UpdateView):
    model = MyModel
    form_class = MyForm
    template_name = 'app/my_form.html'
    success_url = reverse_lazy('app:list')
    
    def form_valid(self, form):
        messages.success(self.request, "تم التحديث بنجاح")
        return super().form_valid(form)
```

### DeleteView
```python
from django.views.generic import DeleteView

class MyDeleteView(LoginRequiredMixin, DeleteView):
    model = MyModel
    template_name = 'app/my_confirm_delete.html'
    success_url = reverse_lazy('app:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "تم الحذف بنجاح")
        return super().delete(request, *args, **kwargs)
```

### Function View
```python
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

@login_required
def my_view(request, pk):
    obj = get_object_or_404(MyModel, pk=pk)
    
    if request.method == 'POST':
        form = MyForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "تم الحفظ")
            return redirect('app:detail', pk=pk)
    else:
        form = MyForm(instance=obj)
    
    return render(request, 'app/my_form.html', {'form': form, 'object': obj})
```

---

## 🔗 قوالب URLs

### urls.py للتطبيق
```python
from django.urls import path
from . import views

app_name = 'app_name'

urlpatterns = [
    path('', views.MyListView.as_view(), name='list'),
    path('create/', views.MyCreateView.as_view(), name='create'),
    path('<int:pk>/', views.MyDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.MyUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.MyDeleteView.as_view(), name='delete'),
]
```

### إضافة في urls.py الرئيسي
```python
# accountant_pro/urls.py
urlpatterns = [
    # ...
    path('app_name/', include('app_name.urls', namespace='app_name')),
]
```

---

## 📝 قوالب Forms

### ModelForm
```python
from django import forms
from .models import MyModel

class MyForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise forms.ValidationError("الاسم قصير جداً")
        return name
```

---

## 🔌 قوالب API

### Serializer
```python
from rest_framework import serializers
from .models import MyModel

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
```

### ViewSet
```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import MyModel
from .serializers import MyModelSerializer

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
```

### تسجيل في Router
```python
# api/urls.py
from rest_framework.routers import DefaultRouter
from app_name.api_views import MyModelViewSet

router = DefaultRouter()
router.register('my-models', MyModelViewSet)
```

---

## 📄 قوالب Templates

### قالب List
```html
{% extends 'base.html' %}
{% load static %}

{% block title %}قائمة العناصر{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h1>العناصر</h1>
        <a href="{% url 'app:create' %}" class="btn btn-primary">
            <i class="fas fa-plus"></i> إضافة جديد
        </a>
    </div>
    
    <div class="card">
        <div class="card-body">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>الاسم</th>
                        <th>الحالة</th>
                        <th>الإجراءات</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td>{{ item.id }}</td>
                        <td>{{ item.name }}</td>
                        <td>
                            {% if item.is_active %}
                            <span class="badge bg-success">نشط</span>
                            {% else %}
                            <span class="badge bg-secondary">غير نشط</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="{% url 'app:detail' item.pk %}" class="btn btn-sm btn-info">
                                <i class="fas fa-eye"></i>
                            </a>
                            <a href="{% url 'app:edit' item.pk %}" class="btn btn-sm btn-warning">
                                <i class="fas fa-edit"></i>
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="4" class="text-center">لا توجد بيانات</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    {% if is_paginated %}
    <nav class="mt-3">
        <ul class="pagination justify-content-center">
            {% if page_obj.has_previous %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.previous_page_number }}">السابق</a>
            </li>
            {% endif %}
            <li class="page-item active">
                <span class="page-link">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
            </li>
            {% if page_obj.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.next_page_number }}">التالي</a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
</div>
{% endblock %}
```

### قالب Form
```html
{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block title %}{% if object %}تعديل{% else %}إنشاء{% endif %} عنصر{% endblock %}

{% block content %}
<div class="container">
    <div class="card">
        <div class="card-header">
            <h4>{% if object %}تعديل{% else %}إنشاء{% endif %} عنصر</h4>
        </div>
        <div class="card-body">
            <form method="post" enctype="multipart/form-data">
                {% csrf_token %}
                {{ form|crispy }}
                <div class="mt-3">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> حفظ
                    </button>
                    <a href="{% url 'app:list' %}" class="btn btn-secondary">
                        <i class="fas fa-times"></i> إلغاء
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 🔍 استعلامات شائعة

```python
# البحث
Model.objects.filter(name__icontains='بحث')

# فلترة بتاريخ
from django.utils import timezone
Model.objects.filter(created_at__date=timezone.now().date())

# ترتيب
Model.objects.order_by('-created_at')

# تجميع
from django.db.models import Sum, Count, Avg
Model.objects.aggregate(total=Sum('amount'))

# Group By
Model.objects.values('status').annotate(count=Count('id'))

# Select Related (ForeignKey)
Model.objects.select_related('customer', 'branch')

# Prefetch Related (ManyToMany, reverse FK)
Model.objects.prefetch_related('items', 'tags')

# Q objects (OR)
from django.db.models import Q
Model.objects.filter(Q(name='x') | Q(code='x'))

# Exists
Model.objects.filter(pk=1).exists()

# Get or 404
from django.shortcuts import get_object_or_404
obj = get_object_or_404(Model, pk=1)
```

---

## ⚡ Signals

```python
# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import MyModel

@receiver(post_save, sender=MyModel)
def my_model_saved(sender, instance, created, **kwargs):
    if created:
        # عند الإنشاء
        pass
    else:
        # عند التحديث
        pass

@receiver(pre_save, sender=MyModel)
def before_save(sender, instance, **kwargs):
    # قبل الحفظ
    pass
```

---

## 🕐 Celery Tasks

```python
# tasks.py
from celery import shared_task

@shared_task
def my_async_task(param):
    """مهمة غير متزامنة"""
    # العملية هنا
    return result

# الاستدعاء
my_async_task.delay(param)

# مع تأخير
my_async_task.apply_async(args=[param], countdown=60)
```

---

## 📊 Admin

```python
# admin.py
from django.contrib import admin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
```

---

*آخر تحديث: يناير 2026*

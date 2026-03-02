"""
واجهات عروض الأسعار — RITA ERP
"""
import json
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, View

from apps.core.models import Branch
from apps.core.mixins import apply_branch_filter, BranchCreateMixin
from apps.sales.models import Customer, PriceList
from apps.inventory.models import Product
from apps.quotations.models import Quotation, QuotationLine, QuotationFollowUp
from apps.quotations.services.quotation_engine import QuotationEngine
from apps.authorization.decorators import PermissionRequiredMixin


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class QuotationForm(forms.Form):
    """فورم إنشاء / تعديل عرض سعر"""
    # العميل
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True).order_by('name'),
        required=False, label='العميل',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_customer'}),
    )
    # بيانات عميل محتمل
    prospect_name = forms.CharField(
        max_length=255, required=False, label='اسم العميل المحتمل',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    prospect_phone = forms.CharField(
        max_length=20, required=False, label='هاتف',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    prospect_email = forms.EmailField(
        required=False, label='إيميل',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    prospect_company = forms.CharField(
        max_length=255, required=False, label='الشركة',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    prospect_address = forms.CharField(
        required=False, label='العنوان',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    valid_days = forms.ChoiceField(
        choices=[('7', '7 أيام'), ('15', '15 يوم'), ('30', '30 يوم'), ('60', '60 يوم')],
        initial='15', label='صلاحية العرض',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discount_percentage = forms.DecimalField(
        min_value=0, max_value=100, initial=0, required=False,
        label='خصم إجمالي %',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    is_taxable = forms.BooleanField(
        required=False, initial=True, label='خاضع للضريبة',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    delivery_required = forms.BooleanField(
        required=False, initial=False, label='يحتاج توصيل',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    delivery_fee = forms.DecimalField(
        min_value=0, initial=0, required=False, label='رسوم التوصيل',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    terms_and_conditions = forms.CharField(
        required=False, label='الشروط والأحكام',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    customer_notes = forms.CharField(
        required=False, label='ملاحظات للعميل',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    internal_notes = forms.CharField(
        required=False, label='ملاحظات داخلية',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    payment_terms = forms.CharField(
        max_length=255, required=False, label='شروط الدفع',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned = super().clean()
        customer = cleaned.get('customer')
        prospect_name = cleaned.get('prospect_name')
        if not customer and not prospect_name:
            raise forms.ValidationError('يجب تحديد عميل أو إدخال اسم عميل محتمل')
        return cleaned


class FollowUpForm(forms.Form):
    follow_up_type = forms.ChoiceField(
        choices=QuotationFollowUp.FOLLOW_UP_TYPES,
        label='نوع المتابعة',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    result = forms.ChoiceField(
        choices=QuotationFollowUp.FOLLOW_UP_RESULTS,
        label='النتيجة',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        label='الملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    next_follow_up_date = forms.DateField(
        required=False, label='تاريخ المتابعة القادمة',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )


# ══════════════════════════════════════════════════════
# لوحة عروض الأسعار
# ══════════════════════════════════════════════════════

class QuotationDashboardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'view'
    template_name = 'quotations/quotation_dashboard.html'

    def get(self, request):
        branch = getattr(request, 'current_branch', None)
        stats = QuotationEngine.get_quotation_stats(branch=branch)

        # العروض القريبة من الانتهاء (خلال 3 أيام)
        today = timezone.now().date()
        expiring_soon = Quotation.objects.filter(
            valid_until__range=[today, today + timezone.timedelta(days=3)],
            status__in=['draft', 'sent', 'negotiation'],
        ).order_by('valid_until')
        if branch:
            expiring_soon = expiring_soon.filter(branch=branch)

        # العروض التي تحتاج متابعة
        need_follow_up = Quotation.objects.filter(
            follow_up_date__lte=today,
            status__in=['sent', 'negotiation'],
        ).order_by('follow_up_date')
        if branch:
            need_follow_up = need_follow_up.filter(branch=branch)

        # آخر العروض
        recent = Quotation.objects.order_by('-date')[:10]
        if branch:
            recent = Quotation.objects.filter(branch=branch).order_by('-date')[:10]

        ctx = {
            'stats': stats,
            'expiring_soon': expiring_soon[:5],
            'need_follow_up': need_follow_up[:5],
            'recent': recent,
            'status_choices': Quotation.QUOTATION_STATUSES,
        }
        return render(request, self.template_name, ctx)


# ══════════════════════════════════════════════════════
# قائمة العروض
# ══════════════════════════════════════════════════════

class QuotationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'quotations'
    permission_action = 'view'
    model = Quotation
    template_name = 'quotations/quotation_list.html'
    context_object_name = 'quotations'
    paginate_by = 25

    def get_queryset(self):
        qs = Quotation.objects.select_related('customer', 'branch', 'salesperson')
        branch = getattr(self.request, 'current_branch', None)
        if branch:
            qs = qs.filter(branch=branch)

        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        customer_id = self.request.GET.get('customer', '')
        salesperson_id = self.request.GET.get('salesperson', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if q:
            qs = qs.filter(
                Q(quotation_number__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(prospect_name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if salesperson_id:
            qs = qs.filter(salesperson_id=salesperson_id)
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)

        return qs.order_by('-date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = Quotation.QUOTATION_STATUSES
        ctx['customers'] = Customer.objects.filter(is_active=True).order_by('name')
        ctx['today'] = timezone.now().date()
        # إجماليات
        qs = self.get_queryset()
        ctx['totals'] = {
            'total': qs.count(),
            'total_value': qs.aggregate(s=Sum('total'))['s'] or 0,
        }
        return ctx


# ══════════════════════════════════════════════════════
# إنشاء عرض سعر
# ══════════════════════════════════════════════════════

class QuotationCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'create'
    template_name = 'quotations/quotation_form.html'

    def get(self, request):
        form = QuotationForm(initial={
            'branch': getattr(request, 'current_branch', None),
            'is_taxable': True,
        })
        products = Product.objects.filter(is_active=True).order_by('name')
        customers = Customer.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {
            'form': form,
            'products': products,
            'customers': customers,
            'action': 'create',
        })

    def post(self, request):
        form = QuotationForm(request.POST)
        products = Product.objects.filter(is_active=True).order_by('name')
        customers = Customer.objects.filter(is_active=True).order_by('name')

        if form.is_valid():
            data = form.cleaned_data

            # تجميع أصناف السطور من POST
            items = _parse_lines_from_post(request.POST, products)
            if not items:
                messages.error(request, 'يجب إضافة صنف واحد على الأقل')
                return render(request, self.template_name, {
                    'form': form, 'products': products, 'customers': customers, 'action': 'create',
                })

            prospect_data = None
            if not data.get('customer'):
                prospect_data = {
                    'name': data.get('prospect_name', ''),
                    'phone': data.get('prospect_phone', ''),
                    'email': data.get('prospect_email', ''),
                    'address': data.get('prospect_address', ''),
                    'company': data.get('prospect_company', ''),
                }

            try:
                qt = QuotationEngine.create_quotation(
                    customer=data.get('customer'),
                    prospect_data=prospect_data,
                    branch=data['branch'],
                    salesperson=request.user,
                    items=items,
                    valid_days=int(data.get('valid_days', 15)),
                    discount_percentage=float(data.get('discount_percentage') or 0),
                    is_taxable=data.get('is_taxable', True),
                    delivery_required=data.get('delivery_required', False),
                    delivery_fee=float(data.get('delivery_fee') or 0),
                    terms=data.get('terms_and_conditions', ''),
                    notes=data.get('customer_notes', ''),
                    user=request.user,
                )
                messages.success(request, f'تم إنشاء عرض السعر {qt.quotation_number} بنجاح')
                return redirect('quotations:quotation_detail', pk=qt.pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')

        return render(request, self.template_name, {
            'form': form, 'products': products, 'customers': customers, 'action': 'create',
        })


def _parse_lines_from_post(post_data, products_qs):
    """تحليل سطور المنتجات من بيانات POST"""
    items = []
    product_ids = post_data.getlist('line_product')
    quantities = post_data.getlist('line_quantity')
    prices = post_data.getlist('line_price')
    discounts = post_data.getlist('line_discount')
    notes_list = post_data.getlist('line_notes')

    products_dict = {str(p.pk): p for p in products_qs}

    for i, pid in enumerate(product_ids):
        if not pid:
            continue
        product = products_dict.get(str(pid))
        if not product:
            continue
        try:
            qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
            price = Decimal(prices[i]) if i < len(prices) and prices[i] else Decimal('0')
            disc = Decimal(discounts[i]) if i < len(discounts) and discounts[i] else Decimal('0')
            note = notes_list[i] if i < len(notes_list) else ''
        except Exception:
            continue
        items.append({
            'product': product,
            'quantity': qty,
            'unit_price': price,
            'discount_percentage': disc,
            'notes': note,
        })
    return items


# ══════════════════════════════════════════════════════
# تفاصيل العرض
# ══════════════════════════════════════════════════════

class QuotationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'quotations'
    permission_action = 'view'
    model = Quotation
    template_name = 'quotations/quotation_detail.html'
    context_object_name = 'quotation'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qt = self.get_object()
        ctx['lines'] = qt.lines.select_related('product').all()
        ctx['follow_ups'] = qt.follow_ups.order_by('-date')
        ctx['follow_up_form'] = FollowUpForm()
        ctx['today'] = timezone.now().date()
        return ctx


# ══════════════════════════════════════════════════════
# تعديل العرض
# ══════════════════════════════════════════════════════

class QuotationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'edit'
    template_name = 'quotations/quotation_form.html'

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = QuotationForm(initial={
            'customer': quotation.customer,
            'prospect_name': quotation.prospect_name,
            'prospect_phone': quotation.prospect_phone,
            'prospect_email': quotation.prospect_email,
            'prospect_address': quotation.prospect_address,
            'prospect_company': quotation.prospect_company,
            'branch': quotation.branch,
            'discount_percentage': quotation.discount_percentage,
            'is_taxable': quotation.is_taxable,
            'delivery_required': quotation.delivery_required,
            'delivery_fee': quotation.delivery_fee,
            'terms_and_conditions': quotation.terms_and_conditions,
            'customer_notes': quotation.customer_notes,
            'internal_notes': quotation.internal_notes,
            'payment_terms': quotation.payment_terms,
        })
        products = Product.objects.filter(is_active=True).order_by('name')
        customers = Customer.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {
            'form': form,
            'quotation': quotation,
            'existing_lines': quotation.lines.select_related('product').all(),
            'products': products,
            'customers': customers,
            'action': 'edit',
        })

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = QuotationForm(request.POST)
        products = Product.objects.filter(is_active=True).order_by('name')
        customers = Customer.objects.filter(is_active=True).order_by('name')

        if form.is_valid():
            data = form.cleaned_data
            items = _parse_lines_from_post(request.POST, products)
            if not items:
                messages.error(request, 'يجب إضافة صنف واحد على الأقل')
                return render(request, self.template_name, {
                    'form': form, 'quotation': quotation,
                    'products': products, 'customers': customers, 'action': 'edit',
                })
            try:
                QuotationEngine.revise_quotation(
                    quotation=quotation,
                    items=items,
                    discount_percentage=float(data.get('discount_percentage') or 0),
                    user=request.user,
                )
                messages.success(request, f'تم تعديل عرض السعر {quotation.quotation_number}')
                return redirect('quotations:quotation_detail', pk=quotation.pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')

        return render(request, self.template_name, {
            'form': form, 'quotation': quotation,
            'products': products, 'customers': customers, 'action': 'edit',
        })


# ══════════════════════════════════════════════════════
# قبول / رفض العرض
# ══════════════════════════════════════════════════════

class AcceptQuotationView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'edit'

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.status = 'accepted'
        quotation.updated_by = request.user
        quotation.save()
        messages.success(request, f'تم قبول عرض السعر {quotation.quotation_number}')
        return redirect('quotations:quotation_detail', pk=pk)


class RejectQuotationView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'edit'

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        reason = request.POST.get('rejection_reason', '')
        competitor = request.POST.get('lost_to_competitor', '')
        quotation.status = 'rejected'
        quotation.rejection_reason = reason
        quotation.lost_to_competitor = competitor
        quotation.updated_by = request.user
        quotation.save()
        messages.warning(request, f'تم رفض عرض السعر {quotation.quotation_number}')
        return redirect('quotations:quotation_detail', pk=pk)


# ══════════════════════════════════════════════════════
# تحويل لفاتورة
# ══════════════════════════════════════════════════════

class ConvertToInvoiceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'edit'

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        try:
            invoice = QuotationEngine.convert_to_invoice(quotation, user=request.user)
            messages.success(
                request,
                f'تم تحويل العرض إلى فاتورة {invoice.invoice_number} بنجاح'
            )
            return redirect('sales:invoice_detail', pk=invoice.pk)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'خطأ في التحويل: {e}')
        return redirect('quotations:quotation_detail', pk=pk)


# ══════════════════════════════════════════════════════
# إضافة متابعة
# ══════════════════════════════════════════════════════

class AddFollowUpView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'quotations'
    permission_action = 'edit'
    template_name = 'quotations/follow_up_form.html'

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = FollowUpForm()
        return render(request, self.template_name, {'form': form, 'quotation': quotation})

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = FollowUpForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            QuotationEngine.add_follow_up(
                quotation=quotation,
                follow_up_type=data['follow_up_type'],
                result=data['result'],
                notes=data['notes'],
                next_date=data.get('next_follow_up_date'),
                user=request.user,
            )
            messages.success(request, 'تم إضافة المتابعة بنجاح')
            return redirect('quotations:quotation_detail', pk=pk)
        return render(request, self.template_name, {'form': form, 'quotation': quotation})


# ══════════════════════════════════════════════════════
# طباعة العرض
# ══════════════════════════════════════════════════════

class QuotationPrintView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'quotations'
    permission_action = 'view'
    model = Quotation
    template_name = 'quotations/quotation_print.html'
    context_object_name = 'quotation'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qt = self.get_object()
        ctx['lines'] = qt.lines.select_related('product').all()
        ctx['today'] = timezone.now().date()
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 20 — واتساب ونسخ
# ══════════════════════════════════════════════════════

class QuotationWhatsAppView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إرسال عرض سعر بالواتساب"""
    permission_module = 'quotations'
    permission_action = 'view'

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        phone = getattr(quotation, 'customer_phone', '') or getattr(quotation, 'prospect_phone', '')
        if not phone:
            try:
                customer = getattr(quotation, 'customer', None)
                phone = getattr(customer, 'phone', '') if customer else ''
            except Exception:
                phone = ''

        # تنسيق رقم الهاتف
        phone_clean = ''.join(c for c in str(phone) if c.isdigit())
        if phone_clean.startswith('0'):
            phone_clean = '20' + phone_clean[1:]

        total = getattr(quotation, 'total', 0) or 0
        message = (
            f'مرحباً،\n'
            f'نحيطكم علماً بعرض الأسعار رقم: {quotation.quotation_number}\n'
            f'الإجمالي: {total:,.2f} ج.م\n'
            f'نرجو التواصل معنا لأي استفسار.\nشكراً لكم 🌟'
        )

        import urllib.parse
        wa_url = f'https://wa.me/{phone_clean}?text={urllib.parse.quote(message)}'

        return render(request, 'quotations/whatsapp_send.html', {
            'title': 'إرسال بالواتساب',
            'quotation': quotation,
            'wa_url': wa_url,
            'phone': phone,
            'message': message,
        })


class QuotationDuplicateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """نسخ عرض سعر"""
    permission_module = 'quotations'
    permission_action = 'create'

    def post(self, request, pk):
        original = get_object_or_404(Quotation, pk=pk)
        try:
            # نسخ العرض
            new_q = Quotation.objects.create(
                prospect_name=original.prospect_name,
                prospect_phone=getattr(original, 'prospect_phone', ''),
                customer=getattr(original, 'customer', None),
                branch=getattr(original, 'branch', None),
                valid_days=getattr(original, 'valid_days', 30),
                notes=f'نسخة من {original.quotation_number}',
                status='draft',
                subtotal=original.subtotal,
                discount_amount=original.discount_amount,
                tax_amount=original.tax_amount,
                total=original.total,
                created_by=request.user,
                updated_by=request.user,
            )
            # نسخ الأسطر
            for line in original.lines.all():
                QuotationLine.objects.create(
                    quotation=new_q,
                    product=line.product,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    discount_percentage=line.discount_percentage,
                    subtotal=line.subtotal,
                )
            messages.success(request, f'تم إنشاء نسخة جديدة: {new_q.quotation_number}')
            return redirect('quotations:quotation_detail', pk=new_q.pk)
        except Exception as e:
            messages.error(request, f'خطأ في النسخ: {e}')
            return redirect('quotations:quotation_detail', pk=pk)

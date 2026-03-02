"""
واجهات تطبيق CRM — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView, View,
)

from apps.core.mixins import BranchFilterMixin, BranchCreateMixin
from apps.core.models import Branch
from apps.crm.models import (
    CustomerGroup, Lead, Interaction, Complaint, Task, CustomerRating, SMSLog,
)
from apps.crm.services.crm_engine import CRMEngine
from apps.sales.models import Customer, SalesInvoice


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class CustomerGroupForm(forms.ModelForm):
    class Meta:
        model = CustomerGroup
        fields = ['name', 'description', 'discount_percentage', 'credit_limit', 'color', 'is_active']
        widgets = {
            'name':                forms.TextInput(attrs={'class': 'form-control'}),
            'description':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit_limit':        forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'color':               forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'is_active':           forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            'name', 'phone', 'phone2', 'email', 'company', 'address', 'governorate',
            'source', 'status', 'priority', 'estimated_value',
            'branch', 'assigned_to', 'next_follow_up', 'notes',
            'lost_reason', 'lost_to_competitor',
        ]
        widgets = {
            'name':               forms.TextInput(attrs={'class': 'form-control'}),
            'phone':              forms.TextInput(attrs={'class': 'form-control'}),
            'phone2':             forms.TextInput(attrs={'class': 'form-control'}),
            'email':              forms.EmailInput(attrs={'class': 'form-control'}),
            'company':            forms.TextInput(attrs={'class': 'form-control'}),
            'address':            forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'governorate':        forms.TextInput(attrs={'class': 'form-control'}),
            'source':             forms.Select(attrs={'class': 'form-select'}),
            'status':             forms.Select(attrs={'class': 'form-select'}),
            'priority':           forms.Select(attrs={'class': 'form-select'}),
            'estimated_value':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'branch':             forms.Select(attrs={'class': 'form-select'}),
            'assigned_to':        forms.Select(attrs={'class': 'form-select'}),
            'next_follow_up':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes':              forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'lost_reason':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'lost_to_competitor': forms.TextInput(attrs={'class': 'form-control'}),
        }


class InteractionForm(forms.ModelForm):
    class Meta:
        model = Interaction
        fields = [
            'customer', 'lead', 'interaction_type', 'result',
            'subject', 'details', 'handled_by', 'branch',
            'follow_up_required', 'follow_up_date', 'follow_up_notes',
            'satisfaction_rating',
        ]
        widgets = {
            'customer':          forms.Select(attrs={'class': 'form-select'}),
            'lead':              forms.Select(attrs={'class': 'form-select'}),
            'interaction_type':  forms.Select(attrs={'class': 'form-select'}),
            'result':            forms.Select(attrs={'class': 'form-select'}),
            'subject':           forms.TextInput(attrs={'class': 'form-control'}),
            'details':           forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'handled_by':        forms.Select(attrs={'class': 'form-select'}),
            'branch':            forms.Select(attrs={'class': 'form-select'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'follow_up_notes':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'satisfaction_rating': forms.Select(attrs={'class': 'form-select'}),
        }


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'customer', 'complaint_type', 'severity', 'subject', 'description',
            'product', 'invoice', 'branch', 'assigned_to', 'image1', 'image2',
        ]
        widgets = {
            'customer':       forms.Select(attrs={'class': 'form-select'}),
            'complaint_type': forms.Select(attrs={'class': 'form-select'}),
            'severity':       forms.Select(attrs={'class': 'form-select'}),
            'subject':        forms.TextInput(attrs={'class': 'form-control'}),
            'description':    forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'product':        forms.Select(attrs={'class': 'form-select'}),
            'invoice':        forms.Select(attrs={'class': 'form-select'}),
            'branch':         forms.Select(attrs={'class': 'form-select'}),
            'assigned_to':    forms.Select(attrs={'class': 'form-select'}),
        }


class ComplaintResolveForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['resolution', 'resolution_type', 'resolution_cost', 'customer_satisfaction', 'status']
        widgets = {
            'resolution':           forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'resolution_type':      forms.Select(attrs={'class': 'form-select'}),
            'resolution_cost':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customer_satisfaction': forms.Select(attrs={'class': 'form-select'}),
            'status':               forms.Select(attrs={'class': 'form-select'}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'assigned_to', 'due_date',
            'status', 'priority', 'customer', 'lead', 'complaint', 'branch',
        ]
        widgets = {
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':      forms.Select(attrs={'class': 'form-select'}),
            'priority':    forms.Select(attrs={'class': 'form-select'}),
            'customer':    forms.Select(attrs={'class': 'form-select'}),
            'lead':        forms.Select(attrs={'class': 'form-select'}),
            'complaint':   forms.Select(attrs={'class': 'form-select'}),
            'branch':      forms.Select(attrs={'class': 'form-select'}),
        }


# ══════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════

class CRMDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = getattr(self.request, 'current_branch', None)
        data = CRMEngine.get_crm_dashboard(branch=branch)
        ctx.update(data)

        today = timezone.now().date()
        ctx['follow_ups_today_list'] = Interaction.objects.filter(
            follow_up_date=today, is_follow_up_done=False,
        ).select_related('customer', 'lead', 'handled_by')[:20]
        ctx['overdue_list'] = Interaction.objects.filter(
            follow_up_date__lt=today, is_follow_up_done=False,
        ).select_related('customer', 'lead')[:20]
        return ctx


# ══════════════════════════════════════════════════════
# Leads
# ══════════════════════════════════════════════════════

class LeadListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    context_object_name = 'leads'
    paginate_by = 30
    branch_field = 'branch'

    def get_queryset(self):
        qs = super().get_queryset().select_related('branch', 'assigned_to')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '')
        source = self.request.GET.get('source', '')
        priority = self.request.GET.get('priority', '')
        assigned = self.request.GET.get('assigned_to', '')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if source:
            qs = qs.filter(source=source)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned:
            qs = qs.filter(assigned_to_id=assigned)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Lead.LEAD_STATUSES
        ctx['sources'] = Lead.LEAD_SOURCES
        ctx['priorities'] = Lead.PRIORITY_CHOICES
        return ctx


class LeadCreateView(LoginRequiredMixin, BranchCreateMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'crm/lead_form.html'
    success_url = reverse_lazy('crm:lead_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إضافة عميل محتمل'
        return ctx


class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'crm/lead_detail.html'
    context_object_name = 'lead'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['interactions'] = self.object.interactions.select_related('handled_by').order_by('-date')[:30]
        ctx['tasks'] = self.object.task_set.order_by('due_date')[:10]
        return ctx


class LeadUpdateView(LoginRequiredMixin, BranchCreateMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = 'crm/lead_form.html'

    def get_success_url(self):
        return reverse_lazy('crm:lead_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تعديل عميل محتمل'
        return ctx


class LeadConvertView(LoginRequiredMixin, View):
    template_name = 'crm/lead_convert.html'

    def get(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        return render(request, self.template_name, {'lead': lead})

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        customer_type = request.POST.get('customer_type', 'retail')
        try:
            customer = CRMEngine.convert_lead_to_customer(lead, customer_type=customer_type, user=request.user)
            messages.success(request, f'تم تحويل {lead.name} إلى عميل بكود {customer.code}')
            return redirect('crm:customer_profile', pk=customer.pk)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('crm:lead_detail', pk=pk)


class LeadKanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/lead_kanban.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = getattr(self.request, 'current_branch', None)
        filters = {}
        if branch:
            filters['branch'] = branch

        active_statuses = ['new', 'contacted', 'interested', 'qualified', 'negotiation']
        ctx['columns'] = {
            status: Lead.objects.filter(status=status, **filters).select_related('assigned_to')
            for status in active_statuses
        }
        ctx['status_labels'] = dict(Lead.LEAD_STATUSES)
        return ctx


# ══════════════════════════════════════════════════════
# Customer Profile
# ══════════════════════════════════════════════════════

class CustomerProfileView(LoginRequiredMixin, View):
    template_name = 'crm/customer_profile.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        rating, _ = CustomerRating.objects.get_or_create(customer=customer)

        invoices = SalesInvoice.objects.filter(customer=customer).order_by('-date')[:20]
        interactions = customer.interactions.select_related('handled_by').order_by('-date')[:20]
        complaints = customer.complaints.order_by('-date')[:10]

        return render(request, self.template_name, {
            'customer': customer,
            'rating': rating,
            'invoices': invoices,
            'interactions': interactions,
            'complaints': complaints,
        })


class CustomerSearchView(LoginRequiredMixin, View):
    template_name = 'crm/customer_search.html'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        customers = []
        if q:
            customers = Customer.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q) | Q(phone__icontains=q)
            ).filter(is_active=True)[:20]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = [{'id': c.pk, 'code': c.code, 'name': c.name, 'phone': c.phone} for c in customers]
            return JsonResponse({'results': data})

        return render(request, self.template_name, {'customers': customers, 'query': q})


# ══════════════════════════════════════════════════════
# Interactions
# ══════════════════════════════════════════════════════

class InteractionListView(LoginRequiredMixin, ListView):
    model = Interaction
    template_name = 'crm/interaction_list.html'
    context_object_name = 'interactions'
    paginate_by = 30

    def get_queryset(self):
        qs = Interaction.objects.select_related('customer', 'lead', 'handled_by', 'branch').order_by('-date')
        customer_id = self.request.GET.get('customer', '')
        itype = self.request.GET.get('type', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if itype:
            qs = qs.filter(interaction_type=itype)
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)
        # Branch filter
        branch = getattr(self.request, 'current_branch', None)
        can_see_all = getattr(self.request, 'can_see_all_branches', False)
        if not can_see_all and branch:
            qs = qs.filter(branch=branch)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['interaction_types'] = Interaction.INTERACTION_TYPES
        return ctx


class InteractionCreateView(LoginRequiredMixin, CreateView):
    model = Interaction
    form_class = InteractionForm
    template_name = 'crm/interaction_form.html'
    success_url = reverse_lazy('crm:interaction_list')

    def form_valid(self, form):
        form.instance.date = timezone.now()
        form.instance.handled_by = self.request.user
        form.instance.branch = getattr(self.request, 'current_branch', None)
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class FollowUpListView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/follow_up_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        base_qs = Interaction.objects.filter(
            follow_up_required=True, is_follow_up_done=False
        ).select_related('customer', 'lead', 'handled_by')

        ctx['today_list'] = base_qs.filter(follow_up_date=today)
        ctx['overdue_list'] = base_qs.filter(follow_up_date__lt=today).order_by('follow_up_date')
        ctx['upcoming_list'] = base_qs.filter(follow_up_date__gt=today).order_by('follow_up_date')[:30]
        return ctx


@login_required
def mark_follow_up_done(request, pk):
    interaction = get_object_or_404(Interaction, pk=pk)
    interaction.is_follow_up_done = True
    interaction.save()
    messages.success(request, 'تم تأشير المتابعة كمكتملة')
    return redirect('crm:follow_up_list')


# ══════════════════════════════════════════════════════
# Complaints
# ══════════════════════════════════════════════════════

class ComplaintListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = Complaint
    template_name = 'crm/complaint_list.html'
    context_object_name = 'complaints'
    paginate_by = 30
    branch_field = 'branch'

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'branch', 'assigned_to')
        status = self.request.GET.get('status', '')
        severity = self.request.GET.get('severity', '')
        ctype = self.request.GET.get('type', '')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if severity:
            qs = qs.filter(severity=severity)
        if ctype:
            qs = qs.filter(complaint_type=ctype)
        if q:
            qs = qs.filter(Q(complaint_number__icontains=q) | Q(subject__icontains=q) | Q(customer__name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Complaint.COMPLAINT_STATUSES
        ctx['severities'] = Complaint.SEVERITY_CHOICES
        ctx['types'] = Complaint.COMPLAINT_TYPES
        return ctx


class ComplaintCreateView(LoginRequiredMixin, View):
    template_name = 'crm/complaint_form.html'

    def get(self, request):
        form = ComplaintForm()
        return render(request, self.template_name, {'form': form, 'title': 'شكوى جديدة'})

    def post(self, request):
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            complaint = CRMEngine.create_complaint(
                customer=cd['customer'],
                complaint_type=cd['complaint_type'],
                subject=cd['subject'],
                description=cd['description'],
                branch=cd['branch'] or getattr(request, 'current_branch', None),
                severity=cd.get('severity', 'medium'),
                product=cd.get('product'),
                invoice=cd.get('invoice'),
                assigned_to=cd.get('assigned_to'),
                user=request.user,
            )
            if cd.get('image1'):
                complaint.image1 = cd['image1']
                complaint.save()
            if cd.get('image2'):
                complaint.image2 = cd['image2']
                complaint.save()
            messages.success(request, f'تم إنشاء الشكوى {complaint.complaint_number}')
            return redirect('crm:complaint_detail', pk=complaint.pk)
        return render(request, self.template_name, {'form': form, 'title': 'شكوى جديدة'})


class ComplaintDetailView(LoginRequiredMixin, DetailView):
    model = Complaint
    template_name = 'crm/complaint_detail.html'
    context_object_name = 'complaint'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tasks'] = self.object.task_set.order_by('due_date')
        return ctx


class ComplaintResolveView(LoginRequiredMixin, View):
    template_name = 'crm/complaint_resolve.html'

    def get(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        form = ComplaintResolveForm(instance=complaint)
        return render(request, self.template_name, {'form': form, 'complaint': complaint})

    def post(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        form = ComplaintResolveForm(request.POST, instance=complaint)
        if form.is_valid():
            CRMEngine.resolve_complaint(
                complaint=complaint,
                resolution=form.cleaned_data['resolution'],
                resolution_type=form.cleaned_data['resolution_type'],
                resolution_cost=form.cleaned_data.get('resolution_cost', 0),
                user=request.user,
            )
            messages.success(request, 'تم حل الشكوى بنجاح')
            return redirect('crm:complaint_detail', pk=pk)
        return render(request, self.template_name, {'form': form, 'complaint': complaint})


# ══════════════════════════════════════════════════════
# Tasks
# ══════════════════════════════════════════════════════

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'crm/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 30

    def get_queryset(self):
        qs = Task.objects.select_related('assigned_to', 'assigned_by', 'customer', 'lead')
        status = self.request.GET.get('status', '')
        priority = self.request.GET.get('priority', '')
        assigned = self.request.GET.get('assigned_to', '')
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned:
            qs = qs.filter(assigned_to_id=assigned)
        else:
            # Default: show current user's tasks
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Task.TASK_STATUSES
        ctx['priorities'] = [('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'مرتفع'), ('urgent', 'عاجل')]
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'crm/task_form.html'
    success_url = reverse_lazy('crm:task_list')

    def form_valid(self, form):
        form.instance.assigned_by = self.request.user
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class TaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.completion_notes = request.POST.get('notes', '')
        task.updated_by = request.user
        task.save()
        messages.success(request, 'تم إكمال المهمة')
        return redirect('crm:task_list')


# ══════════════════════════════════════════════════════
# Customer Groups
# ══════════════════════════════════════════════════════

class CustomerGroupListView(LoginRequiredMixin, ListView):
    model = CustomerGroup
    template_name = 'crm/group_list.html'
    context_object_name = 'groups'
    queryset = CustomerGroup.objects.filter(is_deleted=False)


class CustomerGroupCreateView(LoginRequiredMixin, BranchCreateMixin, CreateView):
    model = CustomerGroup
    form_class = CustomerGroupForm
    template_name = 'crm/group_form.html'
    success_url = reverse_lazy('crm:group_list')


# ══════════════════════════════════════════════════════
# Reports
# ══════════════════════════════════════════════════════

class CustomerRatingReportView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/rating_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grade = self.request.GET.get('grade', '')
        qs = CustomerRating.objects.select_related('customer').order_by('-score')
        if grade:
            qs = qs.filter(grade=grade)
        ctx['ratings'] = qs
        grade_defs = [('A+', 'ممتاز'), ('A', 'جيد جداً'), ('B', 'جيد'), ('C', 'متوسط'), ('D', 'ضعيف'), ('F', 'سيء')]
        ctx['grades'] = grade_defs
        ctx['grade_summary'] = [
            {'grade': g, 'label': l, 'count': CustomerRating.objects.filter(grade=g).count()}
            for g, l in grade_defs
        ]
        return ctx


class LeadSourceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/lead_source_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = getattr(self.request, 'current_branch', None)
        filters = {}
        if branch:
            filters['branch'] = branch

        source_data = (
            Lead.objects.filter(**filters)
            .values('source')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        source_labels = dict(Lead.LEAD_SOURCES)
        ctx['source_data'] = [
            {'source': s['source'], 'label': source_labels.get(s['source'], s['source']), 'count': s['count']}
            for s in source_data
        ]
        total = sum(s['count'] for s in ctx['source_data'])
        ctx['total'] = total
        for item in ctx['source_data']:
            item['pct'] = round(item['count'] / total * 100, 1) if total else 0

        # Status breakdown
        ctx['status_data'] = (
            Lead.objects.filter(**filters)
            .values('status')
            .annotate(count=Count('id'))
        )
        return ctx


class SalesmanPerformanceView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/salesman_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = getattr(self.request, 'current_branch', None)
        filters = {}
        if branch:
            filters['branch'] = branch

        from apps.core.models import User
        salesmen = User.objects.filter(is_active=True)
        data = []
        for user in salesmen:
            total_leads = Lead.objects.filter(assigned_to=user, **filters).count()
            won_leads = Lead.objects.filter(assigned_to=user, status='won', **filters).count()
            data.append({
                'user': user,
                'total_leads': total_leads,
                'won_leads': won_leads,
                'conversion_rate': round(won_leads / total_leads * 100, 1) if total_leads else 0,
                'interactions': Interaction.objects.filter(handled_by=user).count(),
                'open_tasks': Task.objects.filter(assigned_to=user, status__in=['pending', 'in_progress']).count(),
            })
        ctx['salesmen'] = sorted(data, key=lambda x: x['won_leads'], reverse=True)
        return ctx

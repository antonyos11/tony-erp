from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from crm.models import (
    Customer, CustomerType, CustomerSource, ContactPerson,
    Opportunity, OpportunityStage, Activity, ActivityType,
    Quotation, QuotationItem, SupportTicket, TicketCategory,
    Campaign, CampaignResponse
)
from crm.serializers import (
    CustomerSerializer, CustomerListSerializer, CustomerTypeSerializer, CustomerSourceSerializer,
    ContactPersonSerializer, OpportunitySerializer, OpportunityListSerializer, OpportunityStageSerializer,
    ActivitySerializer, ActivityListSerializer, ActivityTypeSerializer,
    QuotationSerializer, QuotationListSerializer, QuotationItemSerializer,
    SupportTicketSerializer, SupportTicketListSerializer, TicketCategorySerializer,
    CampaignSerializer, CampaignListSerializer, CampaignResponseSerializer,
    CustomerStatsSerializer, OpportunityStatsSerializer, ActivityStatsSerializer,
    SalesStatsSerializer, CRMDashboardSerializer
)
from showrooms.mixins import scope_queryset_to_active_showroom

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        return CustomerSerializer
    
    def get_queryset(self):
        queryset = Customer.objects.select_related(
            'customer_type', 'source', 'assigned_to'
        ).prefetch_related('contacts')
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب الحالة
        status_filter = getattr(self.request, "query_params", self.request.GET).get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # تصفية حسب نوع العميل
        customer_type = getattr(self.request, "query_params", self.request.GET).get('customer_type', None)
        if customer_type:
            queryset = queryset.filter(customer_type_id=customer_type)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(
                Q(customer_code__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # إنشاء كود العميل تلقائياً
        import re
        
        # محاولة البحث عن آخر كود يبدأ بـ C ومتبوع بأرقام فقط
        last_customer = Customer.objects.filter(
            customer_code__regex=r'^C\d+$'
        ).order_by('-customer_code').first()
        
        if last_customer:
            try:
                # استخراج الرقم وتجاهل الحرف C
                digits = re.findall(r'\d+', last_customer.customer_code)
                if digits:
                    last_code = int(digits[0])
                    customer_code = f'C{last_code + 1:06d}'
                else:
                    customer_code = 'C000001'
            except (ValueError, IndexError):
                customer_code = 'C000001'
        else:
            # التحقق مما إذا كان هناك نظام ترقيم آخر (مثل CUS) لتجنب التكرار
            if Customer.objects.exists():
                # إذا كانت هناك عملاء ولكن ليس بنظام Cxxxxx، نبدأ من C000001
                # ولكن نتأكد من عدم وجوده (احتياطاً)
                code = 'C000001'
                counter = 1
                while Customer.objects.filter(customer_code=code).exists():
                    counter += 1
                    code = f'C{counter:06d}'
                customer_code = code
            else:
                customer_code = 'C000001'
        
        serializer.save(customer_code=customer_code)
    
    @action(detail=True, methods=['get'])
    def opportunities(self, request, pk=None):
        """الحصول على فرص العميل"""
        customer = self.get_object()
        opportunities = customer.opportunity_set.all()
        serializer = OpportunityListSerializer(opportunities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """الحصول على أنشطة العميل"""
        customer = self.get_object()
        activities = customer.activity_set.all()
        serializer = ActivityListSerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def quotations(self, request, pk=None):
        """الحصول على عروض أسعار العميل"""
        customer = self.get_object()
        quotations = customer.quotation_set.all()
        serializer = QuotationListSerializer(quotations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """الحصول على تذاكر دعم العميل"""
        customer = self.get_object()
        tickets = customer.supportticket_set.all()
        serializer = SupportTicketListSerializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات العملاء"""
        current_month = timezone.now().replace(day=1)
        
        total_customers = Customer.objects.count()
        active_customers = Customer.objects.filter(status='active').count()
        new_customers_this_month = Customer.objects.filter(
            created_at__gte=current_month, status='active'
        ).count()
        
        customers_by_type = list(Customer.objects.filter(status='active').values(
            'customer_type__name'
        ).annotate(count=Count('id')))
        
        customers_by_source = list(Customer.objects.filter(status='active').values(
            'source__name'
        ).annotate(count=Count('id')))
        
        stats_data = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'new_customers_this_month': new_customers_this_month,
            'customers_by_type': customers_by_type,
            'customers_by_source': customers_by_source,
        }
        
        serializer = CustomerStatsSerializer(stats_data)
        return Response(serializer.data)

class CustomerTypeViewSet(viewsets.ModelViewSet):
    queryset = CustomerType.objects.all()
    serializer_class = CustomerTypeSerializer
    permission_classes = [IsAuthenticated]

class CustomerSourceViewSet(viewsets.ModelViewSet):
    queryset = CustomerSource.objects.filter(is_active=True)
    serializer_class = CustomerSourceSerializer
    permission_classes = [IsAuthenticated]

class ContactPersonViewSet(viewsets.ModelViewSet):
    queryset = ContactPerson.objects.all()
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ContactPerson.objects.select_related('customer')
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        customer_id = getattr(self.request, "query_params", self.request.GET).get('customer', None)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset.order_by('-created_at')

class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = Opportunity.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OpportunityListSerializer
        return OpportunitySerializer
    
    def get_queryset(self):
        queryset = Opportunity.objects.select_related(
            'customer', 'stage', 'assigned_to', 'contact_person'
        )
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب المرحلة
        stage = getattr(self.request, "query_params", self.request.GET).get('stage', None)
        if stage:
            queryset = queryset.filter(stage_id=stage)
        
        # تصفية حسب العميل
        customer = getattr(self.request, "query_params", self.request.GET).get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        # تصفية حسب المسؤول
        assigned_to = getattr(self.request, "query_params", self.request.GET).get('assigned_to', None)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def kanban(self, request):
        """عرض الفرص بتنسيق Kanban"""
        stages = OpportunityStage.objects.order_by('order')
        kanban_data = []
        
        for stage in stages:
            opportunities = Opportunity.objects.filter(
                stage=stage
            ).select_related('customer', 'assigned_to')[:20]
            
            serializer = OpportunityListSerializer(opportunities, many=True)
            kanban_data.append({
                'stage': {
                    'id': stage.id,
                    'name': stage.name,
                    'probability': stage.probability
                },
                'opportunities': serializer.data,
                'total_value': sum(opp.estimated_value for opp in opportunities)
            })
        
        return Response(kanban_data)
    
    @action(detail=True, methods=['patch'])
    def update_stage(self, request, pk=None):
        """تحديث مرحلة الفرصة"""
        opportunity = self.get_object()
        stage_id = request.data.get('stage_id')
        
        if stage_id:
            try:
                stage = OpportunityStage.objects.get(id=stage_id)
                opportunity.stage = stage
                opportunity.probability = stage.probability
                
                if stage.is_won or stage.is_lost:
                    opportunity.closed_at = timezone.now()
                
                opportunity.save()
                
                serializer = OpportunitySerializer(opportunity)
                return Response(serializer.data)
            except OpportunityStage.DoesNotExist:
                return Response(
                    {'error': 'المرحلة غير موجودة'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'error': 'stage_id مطلوب'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات الفرص"""
        total_opportunities = Opportunity.objects.count()
        open_opportunities = Opportunity.objects.filter(
            stage__is_won=False, stage__is_lost=False
        ).count()
        won_opportunities = Opportunity.objects.filter(stage__is_won=True).count()
        lost_opportunities = Opportunity.objects.filter(stage__is_lost=True).count()
        
        total_value = Opportunity.objects.aggregate(
            total=Sum('estimated_value')
        )['total'] or 0
        
        won_value = Opportunity.objects.filter(stage__is_won=True).aggregate(
            total=Sum('estimated_value')
        )['total'] or 0
        
        conversion_rate = 0
        if total_opportunities > 0:
            conversion_rate = (won_opportunities / total_opportunities) * 100
        
        opportunities_by_stage = list(
            Opportunity.objects.values('stage__name').annotate(
                count=Count('id'),
                total_value=Sum('estimated_value')
            )
        )
        
        stats_data = {
            'total_opportunities': total_opportunities,
            'open_opportunities': open_opportunities,
            'won_opportunities': won_opportunities,
            'lost_opportunities': lost_opportunities,
            'total_value': total_value,
            'won_value': won_value,
            'conversion_rate': conversion_rate,
            'opportunities_by_stage': opportunities_by_stage,
        }
        
        serializer = OpportunityStatsSerializer(stats_data)
        return Response(serializer.data)

class OpportunityStageViewSet(viewsets.ModelViewSet):
    queryset = OpportunityStage.objects.all().order_by('order')
    serializer_class = OpportunityStageSerializer
    permission_classes = [IsAuthenticated]

class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ActivityListSerializer
        return ActivitySerializer
    
    def get_queryset(self):
        queryset = Activity.objects.select_related(
            'customer', 'activity_type', 'assigned_to', 'opportunity'
        )
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب العميل
        customer = getattr(self.request, "query_params", self.request.GET).get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        # تصفية حسب نوع النشاط
        activity_type = getattr(self.request, "query_params", self.request.GET).get('activity_type', None)
        if activity_type:
            queryset = queryset.filter(activity_type_id=activity_type)
        
        # تصفية حسب الحالة
        status_filter = getattr(self.request, "query_params", self.request.GET).get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return queryset.order_by('-scheduled_date')
    
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """أنشطة التقويم"""
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        
        queryset = self.get_queryset()
        
        if start_date and end_date:
            queryset = queryset.filter(
                scheduled_date__date__range=[start_date, end_date]
            )
        
        activities = queryset.select_related('customer', 'activity_type')
        calendar_events = []
        
        for activity in activities:
            calendar_events.append({
                'id': activity.id,
                'title': activity.title,
                'start': activity.scheduled_date.isoformat(),
                'end': (activity.scheduled_date + timedelta(
                    minutes=activity.duration_minutes
                )).isoformat(),
                'backgroundColor': activity.activity_type.color if activity.activity_type.color else '#007bff',
                'customer': activity.customer.full_name if activity.customer else None,
                'status': activity.status,
                'priority': activity.priority
            })
        
        return Response(calendar_events)
    
    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        """إكمال النشاط"""
        activity = self.get_object()
        activity.status = 'completed'
        activity.completed_at = timezone.now()
        activity.outcome = request.data.get('outcome', '')
        activity.save()
        
        serializer = ActivitySerializer(activity)
        return Response(serializer.data)

class ActivityTypeViewSet(viewsets.ModelViewSet):
    queryset = ActivityType.objects.all()
    serializer_class = ActivityTypeSerializer
    permission_classes = [IsAuthenticated]

class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return QuotationListSerializer
        return QuotationSerializer
    
    def get_queryset(self):
        queryset = Quotation.objects.select_related(
            'customer', 'opportunity', 'prepared_by'
        ).prefetch_related('items__product')
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب العميل
        customer = getattr(self.request, "query_params", self.request.GET).get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        # تصفية حسب الحالة
        status_filter = getattr(self.request, "query_params", self.request.GET).get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(
                Q(quotation_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # إنشاء رقم عرض السعر تلقائياً
        import re
        
        last_quotation = Quotation.objects.filter(
            quotation_number__regex=r'^Q\d+$'
        ).order_by('-quotation_number').first()
        
        if last_quotation:
            try:
                digits = re.findall(r'\d+', last_quotation.quotation_number)
                if digits:
                    last_number = int(digits[0])
                    quotation_number = f'Q{last_number + 1:06d}'
                else:
                    quotation_number = 'Q000001'
            except (ValueError, IndexError):
                quotation_number = 'Q000001'
        else:
            if Quotation.objects.exists():
                code = 'Q000001'
                counter = 1
                while Quotation.objects.filter(quotation_number=code).exists():
                    counter += 1
                    code = f'Q{counter:06d}'
                quotation_number = code
            else:
                quotation_number = 'Q000001'
        
        serializer.save(
            quotation_number=quotation_number,
            prepared_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def calculate_totals(self, request, pk=None):
        """حساب المجاميع"""
        quotation = self.get_object()
        quotation.calculate_totals()
        
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """تحديث حالة العرض"""
        quotation = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in ['sent', 'accepted', 'rejected', 'expired']:
            quotation.status = new_status
            if new_status in ['accepted', 'rejected']:
                quotation.responded_at = timezone.now()
            quotation.save()
            
            serializer = QuotationSerializer(quotation)
            return Response(serializer.data)
        
        return Response(
            {'error': 'حالة غير صحيحة'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SupportTicketListSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        queryset = SupportTicket.objects.select_related(
            'customer', 'category', 'assigned_to', 'created_by'
        )
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب العميل
        customer = getattr(self.request, "query_params", self.request.GET).get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        # تصفية حسب الحالة
        status_filter = getattr(self.request, "query_params", self.request.GET).get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # تصفية حسب الأولوية
        priority = getattr(self.request, "query_params", self.request.GET).get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(
                Q(ticket_number__icontains=search) |
                Q(title__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # إنشاء رقم التذكرة تلقائياً
        import re
        
        last_ticket = SupportTicket.objects.filter(
            ticket_number__regex=r'^T\d+$'
        ).order_by('-ticket_number').first()
        
        if last_ticket:
            try:
                digits = re.findall(r'\d+', last_ticket.ticket_number)
                if digits:
                    last_number = int(digits[0])
                    ticket_number = f'T{last_number + 1:06d}'
                else:
                    ticket_number = 'T000001'
            except (ValueError, IndexError):
                ticket_number = 'T000001'
        else:
            if SupportTicket.objects.exists():
                code = 'T000001'
                counter = 1
                while SupportTicket.objects.filter(ticket_number=code).exists():
                    counter += 1
                    code = f'T{counter:06d}'
                ticket_number = code
            else:
                ticket_number = 'T000001'
        
        serializer.save(
            ticket_number=ticket_number,
            created_by=self.request.user
        )

class TicketCategoryViewSet(viewsets.ModelViewSet):
    queryset = TicketCategory.objects.all()
    serializer_class = TicketCategorySerializer
    permission_classes = [IsAuthenticated]

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CampaignListSerializer
        return CampaignSerializer
    
    def get_queryset(self):
        queryset = Campaign.objects.select_related('created_by', 'customer_type')
        queryset = scope_queryset_to_active_showroom(self.request, queryset)
        
        # تصفية حسب نوع الحملة
        campaign_type = getattr(self.request, "query_params", self.request.GET).get('campaign_type', None)
        if campaign_type:
            queryset = queryset.filter(campaign_type=campaign_type)
        
        # تصفية حسب الحالة
        status_filter = getattr(self.request, "query_params", self.request.GET).get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # البحث
        search = getattr(self.request, "query_params", self.request.GET).get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CRMDashboardView(viewsets.GenericViewSet):
    """Dashboard view for CRM statistics and analytics"""
    permission_classes = [IsAuthenticated]
    serializer_class = CRMDashboardSerializer  # Required for drf-spectacular
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات شاملة لـ CRM"""
        current_month = timezone.now().replace(day=1)
        
        # إحصائيات العملاء
        customer_stats = {
            'total_customers': Customer.objects.count(),
            'active_customers': Customer.objects.filter(status='active').count(),
            'new_customers_this_month': Customer.objects.filter(
                created_at__gte=current_month, status='active'
            ).count(),
            'customers_by_type': list(Customer.objects.filter(status='active').values(
                'customer_type__name'
            ).annotate(count=Count('id'))),
            'customers_by_source': list(Customer.objects.filter(status='active').values(
                'source__name'
            ).annotate(count=Count('id'))),
        }
        
        # إحصائيات الفرص
        total_opportunities = Opportunity.objects.count()
        won_opportunities = Opportunity.objects.filter(stage__is_won=True).count()
        
        opportunity_stats = {
            'total_opportunities': total_opportunities,
            'open_opportunities': Opportunity.objects.filter(
                stage__is_won=False, stage__is_lost=False
            ).count(),
            'won_opportunities': won_opportunities,
            'lost_opportunities': Opportunity.objects.filter(stage__is_lost=True).count(),
            'total_value': Opportunity.objects.aggregate(
                total=Sum('estimated_value')
            )['total'] or 0,
            'won_value': Opportunity.objects.filter(stage__is_won=True).aggregate(
                total=Sum('estimated_value')
            )['total'] or 0,
            'conversion_rate': (won_opportunities / total_opportunities * 100) if total_opportunities > 0 else 0,
            'opportunities_by_stage': list(
                Opportunity.objects.values('stage__name').annotate(
                    count=Count('id'),
                    total_value=Sum('estimated_value')
                )
            ),
        }
        
        # إحصائيات الأنشطة
        activity_stats = {
            'total_activities': Activity.objects.count(),
            'completed_activities': Activity.objects.filter(status='completed').count(),
            'overdue_activities': Activity.objects.filter(
                scheduled_date__lt=timezone.now(),
                status__in=['planned', 'in_progress']
            ).count(),
            'activities_this_week': Activity.objects.filter(
                scheduled_date__date__gte=timezone.now().date(),
                scheduled_date__date__lt=timezone.now().date() + timedelta(days=7)
            ).count(),
            'activities_by_type': list(
                Activity.objects.values('activity_type__name').annotate(count=Count('id'))
            ),
        }
        
        # إحصائيات المبيعات
        total_quotations = Quotation.objects.count()
        accepted_quotations = Quotation.objects.filter(status='accepted').count()
        
        sales_stats = {
            'total_quotations': total_quotations,
            'accepted_quotations': accepted_quotations,
            'quotations_value': Quotation.objects.aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'conversion_rate': (accepted_quotations / total_quotations * 100) if total_quotations > 0 else 0,
        }
        
        # الأنشطة الأخيرة
        recent_activities = Activity.objects.filter(
            scheduled_date__date__gte=timezone.now().date(),
            scheduled_date__date__lt=timezone.now().date() + timedelta(days=7)
        ).select_related('customer', 'activity_type')[:10]
        
        # الفرص المتأخرة
        overdue_opportunities = Opportunity.objects.filter(
            expected_close_date__lt=timezone.now().date(),
            stage__is_won=False,
            stage__is_lost=False
        ).select_related('customer', 'stage')[:10]
        
        dashboard_data = {
            'customer_stats': customer_stats,
            'opportunity_stats': opportunity_stats,
            'activity_stats': activity_stats,
            'sales_stats': sales_stats,
            'recent_activities': ActivityListSerializer(recent_activities, many=True).data,
            'overdue_opportunities': OpportunityListSerializer(overdue_opportunities, many=True).data,
        }
        
        serializer = CRMDashboardSerializer(dashboard_data)
        return Response(serializer.data)
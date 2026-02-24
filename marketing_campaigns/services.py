"""
خدمات الحملات التسويقية
Marketing Campaign Services
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from typing import Dict, List

from .models import Campaign, CampaignMessage, CustomerSegment, ABTest, CampaignROI


class CampaignService:
    """خدمة إدارة الحملات"""
    
    @staticmethod
    def create_campaign(name: str, campaign_type: str, start_date, end_date, 
                       budget: Decimal, segments: List, channels: List, **kwargs) -> Campaign:
        """إنشاء حملة جديدة"""
        campaign = Campaign.objects.create(
            name=name,
            campaign_type=campaign_type,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            channels=channels,
            **kwargs
        )
        
        # إضافة الشرائح المستهدفة
        campaign.target_segments.set(segments)
        
        # حساب حجم الجمهور المستهدف
        total_customers = sum(segment.customer_count for segment in segments)
        campaign.target_audience_size = total_customers
        campaign.save()
        
        return campaign
    
    @staticmethod
    def send_campaign_messages(campaign: Campaign, message_type: str = 'email'):
        """إرسال رسائل الحملة"""
        from crm.models import Customer
        
        # الحصول على العملاء المستهدفين
        customers = Customer.objects.filter(
            segment__in=campaign.target_segments.all()
        ).distinct()
        
        messages_created = 0
        for customer in customers:
            # إنشاء رسالة لكل عميل
            message = CampaignMessage.objects.create(
                campaign=campaign,
                customer=customer,
                message_type=message_type,
                content=campaign.message_template,
                status='pending'
            )
            messages_created += 1
        
        campaign.total_sent = messages_created
        campaign.status = 'active'
        campaign.save()
        
        return messages_created
    
    @staticmethod
    def track_campaign_performance(campaign: Campaign) -> Dict:
        """تتبع أداء الحملة"""
        messages = campaign.messages.all()
        
        # حساب المقاييس
        total_sent = messages.count()
        total_delivered = messages.filter(status__in=['delivered', 'opened', 'clicked', 'converted']).count()
        total_opened = messages.filter(status__in=['opened', 'clicked', 'converted']).count()
        total_clicked = messages.filter(status__in=['clicked', 'converted']).count()
        total_conversions = messages.filter(status='converted').count()
        
        # حساب الإيرادات
        total_revenue = messages.filter(
            status='converted'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        # تحديث الحملة
        campaign.total_sent = total_sent
        campaign.total_delivered = total_delivered
        campaign.total_opened = total_opened
        campaign.total_clicked = total_clicked
        campaign.total_conversions = total_conversions
        campaign.total_revenue = total_revenue
        campaign.calculate_metrics()
        
        return {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_conversions': total_conversions,
            'total_revenue': total_revenue,
            'conversion_rate': campaign.conversion_rate,
            'roi': campaign.roi,
        }
    
    @staticmethod
    def compare_campaigns(campaign_ids: List[int]) -> Dict:
        """مقارنة الحملات"""
        campaigns = Campaign.objects.filter(id__in=campaign_ids)
        
        comparison = []
        for campaign in campaigns:
            comparison.append({
                'name': campaign.name,
                'budget': campaign.budget,
                'actual_cost': campaign.actual_cost,
                'total_sent': campaign.total_sent,
                'conversions': campaign.total_conversions,
                'conversion_rate': campaign.conversion_rate,
                'revenue': campaign.total_revenue,
                'roi': campaign.roi,
            })
        
        return {
            'campaigns': comparison,
            'best_roi': max(comparison, key=lambda x: x['roi']) if comparison else None,
            'best_conversion_rate': max(comparison, key=lambda x: x['conversion_rate']) if comparison else None,
        }


class SegmentationService:
    """خدمة تقسيم العملاء"""
    
    @staticmethod
    def create_segment_by_value(name: str, min_revenue: Decimal = None, 
                               max_revenue: Decimal = None) -> CustomerSegment:
        """إنشاء شريحة حسب قيمة العميل"""
        from crm.models import Customer
        from django.db.models import Sum
        
        # الحصول على العملاء
        customers_query = Customer.objects.annotate(
            total_revenue=Sum('orders__total_amount')
        )
        
        if min_revenue:
            customers_query = customers_query.filter(total_revenue__gte=min_revenue)
        if max_revenue:
            customers_query = customers_query.filter(total_revenue__lte=max_revenue)
        
        customer_count = customers_query.count()
        total_revenue = customers_query.aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
        avg_order_value = total_revenue / customer_count if customer_count > 0 else Decimal('0')
        
        segment = CustomerSegment.objects.create(
            name=name,
            segment_type='value_based',
            criteria={
                'min_revenue': str(min_revenue) if min_revenue else None,
                'max_revenue': str(max_revenue) if max_revenue else None,
            },
            customer_count=customer_count,
            total_revenue=total_revenue,
            average_order_value=avg_order_value,
        )
        
        return segment
    
    @staticmethod
    def create_segment_by_behavior(name: str, min_orders: int = None, 
                                   last_purchase_days: int = None) -> CustomerSegment:
        """إنشاء شريحة حسب السلوك"""
        from crm.models import Customer
        from django.db.models import Count, Max
        
        customers_query = Customer.objects.annotate(
            order_count=Count('orders'),
            last_order_date=Max('orders__order_date')
        )
        
        if min_orders:
            customers_query = customers_query.filter(order_count__gte=min_orders)
        
        if last_purchase_days:
            cutoff_date = timezone.now().date() - timedelta(days=last_purchase_days)
            customers_query = customers_query.filter(last_order_date__gte=cutoff_date)
        
        customer_count = customers_query.count()
        
        segment = CustomerSegment.objects.create(
            name=name,
            segment_type='behavioral',
            criteria={
                'min_orders': min_orders,
                'last_purchase_days': last_purchase_days,
            },
            customer_count=customer_count,
        )
        
        return segment


class ABTestService:
    """خدمة اختبارات A/B"""
    
    @staticmethod
    def create_ab_test(campaign: Campaign, name: str, 
                      variant_a_content: str, variant_b_content: str) -> ABTest:
        """إنشاء اختبار A/B"""
        ab_test = ABTest.objects.create(
            campaign=campaign,
            name=name,
            variant_a_content=variant_a_content,
            variant_b_content=variant_b_content,
        )
        
        return ab_test
    
    @staticmethod
    def assign_variant(ab_test: ABTest, customer) -> str:
        """تعيين نسخة للعميل (A أو B)"""
        import random
        
        # توزيع عشوائي 50/50
        variant = random.choice(['A', 'B'])
        
        if variant == 'A':
            ab_test.variant_a_sent += 1
        else:
            ab_test.variant_b_sent += 1
        
        ab_test.save()
        
        return variant
    
    @staticmethod
    def record_conversion(ab_test: ABTest, variant: str):
        """تسجيل تحويل"""
        if variant == 'A':
            ab_test.variant_a_conversions += 1
        else:
            ab_test.variant_b_conversions += 1
        
        ab_test.calculate_winner()


class ROIAnalysisService:
    """خدمة تحليل العائد على الاستثمار"""
    
    @staticmethod
    def calculate_campaign_roi(campaign: Campaign, 
                              creative_cost: Decimal = Decimal('0'),
                              platform_cost: Decimal = Decimal('0'),
                              media_cost: Decimal = Decimal('0'),
                              staff_cost: Decimal = Decimal('0')) -> CampaignROI:
        """حساب ROI للحملة"""
        
        roi_analysis, created = CampaignROI.objects.get_or_create(
            campaign=campaign,
            defaults={
                'creative_cost': creative_cost,
                'platform_cost': platform_cost,
                'media_cost': media_cost,
                'staff_cost': staff_cost,
            }
        )
        
        if not created:
            roi_analysis.creative_cost = creative_cost
            roi_analysis.platform_cost = platform_cost
            roi_analysis.media_cost = media_cost
            roi_analysis.staff_cost = staff_cost
        
        # تحديث الإيرادات
        roi_analysis.direct_revenue = campaign.total_revenue
        roi_analysis.calculate_roi()
        
        return roi_analysis
    
    @staticmethod
    def get_best_performing_campaigns(limit: int = 10) -> List[Campaign]:
        """الحصول على أفضل الحملات أداءً"""
        campaigns = Campaign.objects.filter(
            status='completed',
            total_conversions__gt=0
        ).order_by('-roi')[:limit]
        
        return list(campaigns)
    
    @staticmethod
    def get_marketing_dashboard() -> Dict:
        """لوحة معلومات التسويق"""
        active_campaigns = Campaign.objects.filter(status='active').count()
        completed_campaigns = Campaign.objects.filter(status='completed').count()
        
        total_spent = Campaign.objects.filter(
            status__in=['active', 'completed']
        ).aggregate(total=Sum('actual_cost'))['total'] or Decimal('0')
        
        total_revenue = Campaign.objects.filter(
            status__in=['active', 'completed']
        ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
        
        avg_roi = Campaign.objects.filter(
            status='completed',
            roi__gt=0
        ).aggregate(avg=Avg('roi'))['avg'] or Decimal('0')
        
        return {
            'active_campaigns': active_campaigns,
            'completed_campaigns': completed_campaigns,
            'total_spent': total_spent,
            'total_revenue': total_revenue,
            'net_profit': total_revenue - total_spent,
            'average_roi': avg_roi,
        }

"""
Web Views لصفحات السوشيال ميديا و CRM
صفحات مستقلة خارج Django Admin
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from urllib.parse import unquote
from .models import (
    SocialConversation, SocialMessage, 
    SocialPlatformConfig, ProductKnowledgeBase, ExcludedCategory
)
from crm.models import Customer, Opportunity


@login_required
def social_dashboard(request):
    """
    لوحة تحكم السوشيال ميديا
    """
    # إحصائيات عامة
    total_conversations = SocialConversation.objects.count()
    active_conversations = SocialConversation.objects.filter(status='active').count()
    converted_customers = SocialConversation.objects.filter(status='converted').count()
    
    # إحصائيات حسب المنصة
    platform_stats = SocialConversation.objects.values('platform').annotate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        converted=Count('id', filter=Q(status='converted'))
    )
    
    # محادثات اليوم
    today = timezone.now().date()
    today_conversations = SocialConversation.objects.filter(
        created_at__date=today
    ).count()
    
    # أحدث المحادثات
    recent_conversations = SocialConversation.objects.select_related(
        'customer', 'opportunity'
    ).order_by('-last_message_at')[:10]
    
    context = {
        'total_conversations': total_conversations,
        'active_conversations': active_conversations,
        'converted_customers': converted_customers,
        'today_conversations': today_conversations,
        'platform_stats': platform_stats,
        'recent_conversations': recent_conversations,
        'page_title': 'لوحة تحكم السوشيال ميديا',
    }
    
    return render(request, 'whatsapp_ai/dashboard.html', context)


@login_required
def conversations_list(request):
    """
    قائمة المحادثات
    """
    # الفلترة
    platform = request.GET.get('platform', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    conversations = SocialConversation.objects.select_related('customer', 'opportunity')
    
    if platform:
        conversations = conversations.filter(platform=platform)
    
    if status_filter:
        conversations = conversations.filter(status=status_filter)
    
    if search:
        conversations = conversations.filter(
            Q(customer_name__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(platform_user_id__icontains=search)
        )
    
    conversations = conversations.order_by('-last_message_at')
    
    context = {
        'conversations': conversations,
        'platform_filter': platform,
        'status_filter': status_filter,
        'search_query': search,
        'page_title': 'المحادثات',
    }
    
    return render(request, 'whatsapp_ai/conversations_list.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """
    تفاصيل محادثة واحدة
    """
    conversation = get_object_or_404(
        SocialConversation.objects.select_related('customer', 'opportunity'),
        id=conversation_id
    )
    
    messages = conversation.messages.order_by('created_at')
    
    # إحصائيات
    total_messages = messages.count()
    inbound_messages = messages.filter(direction='inbound').count()
    outbound_messages = messages.filter(direction='outbound').count()
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'total_messages': total_messages,
        'inbound_messages': inbound_messages,
        'outbound_messages': outbound_messages,
        'page_title': f'محادثة {conversation.customer_name or conversation.platform_user_id}',
    }
    
    return render(request, 'whatsapp_ai/conversation_detail.html', context)


@login_required
def customers_list(request):
    """
    قائمة العملاء من السوشيال ميديا
    """
    search = request.GET.get('search', '')
    source = request.GET.get('source', '')
    
    # Get customers who have social conversations
    customers = Customer.objects.filter(
        social_conversations__isnull=False
    ).prefetch_related('social_conversations').distinct()
    
    if search:
        customers = customers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(mobile__icontains=search)
        )
    
    if source:
        customers = customers.filter(source__name__icontains=source)
    
    customers = customers.order_by('-created_at')
    
    context = {
        'customers': customers,
        'search_query': search,
        'source_filter': source,
        'page_title': 'عملاء السوشيال ميديا',
    }
    
    return render(request, 'whatsapp_ai/customers_list.html', context)


@login_required
def customer_detail(request, customer_id):
    """
    تفاصيل عميل
    """
    customer = get_object_or_404(Customer, id=customer_id)
    
    # المحادثات
    conversations = customer.social_conversations.all().order_by('-last_message_at')
    
    # فرص البيع
    opportunities = customer.opportunities.all().order_by('-created_at')
    
    context = {
        'customer': customer,
        'conversations': conversations,
        'opportunities': opportunities,
        'page_title': f'العميل: {customer.first_name} {customer.last_name}',
    }
    
    return render(request, 'whatsapp_ai/customer_detail.html', context)


@login_required
def opportunities_list(request):
    """
    قائمة فرص البيع من السوشيال ميديا
    """
    search = request.GET.get('search', '')
    stage = request.GET.get('stage', '')
    
    # Get opportunities that have social conversations
    opportunities = Opportunity.objects.filter(
        social_conversations__isnull=False
    ).select_related('customer', 'stage').distinct()
    
    if search:
        opportunities = opportunities.filter(
            Q(name__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search)
        )
    
    if stage:
        opportunities = opportunities.filter(stage__name__icontains=stage)
    
    opportunities = opportunities.order_by('-created_at')
    
    context = {
        'opportunities': opportunities,
        'search_query': search,
        'stage_filter': stage,
        'page_title': 'فرص البيع',
    }
    
    return render(request, 'whatsapp_ai/opportunities_list.html', context)


@login_required
def opportunity_detail(request, opportunity_id):
    """
    تفاصيل فرصة بيع
    """
    opportunity = get_object_or_404(
        Opportunity.objects.select_related('customer', 'stage'),
        id=opportunity_id
    )
    
    # المحادثات المرتبطة
    conversations = SocialConversation.objects.filter(opportunity=opportunity)
    
    context = {
        'opportunity': opportunity,
        'conversations': conversations,
        'page_title': f'فرصة: {opportunity.name}',
    }
    
    return render(request, 'whatsapp_ai/opportunity_detail.html', context)


@login_required
def platform_settings(request):
    """
    إعدادات المنصات
    """
    platforms = SocialPlatformConfig.objects.all().order_by('platform')
    
    if request.method == 'POST':
        # تحديث الإعدادات
        platform_id = request.POST.get('platform_id')
        if platform_id:
            platform_config = get_object_or_404(SocialPlatformConfig, id=platform_id)
            
            platform_config.is_active = request.POST.get('is_active') == 'on'
            platform_config.auto_create_customer = request.POST.get('auto_create_customer') == 'on'
            platform_config.auto_create_opportunity = request.POST.get('auto_create_opportunity') == 'on'
            platform_config.save()
            
            return JsonResponse({'success': True, 'message': 'تم التحديث بنجاح'})
    
    context = {
        'platforms': platforms,
        'page_title': 'إعدادات المنصات',
    }
    
    return render(request, 'whatsapp_ai/platform_settings.html', context)


@login_required
def products_knowledge(request):
    """
    قاعدة معرفة المنتجات
    """
    from django.core.paginator import Paginator
    
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    page_number = request.GET.get('page', 1)
    
    products = ProductKnowledgeBase.objects.filter(is_active=True)
    
    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(description__icontains=search) |
            Q(product_code__icontains=search)
        )
    
    if category:
        products = products.filter(category=category)
    
    products = products.order_by('-popularity_score', 'product_name')
    
    # Pagination - 50 منتج في الصفحة
    paginator = Paginator(products, 50)
    page_obj = paginator.get_page(page_number)
    
    # جميع الفئات
    categories = ProductKnowledgeBase.objects.filter(
        is_active=True
    ).exclude(category='').values_list('category', flat=True).distinct()
    
    # إجمالي المنتجات
    total_products = ProductKnowledgeBase.objects.filter(is_active=True).count()
    
    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search,
        'category_filter': category,
        'total_products': total_products,
        'page_title': 'قاعدة معرفة المنتجات',
    }
    
    return render(request, 'whatsapp_ai/products_knowledge.html', context)


@login_required
def convert_to_customer(request, conversation_id):
    """
    تحويل محادثة إلى عميل (AJAX)
    """
    import uuid
    from crm.models import CustomerSource, OpportunityStage
    from decimal import Decimal
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    conversation = get_object_or_404(SocialConversation, id=conversation_id)
    
    if conversation.customer:
        return JsonResponse({
            'success': False,
            'message': 'المحادثة مرتبطة بعميل بالفعل'
        })
    
    # Get or create customer source
    platform_name = conversation.get_platform_display()
    source, _ = CustomerSource.objects.get_or_create(
        name=platform_name,
        defaults={'description': f'عميل من {platform_name}', 'is_active': True}
    )
    
    # Generate unique customer code
    customer_code = f"SM-{uuid.uuid4().hex[:8].upper()}"
    
    # إنشاء عميل
    customer = Customer.objects.create(
        customer_code=customer_code,
        first_name=conversation.customer_name or f"عميل {platform_name}",
        last_name="",
        phone=conversation.phone_number or conversation.platform_user_id,
        source=source,
        notes=f"محادثة {platform_name} - {conversation.messages_count} رسالة"
    )
    
    conversation.customer = customer
    conversation.status = 'converted'
    conversation.save()
    
    # إنشاء فرصة بيع (اختياري)
    opportunity = None
    if conversation.interested_products:
        # Get or create a default stage
        stage, _ = OpportunityStage.objects.get_or_create(
            name='مبدئي',
            defaults={'order': 1, 'probability': Decimal('10.00'), 'is_won': False, 'is_lost': False}
        )
        
        opportunity = Opportunity.objects.create(
            customer=customer,
            name=f"فرصة من {platform_name} - {customer.first_name}",
            description=f"منتجات مهتم بها: {', '.join(conversation.interested_products)}",
            stage=stage,
            probability=Decimal(str(min(conversation.conversion_probability * 100, 100))),
            estimated_value=Decimal('0'),
            expected_close_date=timezone.now().date() + timedelta(days=30),
            assigned_to=request.user
        )
        conversation.opportunity = opportunity
        conversation.save()
    
    return JsonResponse({
        'success': True,
        'message': 'تم التحويل بنجاح',
        'customer_id': customer.id,
        'opportunity_id': opportunity.id if opportunity else None
    })


@login_required
def analytics(request):
    """
    تحليلات وإحصائيات
    """
    # آخر 7 أيام
    last_7_days = timezone.now() - timedelta(days=7)
    
    # محادثات حسب اليوم
    daily_conversations = []
    for i in range(7):
        date = (timezone.now() - timedelta(days=6-i)).date()
        count = SocialConversation.objects.filter(
            created_at__date=date
        ).count()
        daily_conversations.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # أفضل المنتجات المطلوبة
    top_products = ProductKnowledgeBase.objects.filter(
        is_active=True
    ).order_by('-times_mentioned')[:10]
    
    # معدل التحويل
    total_convs = SocialConversation.objects.count()
    converted_convs = SocialConversation.objects.filter(status='converted').count()
    conversion_rate = (converted_convs / total_convs * 100) if total_convs > 0 else 0
    
    context = {
        'daily_conversations': daily_conversations,
        'top_products': top_products,
        'conversion_rate': round(conversion_rate, 2),
        'page_title': 'التحليلات والإحصائيات',
    }
    
    return render(request, 'whatsapp_ai/analytics.html', context)


# ============================================
#   إدارة المنتجات - عرض/تعديل/حذف
# ============================================

@login_required
def product_detail(request, product_id):
    """عرض تفاصيل منتج"""
    product = get_object_or_404(ProductKnowledgeBase, id=product_id)
    
    context = {
        'product': product,
        'page_title': f'تفاصيل: {product.product_name}',
    }
    return render(request, 'whatsapp_ai/product_detail.html', context)


@login_required
def product_edit(request, product_id):
    """تعديل منتج"""
    product = get_object_or_404(ProductKnowledgeBase, id=product_id)
    
    if request.method == 'POST':
        product.product_name = request.POST.get('product_name', product.product_name)
        product.product_code = request.POST.get('product_code', product.product_code)
        product.description = request.POST.get('description', product.description)
        product.category = request.POST.get('category', product.category)
        
        price = request.POST.get('price')
        if price:
            try:
                product.price = float(price)
            except ValueError:
                pass
        
        product.in_stock = request.POST.get('in_stock') == 'on'
        product.is_active = request.POST.get('is_active') == 'on'
        
        # Keywords as comma separated
        keywords_str = request.POST.get('keywords', '')
        if keywords_str:
            product.keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
        
        product.save()
        messages.success(request, f'تم تحديث المنتج "{product.product_name}" بنجاح')
        return redirect('whatsapp_ai_web:products_knowledge')
    
    context = {
        'product': product,
        'page_title': f'تعديل: {product.product_name}',
    }
    return render(request, 'whatsapp_ai/product_edit.html', context)


@login_required
def product_delete(request, product_id):
    """حذف منتج"""
    product = get_object_or_404(ProductKnowledgeBase, id=product_id)
    
    if request.method == 'POST':
        product_name = product.product_name
        product.delete()
        messages.success(request, f'تم حذف المنتج "{product_name}" بنجاح')
        return redirect('whatsapp_ai_web:products_knowledge')
    
    context = {
        'product': product,
        'page_title': f'حذف: {product.product_name}',
    }
    return render(request, 'whatsapp_ai/product_delete.html', context)


@login_required
def product_toggle(request, product_id):
    """تفعيل/إلغاء تفعيل منتج (AJAX)"""
    if request.method == 'POST':
        product = get_object_or_404(ProductKnowledgeBase, id=product_id)
        product.is_active = not product.is_active
        product.save()
        return JsonResponse({
            'success': True,
            'is_active': product.is_active,
            'message': 'تم التفعيل' if product.is_active else 'تم الإلغاء'
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ============================================
#   إدارة الفئات
# ============================================

@login_required
def categories_manage(request):
    """إدارة الفئات"""
    # جميع الفئات مع عدد المنتجات
    categories = ProductKnowledgeBase.objects.filter(
        is_active=True
    ).exclude(category='').values('category').annotate(
        products_count=Count('id')
    ).order_by('category')
    
    # الفئات المستبعدة
    excluded_categories = ExcludedCategory.objects.all()
    excluded_names = list(excluded_categories.values_list('category_name', flat=True))
    
    # إجمالي المنتجات
    total_products = ProductKnowledgeBase.objects.filter(is_active=True).count()
    
    context = {
        'categories': categories,
        'excluded_categories': excluded_categories,
        'excluded_names': excluded_names,
        'total_products': total_products,
        'page_title': 'إدارة الفئات',
    }
    return render(request, 'whatsapp_ai/categories_manage.html', context)


@login_required
def category_exclude(request):
    """استبعاد فئة من قاعدة المعرفة"""
    if request.method == 'POST':
        category_name = request.POST.get('category_name', '').strip()
        reason = request.POST.get('reason', '')
        delete_products = request.POST.get('delete_products') == 'on'
        
        if category_name:
            # إضافة للفئات المستبعدة
            ExcludedCategory.objects.get_or_create(
                category_name=category_name,
                defaults={'reason': reason, 'excluded_by': request.user}
            )
            
            # حذف أو إلغاء تفعيل المنتجات
            products = ProductKnowledgeBase.objects.filter(category=category_name)
            if delete_products:
                count = products.count()
                products.delete()
                messages.success(request, f'تم استبعاد الفئة "{category_name}" وحذف {count} منتج')
            else:
                count = products.update(is_active=False)
                messages.success(request, f'تم استبعاد الفئة "{category_name}" وإلغاء تفعيل {count} منتج')
        
        return redirect('whatsapp_ai_web:categories_manage')
    
    return redirect('whatsapp_ai_web:categories_manage')


@login_required
def category_include(request, excluded_id):
    """إعادة تضمين فئة مستبعدة"""
    excluded = get_object_or_404(ExcludedCategory, id=excluded_id)
    category_name = excluded.category_name
    
    # إعادة تفعيل المنتجات
    count = ProductKnowledgeBase.objects.filter(category=category_name).update(is_active=True)
    
    # حذف من المستبعدة
    excluded.delete()
    
    messages.success(request, f'تم إعادة تضمين الفئة "{category_name}" وتفعيل {count} منتج')
    return redirect('whatsapp_ai_web:categories_manage')


@login_required
def category_delete_all(request, category_name):
    """حذف جميع منتجات فئة معينة"""
    category_name = unquote(category_name)
    
    if request.method == 'POST':
        products = ProductKnowledgeBase.objects.filter(category=category_name)
        count = products.count()
        products.delete()
        messages.success(request, f'تم حذف {count} منتج من فئة "{category_name}"')
        return redirect('whatsapp_ai_web:categories_manage')
    
    # عرض صفحة تأكيد
    products_count = ProductKnowledgeBase.objects.filter(category=category_name).count()
    context = {
        'category_name': category_name,
        'products_count': products_count,
        'page_title': f'حذف فئة: {category_name}',
    }
    return render(request, 'whatsapp_ai/category_delete_confirm.html', context)

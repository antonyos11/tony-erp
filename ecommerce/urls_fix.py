"""
URLs للمتجر الإلكتروني - واجهة عامة للزوار ولوحة تحكم الإدارة
"""
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from . import views
from . import views_admin
from . import views_auth
from . import views_warranty
from . import views_payment
from . import webhooks

app_name = 'ecommerce'

# API URLs (added for mobile app support)
from . import api_urls

# Sitemaps للـ SEO
sitemaps = {
    'products': views.ProductSitemap,
    'categories': views.CategorySitemap,
    'pages': views.StaticPagesSitemap,
}

urlpatterns = [
    # ==========================================
    # REST API for Mobile App (NEW - January 2026)
    # ==========================================
    path('api/', include('ecommerce.api_urls')),
    
    # الصفحة الرئيسية للمتجر
    path('', views.store_home, name='store_home'),
    
    # المنتجات
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # الفئات
    path('categories/', views.categories_list, name='categories_list'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    
    # العلامات التجارية
    path('brands/', views.brands_list, name='brands_list'),
    
    # البحث
    path('search/', views.search_products, name='search_products'),
    path('quick-order/', views.quick_order, name='quick_order'), # Fix 404
    
    # سلة التسوق
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/count/', views.cart_count_api, name='cart_count'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('cart/remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # الطلبات
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('my-orders/', views.my_orders, name='my_orders'),
    
    # قائمة الأمنيات
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    
    # التقييمات
    path('review/<int:product_id>/', views.add_review, name='add_review'),
    path('review/submit/<int:product_id>/', views.submit_review, name='submit_review'),
    
    # العروض السريعة
    path('flash-sales/', views.flash_sales_list, name='flash_sales'),
    
    # النشرة البريدية
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    
    # مقارنة المنتجات
    path('compare/', views.compare_products, name='compare_products'),
    path('compare/add/', views.add_to_compare, name='add_to_compare'),
    path('compare/remove/', views.remove_from_compare, name='remove_from_compare'),
    path('compare/clear/', views.clear_compare, name='clear_compare'),
    
    # الصفحات الثابتة
    path('about/', views.store_about, name='store_about'),
    path('contact/', views.store_contact, name='store_contact'),
    path('faq/', views.store_faq, name='store_faq'),
    path('privacy/', views.store_privacy, name='store_privacy'),
    path('terms/', views.store_terms, name='store_terms'),
    path('shipping/', views.store_shipping, name='store_shipping'),
    path('page/<str:page_type>/', views.store_page, name='store_page'),
    
    # ==========================================
    # الميزات الجديدة - January 2026
    # ==========================================
    

    # نظام بناء المراتب المخصصة (داخل المتجر)
    path('mattress-builder/', include(('mattress_builder.urls', 'mattress_builder'), namespace='mattress_builder')),
    
    # تتبع الشحنات للعملاء
    path('track-shipment/', views.track_shipment, name='track_shipment'),
    path('track-shipment/<str:tracking_number>/', views.shipment_details, name='shipment_details'),
    
    # المراجعات والتقييمات
    path('reviews/', views.all_reviews, name='all_reviews'),
    path('reviews/my-reviews/', views.my_reviews, name='my_reviews'),
    
    # ==========================================
    # Payment Processing (Egypt - Added January 2026)
    # ==========================================
    path('payment/initiate/<int:order_id>/', views_payment.initiate_payment, name='initiate_payment'),
    path('payment/paymob/response/', views_payment.paymob_response, name='paymob_response'),
    path('payment/success/<int:order_id>/', views_payment.payment_success, name='payment_success'),
    path('payment/failed/<int:order_id>/', views_payment.payment_failed, name='payment_failed'),
    path('payment/check-status/<int:order_id>/', views_payment.check_payment_status, name='check_payment_status'),
    
    # Payment Webhooks
    path('webhooks/paymob/', webhooks.paymob_webhook, name='paymob_webhook'),
    
    # ==========================================
    # تسجيل الدخول والتسجيل للعملاء
    # ==========================================
    
    # تسجيل الدخول والتسجيل
    path('login/', views_auth.customer_login, name='customer_login'),
    path('register/', views_auth.customer_register, name='customer_register'),
    path('logout/', views_auth.customer_logout, name='customer_logout'),
    
    # استعادة كلمة المرور
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views_auth.reset_password, name='reset_password'),
    
    # تأكيد البريد الإلكتروني
    path('verify-email/<str:token>/', views_auth.verify_email, name='verify_email'),
    path('resend-verification/', views_auth.resend_verification, name='resend_verification'),
    
    # تسجيل الدخول الاجتماعي
    path('auth/<str:provider>/', views_auth.social_login_init, name='social_login'),
    path('auth/<str:provider>/callback/', views_auth.social_callback, name='social_callback'),
    path('link/<str:provider>/', views_auth.link_social_account, name='link_social'),
    path('unlink/<str:provider>/', views_auth.unlink_social_account, name='unlink_social'),
    
    # حساب العميل
    path('account/', views_auth.customer_account, name='customer_account'),
    path('account/update/', views_auth.update_profile, name='update_profile'),
    path('account/change-password/', views_auth.change_password, name='change_password'),
    path('account/set-password/', views_auth.set_password, name='set_password'),
    path('account/addresses/', views_auth.manage_addresses, name='manage_addresses'),
    path('account/orders/', views_auth.customer_orders, name='customer_orders'),
    path('account/wishlist/', views_auth.customer_wishlist, name='customer_wishlist'),
    
    # SEO
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    
    # ==========================================
    # لوحة تحكم المتجر الإلكتروني - للإدارة فقط
    # ==========================================
    
    # لوحة التحكم الرئيسية
    path('admin/', views_admin.store_dashboard, name='admin_dashboard'),
    path('admin/dashboard/', views_admin.store_dashboard, name='store_dashboard'),
    
    # قائمة الإعدادات الشاملة
    path('admin/settings-menu/', views_admin.settings_menu, name='admin_settings_menu'),
    
    # إعدادات الهيدر
    path('admin/header-settings/', views_admin.header_settings, name='admin_header_settings'),
    
    # إعدادات الفوتر
    path('admin/footer-settings/', views_admin.footer_settings, name='admin_footer_settings'),
    
    # روابط الهيدر
    path('admin/header-links/', views_admin.header_links_list, name='admin_header_links'),
    
    # النشرة البريدية
    path('admin/newsletter/', views_admin.newsletter_list, name='admin_newsletter'),
    path('admin/newsletter/campaign/add/', views_admin.newsletter_campaign_add, name='admin_newsletter_campaign_add'),
    
    # العروض السريعة
    path('admin/flash-sales/', views_admin.flash_sales_list, name='admin_flash_sales'),
    path('admin/flash-sales/add/', views_admin.flash_sale_add, name='admin_flash_sale_add'),
    
    # أقسام الصفحة الرئيسية
    path('admin/homepage-sections/', views_admin.homepage_sections_list, name='admin_homepage_sections'),
    path('admin/homepage-sections/add/', views_admin.homepage_section_add, name='admin_homepage_section_add'),
    
    # فئة أقسام الصفحة الرئيسية
    path('admin/homepage-category/', views_admin.homepage_category, name='admin_homepage_category'),
    
    # فئات الشريط الجانبي
    path('admin/sidebar-categories/', views_admin.sidebar_categories_list, name='admin_sidebar_categories'),
    
    # تكاليف الشحن
    path('admin/shipping-costs/', views_admin.shipping_costs, name='admin_shipping_costs'),
    
    # إعدادات المتجر
    path('admin/settings/', views_admin.store_settings, name='admin_settings'),
    
    # إدارة بوابات الدفع
    path('admin/payment-gateways/', views_admin.payment_gateways_list, name='admin_payment_gateways'),
    path('admin/payment-gateways/add/', views_admin.payment_gateway_add, name='admin_payment_gateway_add'),
    path('admin/payment-gateways/<int:pk>/edit/', views_admin.payment_gateway_edit, name='admin_payment_gateway_edit'),
    path('admin/payment-gateways/<int:pk>/toggle/', views_admin.payment_gateway_toggle, name='admin_payment_gateway_toggle'),
    path('admin/payment-gateways/<int:pk>/delete/', views_admin.payment_gateway_delete, name='admin_payment_gateway_delete'),
    
    # إدارة شركات الشحن
    path('admin/shipping-companies/', views_admin.shipping_companies_list, name='admin_shipping_companies'),
    path('admin/shipping-companies/add/', views_admin.shipping_company_add, name='admin_shipping_company_add'),
    path('admin/shipping-companies/<int:pk>/edit/', views_admin.shipping_company_edit, name='admin_shipping_company_edit'),
    path('admin/shipping-companies/<int:pk>/toggle/', views_admin.shipping_company_toggle, name='admin_shipping_company_toggle'),
    path('admin/shipping-companies/<int:pk>/delete/', views_admin.shipping_company_delete, name='admin_shipping_company_delete'),
    
    # إدارة التواصل الاجتماعي
    path('admin/social-media/', views_admin.social_media_list, name='admin_social_media'),
    path('admin/social-media/add/', views_admin.social_media_add, name='admin_social_media_add'),
    path('admin/social-media/<int:pk>/edit/', views_admin.social_media_edit, name='admin_social_media_edit'),
    path('admin/social-media/<int:pk>/toggle/', views_admin.social_media_toggle, name='admin_social_media_toggle'),
    path('admin/social-media/<int:pk>/delete/', views_admin.social_media_delete, name='admin_social_media_delete'),
    
    # إدارة محتوى الصفحات
    path('admin/page-content/', views_admin.page_content_list, name='admin_page_content'),
    path('admin/page-content/<int:pk>/edit/', views_admin.page_content_edit, name='admin_page_content_edit'),
    
    # إدارة البانرات
    path('admin/banners/', views_admin.banners_list, name='admin_banners'),
    path('admin/banners/add/', views_admin.banner_add, name='admin_banner_add'),
    path('admin/banners/<int:pk>/edit/', views_admin.banner_edit, name='admin_banner_edit'),
    path('admin/banners/<int:pk>/toggle/', views_admin.banner_toggle, name='admin_banner_toggle'),
    path('admin/banners/<int:pk>/delete/', views_admin.banner_delete, name='admin_banner_delete'),
    
    # إدارة الكوبونات
    path('admin/coupons/', views_admin.coupons_list, name='admin_coupons'),
    path('admin/coupons/add/', views_admin.coupon_add, name='admin_coupon_add'),
    path('admin/coupons/<int:pk>/edit/', views_admin.coupon_edit, name='admin_coupon_edit'),
    path('admin/coupons/<int:pk>/toggle/', views_admin.coupon_toggle, name='admin_coupon_toggle'),
    path('admin/coupons/<int:pk>/delete/', views_admin.coupon_delete, name='admin_coupon_delete'),
    
    # إدارة الطلبات
    path('admin/orders/', views_admin.orders_list, name='admin_orders'),
    path('admin/orders/<int:pk>/', views_admin.order_detail, name='admin_order_detail'),
    path('admin/orders/<int:pk>/update-status/', views_admin.order_update_status, name='admin_order_update_status'),
    
    # إدارة التقييمات
    path('admin/reviews/', views_admin.reviews_list, name='admin_reviews'),
    path('admin/reviews/<int:pk>/approve/', views_admin.review_approve, name='admin_review_approve'),
    path('admin/reviews/<int:pk>/delete/', views_admin.review_delete, name='admin_review_delete'),
    
    # إدارة المنتجات
    path('admin/products/', views_admin.products_list, name='admin_products'),
    path('admin/products/add/', views_admin.product_add, name='admin_product_add'),
    path('admin/products/<int:pk>/edit/', views_admin.product_edit, name='admin_product_edit'),
    path('admin/products/<int:pk>/delete/', views_admin.product_delete, name='admin_product_delete'),
    
    # إدارة التصنيفات
    path('admin/categories/', views_admin.categories_list, name='admin_categories'),
    path('admin/categories/add/', views_admin.category_add, name='admin_category_add'),
    path('admin/categories/<int:pk>/edit/', views_admin.category_edit, name='admin_category_edit'),
    path('admin/categories/<int:pk>/delete/', views_admin.category_delete, name='admin_category_delete'),
    
    # إدارة العلامات التجارية
    path('admin/brands/', views_admin.brands_list, name='admin_brands'),
    path('admin/brands/add/', views_admin.brand_add, name='admin_brand_add'),
    path('admin/brands/<int:pk>/edit/', views_admin.brand_edit, name='admin_brand_edit'),
    path('admin/brands/<int:pk>/delete/', views_admin.brand_delete, name='admin_brand_delete'),
    
    # إدارة العملاء
    path('admin/customers/', views_admin.customers_list, name='admin_customers'),
    path('admin/customers/<int:pk>/', views_admin.customer_detail, name='admin_customer_detail'),
    
    # إدارة مزودي تسجيل الدخول الاجتماعي
    path('admin/social-auth/', views_admin.social_auth_providers_list, name='admin_social_auth'),
    path('admin/social-auth/add/', views_admin.social_auth_provider_add, name='admin_social_auth_add'),
    path('admin/social-auth/<int:pk>/edit/', views_admin.social_auth_provider_edit, name='admin_social_auth_edit'),
    path('admin/social-auth/<int:pk>/toggle/', views_admin.social_auth_provider_toggle, name='admin_social_auth_toggle'),
    path('admin/social-auth/<int:pk>/delete/', views_admin.social_auth_provider_delete, name='admin_social_auth_delete'),
    
    # ==========================================
    # نظام الضمان - صفحات العملاء
    # ==========================================
    
    # الصفحة الرئيسية للضمان
    path('warranty/', views_warranty.warranty_landing, name='warranty_landing'),
    
    # التحقق من الضمان
    path('warranty/check/', views_warranty.warranty_check, name='warranty_check'),
    
    # تسجيل الضمان
    path('warranty/register/', views_warranty.warranty_register, name='warranty_register'),
    path('warranty/register/success/<int:pk>/', views_warranty.warranty_registration_success, name='warranty_registration_success'),
    
    # مطالبة الضمان
    path('warranty/claim/<str:warranty_code>/', views_warranty.warranty_claim_submit, name='warranty_claim_submit'),
    path('warranty/claim/success/<int:pk>/', views_warranty.warranty_claim_success, name='warranty_claim_success'),
    
    # API
    path('api/warranty/verify/', views_warranty.warranty_verify_api, name='warranty_verify_api'),
    
    # ==========================================
    # نظام الضمان - لوحة التحكم
    # ==========================================
    
    # لوحة تحكم الضمان
    path('admin/warranty/', views_warranty.warranty_admin_dashboard, name='warranty_admin_dashboard'),
    
    # سياسات الضمان
    path('admin/warranty/policies/', views_warranty.warranty_policy_list, name='warranty_policy_list'),
    path('admin/warranty/policies/add/', views_warranty.warranty_policy_create, name='warranty_policy_create'),
    path('admin/warranty/policies/<int:pk>/edit/', views_warranty.warranty_policy_edit, name='warranty_policy_edit'),
    path('admin/warranty/policies/<int:pk>/delete/', views_warranty.warranty_policy_delete, name='warranty_policy_delete'),
    
    # بطاقات الضمان
    path('admin/warranty/cards/', views_warranty.warranty_card_list, name='warranty_card_list'),
    path('admin/warranty/cards/add/', views_warranty.warranty_card_create, name='warranty_card_create'),
    path('admin/warranty/cards/<int:pk>/', views_warranty.warranty_card_detail, name='warranty_card_detail'),
    path('admin/warranty/cards/<int:pk>/print/', views_warranty.warranty_card_print, name='warranty_card_print'),
    
    # طلبات تفعيل الضمان
    path('admin/warranty/registrations/', views_warranty.warranty_registration_list, name='warranty_registration_list'),
    path('admin/warranty/registrations/<int:pk>/review/', views_warranty.warranty_registration_review, name='warranty_registration_review'),
    
    # مطالبات الضمان
    path('admin/warranty/claims/', views_warranty.warranty_claim_list, name='warranty_claim_list'),
    path('admin/warranty/claims/<int:pk>/', views_warranty.warranty_claim_detail, name='warranty_claim_detail'),
]

# ==========================================
# بوابة الموظفين - الوصول للنظام من المتجر
# ==========================================
from . import views_employee_portal

urlpatterns += [
    # تسجيل دخول الموظفين
    path('employee-portal/', views_employee_portal.employee_portal_login, name='employee_portal_login'),
    path('employee-portal/logout/', views_employee_portal.employee_portal_logout, name='employee_portal_logout'),
    
    # صفحة الترحيب
    path('employee-portal/welcome/', views_employee_portal.employee_welcome, name='employee_welcome'),
    
    # تسجيل الحضور والانصراف
    path('employee-portal/attendance/', views_employee_portal.register_attendance, name='register_attendance'),
    path('employee-portal/attendance/status/', views_employee_portal.check_attendance_status, name='check_attendance_status'),
    
    # الوصول للنظام
    path('employee-portal/access-system/', views_employee_portal.access_system, name='access_system'),
    
    # التتبع والموقع (للسائقين والمندوبين)
    path('employee-portal/update-location/', views_employee_portal.update_location, name='update_location'),
    
    # لوحة تحكم المندوب
    path('employee-portal/sales-rep/', views_employee_portal.sales_rep_dashboard, name='sales_rep_dashboard'),
    path('employee-portal/sales-rep/submit-visit/', views_employee_portal.submit_visit_report, name='submit_visit_report'),
]

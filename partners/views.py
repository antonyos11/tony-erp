"""
عرض تطبيق الشركاء
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .models import Partner, Customer, Supplier, SupplierDocument, SupplierProduct, PartnerContact
from django.http import JsonResponse, FileResponse, Http404
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal, InvalidOperation


@login_required
def dashboard(request):
    """لوحة تحكم الشركاء"""
    context = {
        'title': 'لوحة تحكم الشركاء',
        'customers_count': Partner.objects.filter(partner_type='customer', is_active=True).count(),
        'suppliers_count': Partner.objects.filter(partner_type='supplier', is_active=True).count(),
        'total_partners': Partner.objects.filter(is_active=True).count(),
    }
    return render(request, 'partners/dashboard.html', context)


@login_required
def partners_list(request):
    """قائمة الشركاء"""
    partners = Partner.objects.filter(is_active=True)

    # فلترة
    partner_type = request.GET.get('type')
    if partner_type:
        partners = partners.filter(partner_type=partner_type)

    search = request.GET.get('search')
    if search:
        partners = partners.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    # ترقيم الصفحات
    paginator = Paginator(partners, 20)
    page_number = request.GET.get('page')
    partners_page = paginator.get_page(page_number)

    context = {
        'title': 'قائمة الشركاء',
        'partners': partners_page,
    'type_choices': Partner.PARTNER_TYPES,
        'current_type': partner_type,
        'search_query': search,
    }
    return render(request, 'partners/partners_list.html', context)


@login_required
def partner_create(request):
    """إنشاء شريك جديد عام (يُستخدم أيضاً لعملاء/موردين عند عدم وجود صفحة مخصصة)."""
    preset_type = request.GET.get('partner_type') or request.POST.get('partner_type')
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        ptype = request.POST.get('partner_type','customer')
        phone = request.POST.get('phone','').strip()
        email = request.POST.get('email','').strip()
        address = request.POST.get('address','').strip()
        # كشف تكرار مبسط (نفس الاسم أو الهاتف)
        duplicate_qs = Partner.objects.filter(is_active=True).filter(Q(name__iexact=name) | (Q(phone__iexact=phone) if phone else Q()))
        if duplicate_qs.exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'duplicate': True, 'message': 'اسم أو هاتف مكرر'}, status=409)
            messages.error(request,'هناك شريك بنفس الاسم أو الهاتف')
            return redirect(request.path)
        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'الاسم مطلوب'}, status=400)
            messages.error(request,'الاسم مطلوب')
        else:
            # أنشئ الشريك أولاً (لا توجد الحقول الإضافية على Partner نفسه)
            is_active = request.POST.get('is_active') == 'on'
            partner = Partner.objects.create(name=name, partner_type=ptype, phone=phone, email=email, address=address, is_active=is_active)
            # إذا كان مورد/كلاهما حدّث سجل Supplier الناتج من الإشارة
            if ptype in ('supplier','both'):
                supply_type = request.POST.get('supply_type','').strip()
                raw_material = request.POST.get('raw_material','').strip()
                commercial_register = request.POST.get('commercial_register','').strip()
                tax_number = request.POST.get('tax_number','').strip()

                supp = getattr(partner, 'supplier_profile', None)
                if not supp:
                    from .models import Supplier
                    supp = Supplier.objects.create(
                        partner=partner,
                        name=name,
                        email=email,
                        phone=phone,
                        address=address,
                        supply_type=supply_type if supply_type else None,
                        raw_material=raw_material if raw_material else None,
                        commercial_register=commercial_register if commercial_register else None,
                        tax_number=tax_number if tax_number else None
                    )
                else:
                    changed = False
                    if supply_type and not supp.supply_type:
                        supp.supply_type = supply_type
                        changed = True
                    if raw_material and not supp.raw_material:
                        supp.raw_material = raw_material
                        changed = True
                    if commercial_register and not supp.commercial_register:
                        supp.commercial_register = commercial_register
                        changed = True
                    if tax_number and not supp.tax_number:
                        supp.tax_number = tax_number
                        changed = True
                    if changed:
                        supp.save(update_fields=['supply_type','raw_material','commercial_register','tax_number'])

                # حفظ المستندات المرفوعة
                document_mapping = {
                    'commercial_register_file': ('commercial_register', 'السجل التجاري'),
                    'tax_certificate_file': ('vat_certificate', 'شهادة ضريبة القيمة المضافة'),
                    'business_license_file': ('authorization', 'رخصة العمل'),
                    'other_document_file': ('other', 'مستند آخر'),
                }

                for file_field, (doc_type, doc_title) in document_mapping.items():
                    uploaded_file = request.FILES.get(file_field)
                    if uploaded_file:
                        try:
                            SupplierDocument.objects.create(
                                supplier=supp,
                                document_type=doc_type,
                                title=doc_title,
                                file=uploaded_file,
                                uploaded_by=request.user
                            )
                        except Exception as e:
                            messages.warning(request, f'تعذر حفظ {doc_title}: {str(e)}')

            # حفظ أرقام التواصل وأسماء المسؤولين
            contact_names = request.POST.getlist('contact_name[]')
            contact_phones = request.POST.getlist('contact_phone[]')
            contact_notes_list = request.POST.getlist('contact_notes[]')
            contact_primaries = request.POST.getlist('contact_primary[]')
            contact_ids = request.POST.getlist('contact_id[]')

            for i in range(len(contact_phones)):
                c_phone = contact_phones[i].strip() if i < len(contact_phones) else ''
                if not c_phone:
                    continue
                c_name = contact_names[i].strip() if i < len(contact_names) else ''
                c_notes = contact_notes_list[i].strip() if i < len(contact_notes_list) else ''
                c_primary = str(i) in contact_primaries
                PartnerContact.objects.create(
                    partner=partner,
                    contact_name=c_name,
                    phone=c_phone,
                    notes=c_notes,
                    is_primary=c_primary,
                )

            # ضمان إنشاء سجل Customer فعلي ليستعمل في الفواتير
            if ptype in ('customer', 'both'):
                Customer.objects.get_or_create(name=name, defaults={'email': email, 'phone': phone, 'address': address})
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': partner.id, 'name': partner.name, 'partner_type': partner.partner_type})

            # رسالة نجاح مع توجيه للموردين
            if ptype in ('supplier', 'both'):
                messages.success(request, 'تم إنشاء المورد بنجاح! يمكنك الآن إضافة المنتجات والمواد الخام مع أسعارها')
                # توجيه المورد لصفحة التعديل لإضافة المنتجات
                return redirect('partners:partner_edit', pk=partner.pk)
            else:
                messages.success(request, 'تم إنشاء الشريك بنجاح')

            # تحديد صفحة الرجوع
            if next_url:
                return redirect(next_url)
            if ptype == 'customer':
                return redirect('partners:customers_list')
            return redirect('partners:partners_list')

    context = {
        'title': 'إضافة شريك جديد',
        'partner_type': preset_type,
        'next': next_url,
    }
    return render(request, 'partners/partner_form.html', context)


@login_required
def partner_detail(request, pk):
    """تفاصيل الشريك"""
    partner = get_object_or_404(Partner, pk=pk)
    partner_contacts = partner.contacts.all()

    context = {
        'title': f'تفاصيل {partner.name}',
        'partner': partner,
        'partner_contacts': partner_contacts,
    }
    return render(request, 'partners/partner_detail.html', context)


@login_required
def partner_edit(request, pk):
    """تعديل شريك"""
    partner = get_object_or_404(Partner, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        phone = request.POST.get('phone','').strip()
        email = request.POST.get('email','').strip()
        address = request.POST.get('address','').strip()
        is_active = request.POST.get('is_active') == 'on'
        changed_fields = []
        if name and name != partner.name:
            partner.name = name; changed_fields.append('name')
        if phone != partner.phone:
            partner.phone = phone; changed_fields.append('phone')
        if email != partner.email:
            partner.email = email; changed_fields.append('email')
        if address != partner.address:
            partner.address = address; changed_fields.append('address')
        if is_active != partner.is_active:
            partner.is_active = is_active; changed_fields.append('is_active')
        if changed_fields:
            partner.save(update_fields=changed_fields)

        # تحديث بيانات المورد الإضافية إن وُجد
        if partner.partner_type in ('supplier','both'):
            supply_type = request.POST.get('supply_type','').strip()
            raw_material = request.POST.get('raw_material','').strip()
            commercial_register = request.POST.get('commercial_register','').strip()
            tax_number = request.POST.get('tax_number','').strip()
            supp = getattr(partner, 'supplier_profile', None)
            if supp:
                supp_changed = []
                if supply_type and supply_type != supp.supply_type:
                    supp.supply_type = supply_type; supp_changed.append('supply_type')
                if raw_material != supp.raw_material:
                    supp.raw_material = raw_material; supp_changed.append('raw_material')
                if commercial_register != supp.commercial_register:
                    supp.commercial_register = commercial_register; supp_changed.append('commercial_register')
                if tax_number != supp.tax_number:
                    supp.tax_number = tax_number; supp_changed.append('tax_number')
                if supp_changed:
                    supp.save(update_fields=supp_changed)
            # في حالة غياب السجل لأي سبب
            else:
                from .models import Supplier
                Supplier.objects.create(partner=partner, name=partner.name, email=partner.email, phone=partner.phone, address=partner.address, supply_type=supply_type, raw_material=raw_material, commercial_register=commercial_register, tax_number=tax_number)

        # تحديث أرقام التواصل وأسماء المسؤولين
        contact_names = request.POST.getlist('contact_name[]')
        contact_phones = request.POST.getlist('contact_phone[]')
        contact_notes_list = request.POST.getlist('contact_notes[]')
        contact_primaries = request.POST.getlist('contact_primary[]')
        contact_ids = request.POST.getlist('contact_id[]')

        # جمع IDs الموجودة في الطلب
        submitted_ids = set()
        for i in range(len(contact_phones)):
            c_phone = contact_phones[i].strip() if i < len(contact_phones) else ''
            if not c_phone:
                continue
            c_name = contact_names[i].strip() if i < len(contact_names) else ''
            c_notes = contact_notes_list[i].strip() if i < len(contact_notes_list) else ''
            c_primary = str(i) in contact_primaries
            c_id = contact_ids[i].strip() if i < len(contact_ids) else ''

            if c_id:
                # تحديث جهة اتصال موجودة
                try:
                    contact = PartnerContact.objects.get(id=c_id, partner=partner)
                    contact.contact_name = c_name
                    contact.phone = c_phone
                    contact.notes = c_notes
                    contact.is_primary = c_primary
                    contact.save()
                    submitted_ids.add(int(c_id))
                except PartnerContact.DoesNotExist:
                    new_contact = PartnerContact.objects.create(
                        partner=partner, contact_name=c_name, phone=c_phone,
                        notes=c_notes, is_primary=c_primary
                    )
                    submitted_ids.add(new_contact.id)
            else:
                # إنشاء جهة اتصال جديدة
                new_contact = PartnerContact.objects.create(
                    partner=partner, contact_name=c_name, phone=c_phone,
                    notes=c_notes, is_primary=c_primary
                )
                submitted_ids.add(new_contact.id)

        # حذف جهات الاتصال التي أزالها المستخدم
        partner.contacts.exclude(id__in=submitted_ids).delete()

        messages.success(request, 'تم تحديث بيانات الشريك')
        return redirect('partners:partner_detail', pk=partner.pk)

    # جلب منتجات المورد للعرض في الصفحة
    supplier_products = []
    available_products = []
    if partner.partner_type in ('supplier', 'both') and hasattr(partner, 'supplier_profile') and partner.supplier_profile:
        supplier = partner.supplier_profile
        supplier_products = SupplierProduct.objects.filter(supplier=supplier).select_related('product', 'product__category')
        # المنتجات غير المرتبطة بالمورد
        from inventory.models import Product
        existing_product_ids = supplier_products.values_list('product_id', flat=True)
        available_products = Product.objects.filter(is_active=True).exclude(id__in=existing_product_ids).order_by('name')

    # وحدات القياس المتاحة
    from inventory.models import Product as InvProduct
    uom_choices = InvProduct.UOM_CHOICES

    # جلب جهات الاتصال
    partner_contacts = partner.contacts.all()

    context = {
        'title': f'تعديل {partner.name}',
        'partner': partner,
        'partner_type': partner.partner_type,
        'partner_contacts': partner_contacts,
        'supplier_products': supplier_products,
        'available_products': available_products,
        'currencies': [('EGP', 'جنيه مصري'), ('USD', 'دولار أمريكي'), ('EUR', 'يورو')],
        'uom_choices': uom_choices,
    }
    return render(request, 'partners/partner_form.html', context)


@login_required
def partner_delete(request, pk):
    """حذف شريك"""
    partner = get_object_or_404(Partner, pk=pk)

    if request.method == 'POST':
        partner.is_active = False
        partner.save()
        messages.success(request, f'تم إلغاء تفعيل {partner.name}')
        return redirect('partners:partners_list')

    context = {
        'title': 'حذف شريك',
        'partner': partner,
    }
    return render(request, 'partners/partner_confirm_delete.html', context)


@login_required
def customers_list(request):
    """قائمة العملاء"""
    customers = Partner.objects.filter(partner_type='customer', is_active=True)

    search = request.GET.get('search')
    if search:
        customers = customers.filter(name__icontains=search)

    context = {
        'title': 'قائمة العملاء',
        'partners': customers,
        'partner_type': 'customer',
    }
    return render(request, 'partners/partners_list.html', context)


@login_required
def customer_create(request):
    """إنشاء عميل جديد (واجهة مختصرة)"""
    if request.method == 'POST':
        request.POST = request.POST.copy()
        request.POST['partner_type'] = 'customer'
        request.POST['next'] = request.POST.get('next') or request.GET.get('next') or 'partners:customers_list'
        return partner_create(request)
    context = {'title': 'إضافة عميل جديد','partner_type':'customer','next': request.GET.get('next') or 'partners:customers_list'}
    return render(request,'partners/partner_form.html',context)


@login_required
def suppliers_list(request):
    """قائمة الموردين"""
    # استخدام Supplier مباشرة للحصول على المستندات
    suppliers = Supplier.objects.select_related('partner').prefetch_related('documents').all()

    search = request.GET.get('search')
    if search:
        suppliers = suppliers.filter(name__icontains=search)

    # عرض النشطين فقط إلا لو طلب عرض الكل
    show_all = request.GET.get('show_all', '')
    if not show_all:
        suppliers = suppliers.filter(is_active=True)

    # إضافة معلومة المستندات المنتهية لكل مورد
    for supplier in suppliers:
        supplier.has_expired_docs = any(doc.is_expired for doc in supplier.documents.all())

    # إحصائيات
    total_suppliers = Supplier.objects.count()
    active_suppliers = Supplier.objects.filter(is_active=True).count()

    context = {
        'title': 'قائمة الموردين',
        'suppliers': suppliers,
        'partner_type': 'supplier',
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        'show_all': show_all,
    }
    return render(request, 'partners/suppliers_list.html', context)


@login_required
def supplier_create(request):
    """إنشاء مورد جديد (واجهة مختصرة)"""
    if request.method == 'POST':
        request.POST = request.POST.copy()
        request.POST['partner_type'] = 'supplier'
        request.POST['next'] = request.POST.get('next') or request.GET.get('next') or 'partners:suppliers_list'
        return partner_create(request)
    context = {'title':'إضافة مورد جديد','partner_type':'supplier','next': request.GET.get('next') or 'partners:suppliers_list'}
    return render(request,'partners/partner_form.html',context)


@login_required
def supplier_detail(request, pk):
    """عرض تفاصيل المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)

    # جلب منتجات المورد
    products = SupplierProduct.objects.filter(supplier=supplier).select_related('product').order_by('-is_preferred', 'product__name')[:10]

    # جلب مستندات المورد
    documents = supplier.documents.all().order_by('-uploaded_at')[:5]

    # جلب جهات الاتصال المرتبطة بالشريك
    partner_contacts = supplier.partner.contacts.all() if supplier.partner else []

    context = {
        'title': f'تفاصيل المورد: {supplier.name}',
        'supplier': supplier,
        'partner': supplier.partner,  # للتوافق مع القوالب الموجودة
        'partner_type': 'supplier',
        'products': products,
        'documents': documents,
        'partner_contacts': partner_contacts,
    }
    return render(request, 'partners/supplier_detail.html', context)


@login_required
def supplier_edit(request, pk):
    """تعديل بيانات المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    partner = supplier.partner

    # إنشاء Partner إذا لم يكن موجوداً (لدعم جهات الاتصال)
    if not partner:
        partner = Partner.objects.create(
            name=supplier.name,
            email=supplier.email,
            phone=supplier.phone,
            address=supplier.address,
            partner_type='supplier',
            is_active=supplier.is_active,
        )
        supplier.partner = partner
        supplier.save(update_fields=['partner'])

    if request.method == 'POST':
        # تحديث بيانات المورد
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        supply_type = request.POST.get('supply_type', '').strip()
        commercial_register = request.POST.get('commercial_register', '').strip()
        tax_number = request.POST.get('tax_number', '').strip()

        raw_material = request.POST.get('raw_material', '').strip()

        # تحديث بيانات المورد
        changed = []
        if name and name != supplier.name:
            supplier.name = name
            changed.append('name')
        if phone != supplier.phone:
            supplier.phone = phone
            changed.append('phone')
        if email != supplier.email:
            supplier.email = email
            changed.append('email')
        if address != supplier.address:
            supplier.address = address
            changed.append('address')
        if supply_type != supplier.supply_type:
            supplier.supply_type = supply_type
            changed.append('supply_type')
        if raw_material != supplier.raw_material:
            supplier.raw_material = raw_material
            changed.append('raw_material')
        if commercial_register != supplier.commercial_register:
            supplier.commercial_register = commercial_register
            changed.append('commercial_register')
        if tax_number != supplier.tax_number:
            supplier.tax_number = tax_number
            changed.append('tax_number')

        # تحديث حالة المورد (نشط/غير نشط) - checkbox لا يُرسل قيمة عند unchecked
        is_active = request.POST.get('is_active') == 'on'
        if is_active != supplier.is_active:
            supplier.is_active = is_active
            changed.append('is_active')

        if changed:
            supplier.save(update_fields=changed)

        # تحديث Partner المرتبط إذا وجد
        if partner:
            partner_changed = []
            if name and name != partner.name:
                partner.name = name
                partner_changed.append('name')
            if phone != partner.phone:
                partner.phone = phone
                partner_changed.append('phone')
            if email != partner.email:
                partner.email = email
                partner_changed.append('email')
            if address != partner.address:
                partner.address = address
                partner_changed.append('address')
            if is_active != partner.is_active:
                partner.is_active = is_active
                partner_changed.append('is_active')
            if partner_changed:
                partner.save(update_fields=partner_changed)

        # تحديث أرقام التواصل وأسماء المسؤولين
        if partner:
            contact_names = request.POST.getlist('contact_name[]')
            contact_phones = request.POST.getlist('contact_phone[]')
            contact_notes_list = request.POST.getlist('contact_notes[]')
            contact_primaries = request.POST.getlist('contact_primary[]')
            contact_ids = request.POST.getlist('contact_id[]')

            submitted_ids = set()
            for i in range(len(contact_phones)):
                c_phone = contact_phones[i].strip() if i < len(contact_phones) else ''
                if not c_phone:
                    continue
                c_name = contact_names[i].strip() if i < len(contact_names) else ''
                c_notes = contact_notes_list[i].strip() if i < len(contact_notes_list) else ''
                c_primary = str(i) in contact_primaries
                c_id = contact_ids[i].strip() if i < len(contact_ids) else ''

                if c_id:
                    try:
                        contact = PartnerContact.objects.get(id=c_id, partner=partner)
                        contact.contact_name = c_name
                        contact.phone = c_phone
                        contact.notes = c_notes
                        contact.is_primary = c_primary
                        contact.save()
                        submitted_ids.add(int(c_id))
                    except PartnerContact.DoesNotExist:
                        new_contact = PartnerContact.objects.create(
                            partner=partner, contact_name=c_name, phone=c_phone,
                            notes=c_notes, is_primary=c_primary
                        )
                        submitted_ids.add(new_contact.id)
                else:
                    new_contact = PartnerContact.objects.create(
                        partner=partner, contact_name=c_name, phone=c_phone,
                        notes=c_notes, is_primary=c_primary
                    )
                    submitted_ids.add(new_contact.id)

            # حذف جهات الاتصال التي أزالها المستخدم
            partner.contacts.exclude(id__in=submitted_ids).delete()

        messages.success(request, 'تم تحديث بيانات المورد بنجاح')
        return redirect('partners:supplier_detail', pk=supplier.pk)

    # جلب منتجات المورد
    products = SupplierProduct.objects.filter(supplier=supplier).select_related('product').order_by('-is_preferred', 'product__name')

    # جلب جهات الاتصال
    partner_contacts = partner.contacts.all() if partner else []

    context = {
        'title': f'تعديل المورد: {supplier.name}',
        'supplier': supplier,
        'partner': partner,
        'partner_type': 'supplier',
        'products': products,
        'partner_contacts': partner_contacts,
    }
    return render(request, 'partners/supplier_form.html', context)


@login_required
def supplier_delete(request, pk):
    """حذف مورد نهائي من قاعدة البيانات"""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        supplier_name = supplier.name
        partner = supplier.partner
        # حذف المورد نهائياً
        supplier.delete()
        # حذف الشريك المرتبط أيضاً إن وجد
        if partner:
            partner.delete()
        messages.success(request, f'تم حذف المورد "{supplier_name}" نهائياً')
        return redirect('partners:suppliers_list')

    # إذا كان GET نعرض صفحة تأكيد بسيطة أو نرجعه للقائمة
    return redirect('partners:suppliers_list')


@login_required
def partners_reports(request):
    """تقارير الشركاء"""
    context = {
        'title': 'تقارير الشركاء',
    }
    return render(request, 'partners/reports.html', context)


@login_required
def customers_report(request):
    """تقرير العملاء"""
    customers = Partner.objects.filter(partner_type='customer', is_active=True)

    context = {
        'title': 'تقرير العملاء',
        'customers': customers,
    }
    return render(request, 'partners/customers_report.html', context)


@login_required
def suppliers_report(request):
    """تقرير الموردين"""
    suppliers = Partner.objects.filter(partner_type='supplier', is_active=True)

    context = {
        'title': 'تقرير الموردين',
        'suppliers': suppliers,
    }
    return render(request, 'partners/suppliers_report.html', context)


@login_required
def supplier_documents(request, supplier_id):
    """عرض مستندات مورد معين"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    documents = supplier.documents.all().order_by('-uploaded_at')

    # فلترة حسب النوع
    doc_type = request.GET.get('type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)

    # فلترة المستندات المنتهية
    show_expired = request.GET.get('expired')
    if show_expired == '1':
        documents = [doc for doc in documents if doc.is_expired]

    context = {
        'title': f'مستندات المورد: {supplier.name}',
        'supplier': supplier,
        'documents': documents,
        'document_types': SupplierDocument.DOCUMENT_TYPES,
        'current_type': doc_type,
    }
    return render(request, 'partners/supplier_documents.html', context)


@login_required
def supplier_document_add(request, supplier_id):
    """صفحة إضافة مستند جديد لمورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        title = request.POST.get('title', '').strip()
        document_number = request.POST.get('document_number', '').strip()
        issue_date = request.POST.get('issue_date') or None
        expiry_date = request.POST.get('expiry_date') or None
        notes = request.POST.get('notes', '').strip()
        file = request.FILES.get('file')

        if not document_type or not file:
            messages.error(request, 'نوع المستند والملف مطلوبان')
        else:
            try:
                doc = SupplierDocument.objects.create(
                    supplier=supplier,
                    document_type=document_type,
                    title=title or f'{dict(SupplierDocument.DOCUMENT_TYPES).get(document_type)}',
                    document_number=document_number,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    notes=notes,
                    file=file,
                    uploaded_by=request.user
                )
                messages.success(request, 'تم إضافة المستند بنجاح')
                return redirect('partners:partner_edit', pk=supplier.partner.pk)
            except Exception as e:
                messages.error(request, f'خطأ في إضافة المستند: {str(e)}')

    context = {
        'title': f'إضافة مستند - {supplier.name}',
        'supplier': supplier,
        'document_types': SupplierDocument.DOCUMENT_TYPES,
    }
    return render(request, 'partners/supplier_document_add.html', context)


@login_required
def supplier_document_upload(request, supplier_id):
    """رفع مستند جديد لمورد (API)"""
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        title = request.POST.get('title', '').strip()
        document_number = request.POST.get('document_number', '').strip()
        issue_date = request.POST.get('issue_date') or None
        expiry_date = request.POST.get('expiry_date') or None
        notes = request.POST.get('notes', '').strip()
        file = request.FILES.get('file')

        if not title or not file:
            messages.error(request, 'العنوان والملف مطلوبان')
            return redirect('partners:supplier_documents', supplier_id=supplier_id)

        try:
            doc = SupplierDocument.objects.create(
                supplier=supplier,
                document_type=document_type,
                title=title,
                document_number=document_number,
                file=file,
                issue_date=issue_date,
                expiry_date=expiry_date,
                notes=notes,
                uploaded_by=request.user
            )
            messages.success(request, f'تم رفع المستند "{title}" بنجاح')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم رفع المستند بنجاح',
                    'document_id': doc.id
                })
        except Exception as e:
            messages.error(request, f'خطأ في رفع المستند: {str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'خطأ: {str(e)}'
                }, status=400)

        return redirect('partners:supplier_documents', supplier_id=supplier_id)

    context = {
        'title': f'رفع مستند - {supplier.name}',
        'supplier': supplier,
        'document_types': SupplierDocument.DOCUMENT_TYPES,
    }
    return render(request, 'partners/supplier_document_upload.html', context)


@login_required
def supplier_document_delete(request, document_id):
    """حذف مستند مورد"""
    document = get_object_or_404(SupplierDocument, id=document_id)
    supplier = document.supplier
    partner_id = supplier.partner.pk

    try:
        # حذف الملف من النظام
        if document.file:
            document.file.delete()

        document.delete()
        messages.success(request, 'تم حذف المستند بنجاح')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        messages.error(request, f'خطأ في حذف المستند: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    # الرجوع لصفحة تعديل الشريك
    return redirect('partners:partner_edit', pk=partner_id)


@login_required
def supplier_document_download(request, document_id):
    """تحميل مستند مورد"""
    document = get_object_or_404(SupplierDocument, id=document_id)

    try:
        if document.file:
            response = FileResponse(document.file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
            return response
        else:
            raise Http404("الملف غير موجود")
    except Exception as e:
        messages.error(request, f'خطأ في تحميل المستند: {str(e)}')
        return redirect('partners:supplier_documents', supplier_id=document.supplier.id)


# ==================== منتجات الموردين ====================

@login_required
def supplier_products(request, supplier_id):
    """عرض منتجات مورد معين مع أسعارها"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    products = SupplierProduct.objects.filter(supplier=supplier).select_related('product').order_by('-is_preferred', 'product__name')

    # بحث
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(supplier_sku__icontains=search)
        )

    # فلترة
    show_active = request.GET.get('active')
    if show_active == '1':
        products = products.filter(is_active=True)
    elif show_active == '0':
        products = products.filter(is_active=False)

    context = {
        'title': f'منتجات المورد: {supplier.name}',
        'supplier': supplier,
        'products': products,
        'search_query': search,
        'show_active': show_active,
    }
    return render(request, 'partners/supplier_products.html', context)


@login_required
def supplier_product_add(request, supplier_id):
    """إضافة منتج جديد للمورد"""
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        product_id = request.POST.get('product')
        supplier_sku = request.POST.get('supplier_sku', '').strip()
        price_str = request.POST.get('price', '0')
        currency = request.POST.get('currency', 'EGP')
        min_qty_str = request.POST.get('minimum_order_quantity', '1')
        lead_time_str = request.POST.get('lead_time_days', '')
        uom = request.POST.get('uom', 'unit')
        is_preferred = request.POST.get('is_preferred') == 'on'
        is_active = request.POST.get('is_active', 'on') == 'on'
        notes = request.POST.get('notes', '').strip()

        try:
            price = Decimal(price_str)
            min_qty = Decimal(min_qty_str) if min_qty_str else Decimal('1')
            lead_time = int(lead_time_str) if lead_time_str else 0
        except (InvalidOperation, ValueError):
            messages.error(request, 'قيم غير صحيحة للسعر أو الكمية')
            return redirect('partners:supplier_product_add', supplier_id=supplier_id)

        if not product_id:
            messages.error(request, 'يجب اختيار منتج')
            return redirect('partners:supplier_product_add', supplier_id=supplier_id)

        from inventory.models import Product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            messages.error(request, 'المنتج غير موجود')
            return redirect('partners:supplier_product_add', supplier_id=supplier_id)

        # تحقق من عدم التكرار
        if SupplierProduct.objects.filter(supplier=supplier, product=product).exists():
            messages.error(request, f'المنتج "{product.name}" مرتبط بالفعل بهذا المورد')
            return redirect('partners:supplier_product_add', supplier_id=supplier_id)

        # إذا كان مفضل، إلغاء التفضيل من الآخرين
        if is_preferred:
            SupplierProduct.objects.filter(product=product, is_preferred=True).update(is_preferred=False)

        SupplierProduct.objects.create(
            supplier=supplier,
            product=product,
            supplier_sku=supplier_sku,
            price=price,
            currency=currency,
            minimum_order_quantity=min_qty,
            lead_time_days=lead_time,
            uom=uom,
            is_preferred=is_preferred,
            is_active=is_active,
            notes=notes,
        )

        messages.success(request, f'تم إضافة "{product.name}" بسعر {price} {currency}')
        return redirect('partners:supplier_products', supplier_id=supplier_id)

    # جلب المنتجات غير المرتبطة بالمورد
    from inventory.models import Product
    existing_product_ids = SupplierProduct.objects.filter(supplier=supplier).values_list('product_id', flat=True)
    available_products = Product.objects.filter(is_active=True).exclude(id__in=existing_product_ids).order_by('name')

    context = {
        'title': f'إضافة منتج للمورد: {supplier.name}',
        'supplier': supplier,
        'available_products': available_products,
        'currencies': [('EGP', 'جنيه مصري'), ('USD', 'دولار أمريكي'), ('EUR', 'يورو')],
        'uom_choices': SupplierProduct.UOM_CHOICES,
    }
    return render(request, 'partners/supplier_product_form.html', context)


@login_required
def supplier_product_add_ajax(request, supplier_id):
    """إضافة منتج للمورد بالـ AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طلب غير صحيح'}, status=400)

    supplier = get_object_or_404(Supplier, id=supplier_id)

    product_id = request.POST.get('product_id')
    price_str = request.POST.get('price', '0')
    min_qty_str = request.POST.get('minimum_order_quantity', '0')
    lead_time_str = request.POST.get('lead_time_days', '0')
    uom = request.POST.get('uom', 'unit')  # وحدة القياس

    try:
        price = Decimal(price_str)
        min_qty = Decimal(min_qty_str) if min_qty_str else Decimal('0')
        lead_time = int(lead_time_str) if lead_time_str else 0
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'قيم غير صحيحة'}, status=400)

    if not product_id:
        return JsonResponse({'success': False, 'error': 'يجب اختيار منتج'}, status=400)

    from inventory.models import Product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المنتج غير موجود'}, status=404)

    # تحقق من عدم التكرار
    if SupplierProduct.objects.filter(supplier=supplier, product=product).exists():
        return JsonResponse({'success': False, 'error': f'المنتج "{product.name}" مرتبط بالفعل'}, status=400)

    # إنشاء الربط
    sp = SupplierProduct.objects.create(
        supplier=supplier,
        product=product,
        price=price,
        currency='EGP',
        minimum_order_quantity=min_qty,
        lead_time_days=lead_time,
        uom=uom,  # حفظ وحدة القياس
        is_active=True,
    )

    return JsonResponse({
        'success': True,
        'message': f'تم إضافة "{product.name}" بنجاح',
        'id': sp.id
    })


@login_required
def supplier_product_edit(request, supplier_product_id):
    """تعديل سعر/بيانات منتج مورد"""
    sp = get_object_or_404(SupplierProduct, id=supplier_product_id)
    supplier = sp.supplier

    if request.method == 'POST':
        supplier_sku = request.POST.get('supplier_sku', '').strip()
        price_str = request.POST.get('price', '0')
        currency = request.POST.get('currency', 'EGP')
        min_qty_str = request.POST.get('minimum_order_quantity', '1')
        lead_time_str = request.POST.get('lead_time_days', '')
        uom = request.POST.get('uom', 'unit')
        is_preferred = request.POST.get('is_preferred') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        notes = request.POST.get('notes', '').strip()

        try:
            price = Decimal(price_str)
            min_qty = Decimal(min_qty_str) if min_qty_str else Decimal('1')
            lead_time = int(lead_time_str) if lead_time_str else 0
        except (InvalidOperation, ValueError):
            messages.error(request, 'قيم غير صحيحة للسعر أو الكمية')
            return redirect('partners:supplier_product_edit', supplier_product_id=supplier_product_id)

        # إذا كان مفضل، إلغاء التفضيل من الآخرين
        if is_preferred and not sp.is_preferred:
            SupplierProduct.objects.filter(product=sp.product, is_preferred=True).update(is_preferred=False)

        sp.supplier_sku = supplier_sku
        sp.price = price
        sp.currency = currency
        sp.minimum_order_quantity = min_qty
        sp.lead_time_days = lead_time
        sp.uom = uom
        sp.is_preferred = is_preferred
        sp.is_active = is_active
        sp.notes = notes
        sp.save()

        # تحديث تكلفة المنتج إذا كان هذا المورد هو المفضل
        if is_preferred:
            sp.product.cost = price
            sp.product.save(update_fields=['cost'])

        messages.success(request, f'تم تحديث سعر "{sp.product.name}" إلى {price} {currency}')
        return redirect('partners:supplier_products', supplier_id=supplier.id)

    context = {
        'title': f'تعديل سعر: {sp.product.name}',
        'supplier': supplier,
        'supplier_product': sp,
        'currencies': [('EGP', 'جنيه مصري'), ('USD', 'دولار أمريكي'), ('EUR', 'يورو')],
        'uom_choices': SupplierProduct.UOM_CHOICES,
        'edit_mode': True,
    }
    return render(request, 'partners/supplier_product_form.html', context)


@login_required
def supplier_product_delete(request, supplier_product_id):
    """حذف منتج من المورد"""
    sp = get_object_or_404(SupplierProduct, id=supplier_product_id)
    supplier_id = sp.supplier.id
    product_name = sp.product.name

    if request.method == 'POST':
        sp.delete()
        messages.success(request, f'تم حذف "{product_name}" من قائمة منتجات المورد')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

    return redirect('partners:supplier_products', supplier_id=supplier_id)


@login_required
def all_supplier_products(request):
    """عرض جميع منتجات الموردين"""
    products = SupplierProduct.objects.select_related('supplier', 'product').order_by('product__name', '-is_preferred')

    # بحث
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(supplier__name__icontains=search)
        )

    # فلترة حسب المورد
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)

    # فلترة حسب المنتج
    product_id = request.GET.get('product')
    if product_id:
        products = products.filter(product_id=product_id)

    # ترقيم الصفحات
    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    context = {
        'title': 'أسعار الموردين',
        'products': products_page,
        'suppliers': Supplier.objects.all().order_by('name'),
        'search_query': search,
        'current_supplier': supplier_id,
    }
    return render(request, 'partners/all_supplier_products.html', context)


@login_required
def supplier_account(request, supplier_id):
    """عرض حساب المورد - الفواتير والدفعات والرصيد"""
    supplier = get_object_or_404(Supplier, pk=supplier_id)

    # استيراد النماذج
    from purchases.models import PurchaseBill, SupplierPayment

    # التحقق من وجود Partner مرتبط
    if not supplier.partner:
        from django.contrib import messages
        messages.error(request, 'هذا المورد غير مرتبط بسجل شريك. يرجى تحديث بيانات المورد.')
        return redirect('partners:suppliers_list')

    # جلب الفواتير
    bills = PurchaseBill.objects.filter(
        supplier=supplier.partner,
        is_deleted=False
    ).select_related('supplier').prefetch_related('items').order_by('-date')

    # جلب الدفعات
    payments = SupplierPayment.objects.filter(
        supplier=supplier.partner
    ).select_related('bill', 'payment_method').order_by('-date')

    # حساب الإجماليات
    total_bills = bills.aggregate(total=Sum('paid'))['total'] or Decimal('0')
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # حساب إجمالي الفواتير (قبل الدفع)
    bills_total_amount = sum(bill.total for bill in bills)

    # الرصيد = إجمالي الفواتير - إجمالي الدفعات
    balance = bills_total_amount - total_payments

    context = {
        'title': f'حساب المورد: {supplier.name}',
        'supplier': supplier,
        'bills': bills,
        'payments': payments,
        'total_bills': bills_total_amount,
        'total_payments': total_payments,
        'balance': balance,
    }
    return render(request, 'partners/supplier_account.html', context)


@login_required
def quick_price_update(request):
    """
    صفحة تحديث أسعار الموردين بسرعة
    - عرض جميع المنتجات مع أسعار الموردين
    - تحديث الأسعار بشكل سريع inline
    - فلترة حسب المورد أو الفئة
    """
    from inventory.models import Product, Category

    # الفلاتر
    supplier_id = request.GET.get('supplier', '')
    category_id = request.GET.get('category', '')
    raw_material_type = request.GET.get('raw_material_type', '')
    search = request.GET.get('search', '')

    # جلب منتجات الموردين
    products_qs = SupplierProduct.objects.select_related(
        'supplier', 'product', 'product__category'
    ).filter(is_active=True).order_by('product__name', '-is_preferred')

    # فلترة
    if supplier_id:
        products_qs = products_qs.filter(supplier_id=supplier_id)
    if category_id:
        products_qs = products_qs.filter(product__category_id=category_id)
    if raw_material_type:
        products_qs = products_qs.filter(product__raw_material_type=raw_material_type)
    if search:
        products_qs = products_qs.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(supplier__name__icontains=search)
        )

    # معالجة التحديث
    if request.method == 'POST':
        updated_count = 0
        errors = []

        for key, value in request.POST.items():
            if key.startswith('price_'):
                try:
                    sp_id = int(key.replace('price_', ''))
                    new_price = Decimal(value.strip() or '0')

                    sp = SupplierProduct.objects.get(id=sp_id)
                    if sp.price != new_price:
                        old_price = sp.price
                        sp.price = new_price
                        sp.save()

                        # تحديث تكلفة المنتج إذا كان هذا المورد هو المفضل
                        if sp.is_preferred:
                            sp.product.cost = new_price
                            sp.product.save(update_fields=['cost'])

                        updated_count += 1
                except Exception as e:
                    errors.append(str(e))

        if updated_count > 0:
            messages.success(request, f'تم تحديث {updated_count} سعر بنجاح')
        if errors:
            messages.warning(request, f'حدثت أخطاء: {", ".join(errors[:3])}')

        return redirect(request.get_full_path())

    # تجميع المنتجات حسب المنتج لعرض جميع موردين كل منتج
    products_by_product = {}
    for sp in products_qs:
        if sp.product_id not in products_by_product:
            products_by_product[sp.product_id] = {
                'product': sp.product,
                'suppliers': []
            }
        products_by_product[sp.product_id]['suppliers'].append(sp)

    context = {
        'title': 'تحديث أسعار الموردين السريع',
        'products_by_product': products_by_product.values(),
        'suppliers': Supplier.objects.all().order_by('name'),
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'raw_material_types': Product.RAW_MATERIAL_TYPE_CHOICES,
        'current_supplier': supplier_id,
        'current_category': category_id,
        'current_raw_material_type': raw_material_type,
        'search_query': search,
    }
    return render(request, 'partners/quick_price_update.html', context)
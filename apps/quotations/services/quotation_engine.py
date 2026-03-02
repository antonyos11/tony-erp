"""
محرك عروض الأسعار — RITA ERP
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.quotations.models import Quotation, QuotationLine, QuotationFollowUp
from apps.sales.models import Customer
from apps.accounts.services.vat_engine import VATEngine


class QuotationEngine:

    @staticmethod
    def _generate_quotation_number():
        today = timezone.now()
        count = Quotation.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1
        return f"QT-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_quotation(cls, customer=None, prospect_data=None, branch=None,
                         salesperson=None, items=None, valid_days=15,
                         discount_percentage=0, is_taxable=True,
                         delivery_required=False, delivery_fee=0,
                         terms='', notes='', user=None):
        """
        إنشاء عرض سعر

        customer: عميل موجود (اختياري)
        prospect_data: بيانات عميل محتمل (لو مش مسجل)
        items: [{'product': obj, 'quantity': 5, 'unit_price': 200, 'discount_percentage': 0}, ...]
        """
        quotation = Quotation.objects.create(
            quotation_number=cls._generate_quotation_number(),
            date=timezone.now(),
            valid_until=timezone.now().date() + timezone.timedelta(days=valid_days),
            customer=customer,
            prospect_name=prospect_data.get('name', '') if prospect_data else '',
            prospect_phone=prospect_data.get('phone', '') if prospect_data else '',
            prospect_email=prospect_data.get('email', '') if prospect_data else '',
            prospect_address=prospect_data.get('address', '') if prospect_data else '',
            prospect_company=prospect_data.get('company', '') if prospect_data else '',
            branch=branch,
            salesperson=salesperson,
            discount_percentage=discount_percentage,
            is_taxable=is_taxable,
            delivery_required=delivery_required,
            delivery_fee=delivery_fee,
            terms_and_conditions=terms,
            customer_notes=notes,
            created_by=user,
            updated_by=user,
        )

        subtotal = Decimal('0')
        for i, item in enumerate(items or []):
            product = item['product']
            qty = Decimal(str(item['quantity']))
            price = Decimal(str(item['unit_price']))
            disc_pct = Decimal(str(item.get('discount_percentage', 0)))

            line_total = qty * price
            line_disc = line_total * disc_pct / 100
            line_sub = line_total - line_disc

            est_cost = product.cost_price * qty
            est_profit = line_sub - est_cost

            QuotationLine.objects.create(
                quotation=quotation,
                product=product,
                description=item.get('description', product.name),
                quantity=qty,
                unit_price=price,
                discount_percentage=disc_pct,
                discount_amount=line_disc,
                subtotal=line_sub,
                custom_width=item.get('custom_width'),
                custom_length=item.get('custom_length'),
                custom_height=item.get('custom_height'),
                estimated_cost=est_cost,
                estimated_profit=est_profit,
                notes=item.get('notes', ''),
                sort_order=i,
            )
            subtotal += line_sub

        # حساب الإجماليات
        invoice_disc = subtotal * Decimal(str(discount_percentage)) / 100
        taxable = subtotal - invoice_disc
        tax = Decimal('0')
        if is_taxable:
            vat = VATEngine.calculate_tax(taxable)
            tax = vat['tax_amount']

        total = taxable + tax + Decimal(str(delivery_fee))

        quotation.subtotal = subtotal
        quotation.discount_amount = invoice_disc
        quotation.taxable_amount = taxable
        quotation.tax_amount = tax
        quotation.total = total
        quotation.save()

        return quotation

    @classmethod
    @transaction.atomic
    def revise_quotation(cls, quotation, items, discount_percentage=0, user=None):
        """
        تعديل عرض سعر — ينشئ نسخة معدّلة
        """
        quotation.revision_number += 1
        quotation.status = 'revised'

        # حذف السطور القديمة
        quotation.lines.all().delete()

        subtotal = Decimal('0')
        for i, item in enumerate(items):
            product = item['product']
            qty = Decimal(str(item['quantity']))
            price = Decimal(str(item['unit_price']))
            disc_pct = Decimal(str(item.get('discount_percentage', 0)))

            line_total = qty * price
            line_disc = line_total * disc_pct / 100
            line_sub = line_total - line_disc

            QuotationLine.objects.create(
                quotation=quotation,
                product=product,
                quantity=qty,
                unit_price=price,
                discount_percentage=disc_pct,
                discount_amount=line_disc,
                subtotal=line_sub,
                estimated_cost=product.cost_price * qty,
                estimated_profit=line_sub - (product.cost_price * qty),
                sort_order=i,
            )
            subtotal += line_sub

        invoice_disc = subtotal * Decimal(str(discount_percentage)) / 100
        taxable = subtotal - invoice_disc
        tax = Decimal('0')
        if quotation.is_taxable:
            vat = VATEngine.calculate_tax(taxable)
            tax = vat['tax_amount']

        quotation.subtotal = subtotal
        quotation.discount_percentage = discount_percentage
        quotation.discount_amount = invoice_disc
        quotation.taxable_amount = taxable
        quotation.tax_amount = tax
        quotation.total = taxable + tax + quotation.delivery_fee
        quotation.updated_by = user
        quotation.save()
        return quotation

    @classmethod
    @transaction.atomic
    def convert_to_invoice(cls, quotation, user=None):
        """
        تحويل عرض سعر مقبول إلى فاتورة بيع
        """
        if quotation.status != 'accepted':
            raise ValueError("العرض يجب أن يكون مقبولاً أولاً")

        from apps.sales.services.sales_engine import SalesEngine

        # لو العميل مش مسجل — نسجله
        customer = quotation.customer
        if not customer and quotation.prospect_name:
            customer = cls.quick_create_customer(quotation, user)
            quotation.customer = customer
            quotation.save()

        if not customer:
            raise ValueError("لا يوجد عميل مرتبط بالعرض")

        # تحضير الأصناف
        items = []
        for line in quotation.lines.all():
            items.append({
                'product': line.product,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'discount_percentage': line.discount_percentage,
                'custom_width': line.custom_width,
                'custom_length': line.custom_length,
                'notes': line.notes,
            })

        # إنشاء الفاتورة
        invoice = SalesEngine.create_invoice(
            customer=customer,
            branch=quotation.branch,
            warehouse=quotation.branch.warehouses.filter(
                warehouse_type__in=['branch', 'finished']
            ).first(),
            salesperson=quotation.salesperson,
            items=items,
            discount_percentage=float(quotation.discount_percentage),
            is_taxable=quotation.is_taxable,
            delivery_required=quotation.delivery_required,
            delivery_address=quotation.delivery_address,
            delivery_fee=float(quotation.delivery_fee),
            notes=f'محوّل من عرض سعر {quotation.quotation_number}',
            user=user,
        )

        quotation.converted_invoice = invoice
        quotation.status = 'converted'
        quotation.updated_by = user
        quotation.save()

        return invoice

    @classmethod
    def quick_create_customer(cls, quotation, user=None):
        """
        إنشاء عميل سريع من بيانات عرض السعر
        """
        last = Customer.objects.order_by('-code').first()
        if last and last.code.startswith('C'):
            try:
                new_num = int(last.code[1:]) + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1

        customer = Customer.objects.create(
            code=f'C{new_num:04d}',
            name=quotation.prospect_name,
            customer_type='retail',
            phone=quotation.prospect_phone,
            address=quotation.prospect_address,
            branch=quotation.branch,
            is_active=True,
            created_by=user,
            updated_by=user,
        )
        return customer

    @classmethod
    def add_follow_up(cls, quotation, follow_up_type, result, notes,
                      next_date=None, user=None):
        """إضافة متابعة"""
        follow_up = QuotationFollowUp.objects.create(
            quotation=quotation,
            date=timezone.now(),
            follow_up_type=follow_up_type,
            result=result,
            notes=notes,
            next_follow_up_date=next_date,
            created_by=user,
            updated_by=user,
        )

        quotation.follow_up_date = next_date
        if result == 'will_buy':
            quotation.status = 'accepted'
        elif result == 'lost':
            quotation.status = 'rejected'
        elif result == 'needs_revision':
            quotation.status = 'negotiation'
        quotation.save()

        return follow_up

    @classmethod
    def get_quotation_stats(cls, branch=None, salesperson=None):
        """إحصائيات عروض الأسعار"""
        from django.db.models import Count, Sum, Q

        filters = {}
        if branch:
            filters['branch'] = branch
        if salesperson:
            filters['salesperson'] = salesperson

        qs = Quotation.objects.filter(**filters)

        total = qs.count()
        accepted = qs.filter(status='accepted').count()
        converted = qs.filter(status='converted').count()
        rejected = qs.filter(status='rejected').count()
        pending = qs.filter(status__in=['draft', 'sent', 'negotiation']).count()

        conversion_rate = ((accepted + converted) / total * 100) if total > 0 else 0

        total_value = qs.filter(
            status__in=['accepted', 'converted']
        ).aggregate(total=Sum('total'))['total'] or 0

        return {
            'total': total,
            'accepted': accepted,
            'converted': converted,
            'rejected': rejected,
            'pending': pending,
            'conversion_rate': round(conversion_rate, 1),
            'total_value': total_value,
        }

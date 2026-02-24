# pyright: reportAttributeAccessIssue=false
from django.db import models
from decimal import Decimal
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import random
import string
import uuid
from core.sequence_utils import next_sequence, format_code


def _generate_unique_barcode(length: int = 12):
	"""توليد باركود رقمي فريد بطول محدد (افتراضي 12 رقم)."""
	length = max(8, min(int(length or 12), 20))  # حمايات ضد القيم غير المنطقية
	while True:
		code = ''.join(random.choice('0123456789') for _ in range(length))
		if not Product.objects.filter(barcode=code).exists():  # type: ignore[name-defined]
			return code


# واجهة عامة مستخدمة في أماكن متعددة (السابق كان مفقوداً ويكسر بعض الشاشات)
def generate_unique_barcode(length: int = 12):
	return _generate_unique_barcode(length)


class Category(models.Model):
	"""فئات المنتجات - للتصنيف والتقارير"""
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=100, unique=True, verbose_name=_('اسم الفئة'))
	description = models.TextField(blank=True, verbose_name=_('الوصف'))
	parent = models.ForeignKey(
		'self',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='children',
		verbose_name=_('الفئة الأم')
	)
	image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name=_('صورة الفئة'))
	is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
	sort_order = models.PositiveIntegerField(default=0, verbose_name=_('ترتيب العرض'))
	created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
	updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))

	class Meta:
		verbose_name = _('فئة')
		verbose_name_plural = _('الفئات')
		ordering = ['sort_order', 'name']
		indexes = [
			models.Index(fields=['name']),
			models.Index(fields=['is_active']),
		]

	def __str__(self):
		if self.parent:
			return f"{self.parent.name} > {self.name}"
		return self.name

	@property
	def full_path(self):
		"""المسار الكامل للفئة"""
		path = [self.name]
		parent = self.parent
		while parent:
			path.insert(0, parent.name)
			parent = parent.parent
		return ' > '.join(path)

	@property
	def product_count(self):
		"""عدد المنتجات في هذه الفئة"""
		return self.products.count()


class Product(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	sku = models.CharField(max_length=100, unique=True)
	name = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	image = models.ImageField(
		upload_to='products/',
		blank=True,
		null=True,
		verbose_name=_('صورة المنتج')
	)
	category = models.ForeignKey(
		Category,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='products',
		verbose_name=_('الفئة')
	)
	price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
	cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
	promo_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
	promo_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	promo_start = models.DateField(null=True, blank=True)
	promo_end = models.DateField(null=True, blank=True)
	is_promo_active = models.BooleanField(default=False)
	min_stock = models.PositiveIntegerField(default=0)
	UOM_CHOICES = [
		('unit', _('وحدة')),
		('kg', _('كيلوجرام')),
		('g', _('جرام')),
		('ton', _('طن')),
		('m', _('متر')),
		('m2', _('متر مربع')),
		('m3', _('متر مكعب')),
		('cm', _('سنتيمتر')),
		('mm', _('مليمتر')),
		('liter', _('لتر')),
		('gallon', _('جالون')),
		('barrel', _('برميل')),
		('can', _('صفيحة')),
		('box', _('صندوق')),
		('carton', _('كرتونة')),
		('pallet', _('بالت')),
		('roll', _('لفة')),
		('sheet', _('لوح/ورقة')),
		('bag', _('كيس/شكارة')),
		('piece', _('قطعة')),
	]
	purchase_uom = models.CharField(max_length=10, choices=UOM_CHOICES, default='unit')
	usage_uom = models.CharField(max_length=10, choices=UOM_CHOICES, default='unit')
	conversion_factor = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('1'))
	
	# حساب معامل التحويل تلقائياً من الأبعاد (length/width/height معرفين أسفل كـ PositiveIntegerField)
	auto_calculate_conversion = models.BooleanField(
		default=False,
		verbose_name=_('حساب معامل التحويل تلقائياً'),
		help_text=_('إذا كان محدداً، سيتم حساب معامل التحويل من الأبعاد (طول × عرض × ارتفاع)')
	)
	
	# حقول إضافية للمواد الخام
	PRODUCT_TYPE_CHOICES = [
		('raw_material', _('مادة خام')),
		('semi_finished', _('نصف مصنع')),
		('finished', _('منتج تام')),
		('spare_part', _('قطعة غيار')),
		('service', _('خدمة')),
	]
	product_type = models.CharField(
		max_length=20,
		choices=PRODUCT_TYPE_CHOICES,
		default='finished',
		verbose_name=_('نوع المنتج')
	)

	# نوع المادة الخام (للتحكم في طريقة الإدخال والوحدات)
	RAW_MATERIAL_TYPE_CHOICES = [
		('foam', _('إسفنج')),
		('pad', _('باد/لباد')),
		('glue', _('غراء')),
		('fiber', _('فيبر')),
		('thread', _('خيوط')),
		('vaseline', _('فازلين')),
		('fabric', _('أقمشة')),
		('spring', _('سوست')),
		('wood', _('خشب')),
		('metal', _('معدن')),
		('other', _('أخرى')),
	]
	raw_material_type = models.CharField(
		max_length=20,
		choices=RAW_MATERIAL_TYPE_CHOICES,
		blank=True,
		default='',
		verbose_name=_('نوع المادة الخام'),
		help_text=_('يحدد كيفية إدخال المادة ووحداتها')
	)
	
	# لدعم الموردين المتعددين للمادة الواحدة
	preferred_supplier = models.ForeignKey(
		'partners.Supplier',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='preferred_products',
		verbose_name=_('المورد المفضل')
	)
	
	# سعر الشراء من المورد (بوحدة الشراء)
	purchase_price = models.DecimalField(
		max_digits=15,
		decimal_places=2,
		default=Decimal('0'),
		verbose_name=_('سعر وحدة الشراء'),
		help_text=_('سعر الشراء من المورد بوحدة الشراء (طن، كيلو، صفيحة، الخ)')
	)
	
	# تكلفة وحدة الاستخدام المحسوبة (تلقائي)
	usage_unit_cost = models.DecimalField(
		max_digits=15,
		decimal_places=4,
		default=Decimal('0'),
		verbose_name=_('تكلفة وحدة الاستخدام'),
		help_text=_('يتم حسابها تلقائياً = سعر الشراء ÷ معامل التحويل')
	)

	# نسبة الهدر (Waste Percentage)
	waste_percentage = models.DecimalField(
		max_digits=5, 
		decimal_places=2, 
		default=Decimal('0.00'),
		verbose_name=_('نسبة الهدر %'),
		help_text=_('نسبة الهدر المتوقعة (مثلاً 5% للقص) تضاف للتكلفة')
	)
	
	# لدعم الباركود اليدوي أو التلقائي
	manual_barcode = models.BooleanField(
		default=False,
		verbose_name=_('باركود يدوي'),
		help_text=_('إذا كان محدداً، لن يتم توليد باركود تلقائياً')
	)
	barcode = models.CharField(max_length=20, unique=True, blank=True, null=True)
	is_third_party = models.BooleanField(default=False)
	is_active = models.BooleanField(
		default=True,
		verbose_name=_('نشط'),
		help_text=_('هل المنتج نشط ويظهر في القوائم؟')
	)
	internal_code = models.CharField(max_length=30, unique=True, blank=True, null=True)
	production_department_code = models.CharField(
		max_length=50,
		blank=True,
		help_text=_('كود قسم الإنتاج المرتبط (اختياري، يطابق كود القسم في الموارد البشرية إن استخدمته)')
	)
	
	# حقول المتجر الإلكتروني
	show_in_store = models.BooleanField(
		default=True,
		verbose_name=_('إظهار في المتجر الإلكتروني'),
		help_text=_('هل يظهر هذا المنتج في المتجر الإلكتروني؟')
	)
	is_new = models.BooleanField(
		default=False,
		verbose_name=_('منتج جديد'),
		help_text=_('علامة المنتج كـ "جديد" للعرض في المتجر')
	)
	new_until = models.DateField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ انتهاء علامة جديد'),
		help_text=_('تاريخ انتهاء ظهور علامة "جديد" (اختياري)')
	)
	store_description = models.TextField(
		blank=True,
		verbose_name=_('وصف المتجر'),
		help_text=_('وصف مفصل للعرض في المتجر الإلكتروني')
	)
	store_featured = models.BooleanField(
		default=False,
		verbose_name=_('منتج مميز'),
		help_text=_('عرض المنتج كمميز في الصفحة الرئيسية')
	)
	
	# حقول المقاسات (للمنتجات ذات الأبعاد مثل المراتب)
	width = models.PositiveIntegerField(
		null=True,
		blank=True,
		verbose_name=_('العرض (سم)'),
		help_text=_('عرض المنتج بالسنتيمتر')
	)
	length = models.PositiveIntegerField(
		null=True,
		blank=True,
		verbose_name=_('الطول (سم)'),
		help_text=_('طول المنتج بالسنتيمتر')
	)
	height = models.PositiveIntegerField(
		null=True,
		blank=True,
		verbose_name=_('الارتفاع (سم)'),
		help_text=_('ارتفاع المنتج بالسنتيمتر')
	)

	class Meta:
		indexes = [
			models.Index(fields=['sku']),
			models.Index(fields=['name']),
		]

	def __str__(self):  # pragma: no cover - simple repr
		return f"{self.sku} - {self.name}"

	@property
	def effective_price(self):
		from django.utils import timezone
		if not self.is_promo_active:
			return self.price
		today = timezone.now().date()
		if self.promo_start and today < self.promo_start:
			return self.price
		if self.promo_end and today > self.promo_end:
			return self.price
		if self.promo_price and self.promo_price > 0:
			return self.promo_price
		try:
			pct = float(self.promo_percent)
			if pct <= 0:
				return self.price
			discounted = (self.price * (Decimal('100') - Decimal(str(pct))) / Decimal('100')).quantize(Decimal('0.01'))
			return discounted
		except Exception:
			return self.price

	def convert_qty_purchase_to_usage(self, qty_purchase: float) -> float:
		try:
			return float(qty_purchase) * float(self.conversion_factor or 1)
		except Exception:
			return float(qty_purchase)

	def convert_cost_per_usage_unit(self) -> float:
		try:
			cf = float(self.conversion_factor or 1) or 1.0
			return float(self.cost) / cf
		except Exception:
			return float(self.cost)
	
	def calculate_conversion_from_dimensions(self):
		"""
		حساب معامل التحويل من الأبعاد بناءً على وحدات الشراء والاستخدام
		المعامل = كم وحدة استخدام تطلع من 1 وحدة شراء
		"""
		purchase = self.purchase_uom or 'unit'
		usage = self.usage_uom or 'unit'

		# نفس الوحدة = لا حاجة للتحويل
		if purchase == usage:
			return Decimal('1')

		if not (self.length and self.width and self.height):
			return self.conversion_factor or Decimal('1')

		try:
			length = self.length
			width = self.width
			height = self.height  # السُمك

			vol_units = ('m3',)
			area_units = ('m2',)
			length_units = ('m', 'cm', 'mm')
			piece_units = ('unit', 'piece', 'sheet')

			# شراء بالحجم (م³) واستخدام بالقطعة/لوح
			if purchase in vol_units and usage in piece_units:
				volume_per_piece = length * width * height
				if volume_per_piece > 0:
					return (Decimal('1') / volume_per_piece).quantize(Decimal('0.0001'))

			# شراء بالقطعة واستخدام بالحجم
			elif purchase in piece_units and usage in vol_units:
				return (length * width * height).quantize(Decimal('0.0001'))

			# شراء بالمساحة (م²) واستخدام بالقطعة
			elif purchase in area_units and usage in piece_units:
				area = length * width
				if area > 0:
					return (Decimal('1') / area).quantize(Decimal('0.0001'))

			# شراء بالقطعة واستخدام بالمساحة
			elif purchase in piece_units and usage in area_units:
				return (length * width).quantize(Decimal('0.0001'))

			# شراء بالحجم واستخدام بالمساحة
			elif purchase in vol_units and usage in area_units:
				if height > 0:
					return (Decimal('1') / height).quantize(Decimal('0.0001'))

			# شراء بالمساحة واستخدام بالحجم
			elif purchase in area_units and usage in vol_units:
				return height.quantize(Decimal('0.0001'))

			# شراء بالمتر واستخدام بالقطعة
			elif purchase in length_units and usage in piece_units:
				if length > 0:
					return (Decimal('1') / length).quantize(Decimal('0.0001'))

			# شراء بالقطعة واستخدام بالمتر
			elif purchase in piece_units and usage in length_units:
				return length.quantize(Decimal('0.0001'))

			# حالة افتراضية
			return self.conversion_factor or Decimal('1')

		except Exception:
			return self.conversion_factor or Decimal('1')
	
	def calculate_usage_unit_cost(self):
		"""
		حساب تكلفة وحدة الاستخدام من سعر الشراء ومعامل التحويل ونسبة الهدر
		الصيغة: تكلفة وحدة الاستخدام = (سعر الشراء ÷ معامل التحويل) × (1 + نسبة الهدر)
		"""
		if not self.purchase_price or self.purchase_price <= 0:
			return Decimal('0')
		
		try:
			conversion = self.conversion_factor or Decimal('1')
			if conversion <= 0:
				conversion = Decimal('1')
			
			# 1. التكلفة الأساسية
			base_cost = self.purchase_price / conversion
			
			# 2. إضافة نسبة الهدر
			waste_factor = Decimal('1') + (self.waste_percentage / Decimal('100'))
			final_cost = base_cost * waste_factor
			
			return final_cost.quantize(Decimal('0.0001'))
			
		except Exception:
			return Decimal('0')

	def save(self, *args, **kwargs):  # pragma: no cover - simple deterministic generation
		# توليد باركود تلقائي فقط إذا لم يكن موجوداً ولم يكن يدوياً
		if not self.barcode and not self.manual_barcode:
			self.barcode = generate_unique_barcode()
		if not self.internal_code:
			# استخدم SKU كاملاً لتجنب التعارض بين المنتجات المتشابهة في الاسم
			base_code = f"INT{self.sku}"[:30]
			code = base_code
			counter = 1
			while Product.objects.filter(internal_code=code).exclude(
				pk=self.pk if self.pk else 0
			).exists():
				suffix = f"-{counter}"
				code = base_code[:30 - len(suffix)] + suffix
				counter += 1
			self.internal_code = code
		
		# حساب معامل التحويل تلقائياً من الأبعاد (للمواد الخام فقط)
		if self.product_type == 'raw_material' and self.auto_calculate_conversion:
			self.conversion_factor = self.calculate_conversion_from_dimensions()
		
		# حساب تكلفة وحدة الاستخدام تلقائياً (للمواد الخام فقط)
		if self.product_type == 'raw_material':
			self.usage_unit_cost = self.calculate_usage_unit_cost()
			# تحديث cost ليكون تكلفة وحدة الاستخدام (للاستخدام في BOM)
			self.cost = self.usage_unit_cost
		
		super().save(*args, **kwargs)

	@property
	def current_stock(self):
		"""إجمالي الكمية المتوفرة لكل المواقع (يدعم استدعاءات التقارير والإشعارات)."""
		try:
			from django.db.models import Sum
			return self.stocks.aggregate(total=Sum('quantity'))['total'] or 0
		except Exception:
			return 0

	@property
	def is_low_stock(self):
		"""تحديد إن كان المخزون منخفضاً مقارنةً بالحد الأدنى."""
		try:
			return self.current_stock <= (self.min_stock or 0)
		except Exception:
			return False

	@property
	def is_new_product(self):
		"""تحديد إن كان المنتج لا يزال يحمل علامة 'جديد'."""
		from django.utils import timezone
		if not self.is_new:
			return False
		if self.new_until:
			return timezone.now().date() <= self.new_until
		return True

	@property
	def sale_price(self):
		"""سعر البيع - للتوافق مع القالب"""
		return self.price
	
	@property
	def total_value(self):
		"""القيمة الإجمالية للمخزون"""
		try:
			return self.current_stock * float(self.price)
		except Exception:
			return 0


# =====================
# وحدات التعبئة للمواد الخام
# =====================

class PackagingUnit(models.Model):
	"""
	وحدات التعبئة للمواد الخام
	مثل: صفيحة غراء 20 كجم، برميل غراء 200 كجم، لوح إسفنج 200×100×10 سم
	"""
	id = models.AutoField(primary_key=True)

	product = models.ForeignKey(
		Product,
		on_delete=models.CASCADE,
		related_name='packaging_units',
		verbose_name=_('المنتج')
	)

	# اسم وحدة التعبئة
	name = models.CharField(
		max_length=100,
		verbose_name=_('اسم وحدة التعبئة'),
		help_text=_('مثل: صفيحة 20 كجم، برميل 200 كجم، لوح 200×100×10')
	)

	# الكمية في الوحدة (بوحدة الشراء)
	quantity_per_unit = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		verbose_name=_('الكمية في الوحدة'),
		help_text=_('مثل: 20 كجم للصفيحة، 200 كجم للبرميل')
	)

	# نوع وحدة التعبئة
	PACKAGING_TYPE_CHOICES = [
		('tin', _('صفيحة')),
		('barrel', _('برميل')),
		('sheet', _('لوح/فرخ')),
		('roll', _('لفة/رول')),
		('bag', _('شيكارة/كيس')),
		('box', _('كرتونة/صندوق')),
		('pallet', _('باليت')),
		('other', _('أخرى')),
	]
	packaging_type = models.CharField(
		max_length=20,
		choices=PACKAGING_TYPE_CHOICES,
		default='other',
		verbose_name=_('نوع التعبئة')
	)

	# أبعاد اللوح/الفرخ (للإسفنج والباد)
	length_cm = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('الطول (سم)'),
		help_text=_('طول اللوح بالسنتيمتر')
	)
	width_cm = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('العرض (سم)'),
		help_text=_('عرض اللوح بالسنتيمتر')
	)
	height_cm = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('الارتفاع/السُمك (سم)'),
		help_text=_('ارتفاع أو سُمك اللوح بالسنتيمتر')
	)

	# الوزن (للباد وغيره)
	weight_kg = models.DecimalField(
		max_digits=10,
		decimal_places=3,
		null=True,
		blank=True,
		verbose_name=_('الوزن (كجم)'),
		help_text=_('وزن الوحدة بالكيلوجرام')
	)

	# السعر المحسوب للوحدة
	calculated_price = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('السعر المحسوب'),
		help_text=_('سعر الوحدة محسوب من سعر الكيلو/المتر المكعب')
	)

	# ترتيب العرض
	sort_order = models.PositiveIntegerField(default=0, verbose_name=_('الترتيب'))
	is_default = models.BooleanField(default=False, verbose_name=_('الافتراضي'))
	is_active = models.BooleanField(default=True, verbose_name=_('نشط'))

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _('وحدة تعبئة')
		verbose_name_plural = _('وحدات التعبئة')
		ordering = ['product', 'sort_order', 'name']
		indexes = [
			models.Index(fields=['product', 'is_active']),
			models.Index(fields=['packaging_type']),
		]

	def __str__(self):
		return f"{self.product.name} - {self.name}"

	@property
	def volume_m3(self):
		"""حساب الحجم بالمتر المكعب (للألواح)"""
		if self.length_cm and self.width_cm and self.height_cm:
			return (self.length_cm * self.width_cm * self.height_cm) / Decimal('1000000')
		return None

	@property
	def dimensions_text(self):
		"""نص الأبعاد"""
		if self.length_cm and self.width_cm:
			if self.height_cm:
				return f"{self.length_cm}×{self.width_cm}×{self.height_cm} سم"
			return f"{self.length_cm}×{self.width_cm} سم"
		return ""

	def calculate_price(self):
		"""حساب سعر الوحدة من سعر المنتج الأساسي"""
		if not self.product.cost:
			return Decimal('0')

		# للألواح: السعر = الحجم × سعر المتر المكعب
		if self.volume_m3 and self.product.purchase_uom == 'm3':
			return self.volume_m3 * self.product.cost

		# للوزن: السعر = الوزن × سعر الكيلو
		if self.weight_kg and self.product.purchase_uom == 'kg':
			return self.weight_kg * self.product.cost

		# للكمية العادية
		if self.quantity_per_unit:
			return self.quantity_per_unit * self.product.cost

		return Decimal('0')

	def save(self, *args, **kwargs):
		# حساب السعر تلقائياً
		self.calculated_price = self.calculate_price()

		# إذا كانت وحدة افتراضية، إلغاء الافتراضي من الباقي
		if self.is_default:
			PackagingUnit.objects.filter(
				product=self.product,
				is_default=True
			).exclude(pk=self.pk).update(is_default=False)

		super().save(*args, **kwargs)


# =====================
# قوالب المنتجات
# =====================

class ProductTemplate(models.Model):
	"""
	قوالب جاهزة للمنتجات - لتسريع إضافة منتجات متشابهة
	"""
	id = models.AutoField(primary_key=True)
	
	name = models.CharField(
		max_length=255,
		verbose_name=_('اسم القالب'),
		help_text=_('اسم وصفي للقالب (مثل: قالب إسفنج قياسي)')
	)
	
	description = models.TextField(
		blank=True,
		verbose_name=_('الوصف'),
		help_text=_('وصف القالب ومتى يستخدم')
	)
	
	# نوع المنتج
	product_type = models.CharField(
		max_length=20,
		choices=Product.PRODUCT_TYPE_CHOICES,
		default='raw_material',
		verbose_name=_('نوع المنتج')
	)
	
	# نوع المادة الخام
	raw_material_type = models.CharField(
		max_length=20,
		choices=Product.RAW_MATERIAL_TYPE_CHOICES,
		blank=True,
		default='',
		verbose_name=_('نوع المادة الخام')
	)
	
	# الفئة الافتراضية
	category = models.ForeignKey(
		Category,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='product_templates',
		verbose_name=_('الفئة')
	)
	
	# وحدات القياس
	purchase_uom = models.CharField(
		max_length=10,
		choices=Product.UOM_CHOICES,
		default='unit',
		verbose_name=_('وحدة الشراء')
	)
	
	usage_uom = models.CharField(
		max_length=10,
		choices=Product.UOM_CHOICES,
		default='unit',
		verbose_name=_('وحدة الاستخدام')
	)
	
	conversion_factor = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		default=Decimal('1'),
		verbose_name=_('معامل التحويل'),
		help_text=_('عدد وحدات الاستخدام في وحدة الشراء')
	)
	
	# الحساب التلقائي للتحويل
	auto_calculate_conversion = models.BooleanField(
		default=False,
		verbose_name=_('حساب معامل التحويل تلقائياً')
	)
	
	# الأبعاد
	length = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		null=True,
		blank=True,
		verbose_name=_('الطول')
	)
	
	width = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		null=True,
		blank=True,
		verbose_name=_('العرض')
	)
	
	height = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		null=True,
		blank=True,
		verbose_name=_('الارتفاع/السُمك')
	)
	
	# المورد المفضل
	preferred_supplier = models.ForeignKey(
		'partners.Supplier',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='product_templates',
		verbose_name=_('المورد المفضل')
	)
	
	# معلومات إضافية
	min_stock = models.PositiveIntegerField(
		default=0,
		verbose_name=_('الحد الأدنى للمخزون')
	)
	
	is_active = models.BooleanField(
		default=True,
		verbose_name=_('نشط')
	)
	
	# معلومات التتبع
	created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
	updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='created_product_templates',
		verbose_name=_('أنشئ بواسطة')
	)
	
	# عدد المرات المستخدم فيها القالب
	usage_count = models.PositiveIntegerField(
		default=0,
		verbose_name=_('عدد الاستخدامات'),
		help_text=_('عدد المرات التي استخدم فيها هذا القالب')
	)
	
	class Meta:
		verbose_name = _('قالب منتج')
		verbose_name_plural = _('قوالب المنتجات')
		ordering = ['-usage_count', 'name']
		indexes = [
			models.Index(fields=['product_type']),
			models.Index(fields=['is_active']),
			models.Index(fields=['-usage_count']),
		]
	
	def __str__(self):
		return f"{self.name} ({self.get_product_type_display()})"
	
	def increment_usage(self):
		"""زيادة عداد الاستخدام"""
		self.usage_count += 1
		self.save(update_fields=['usage_count'])
	
	def to_product_dict(self):
		"""تحويل القالب إلى dictionary يمكن استخدامه لإنشاء منتج جديد"""
		return {
			'product_type': self.product_type,
			'raw_material_type': self.raw_material_type,
			'category': self.category,
			'purchase_uom': self.purchase_uom,
			'usage_uom': self.usage_uom,
			'conversion_factor': self.conversion_factor,
			'auto_calculate_conversion': self.auto_calculate_conversion,
			'length': self.length,
			'width': self.width,
			'height': self.height,
			'preferred_supplier': self.preferred_supplier,
			'min_stock': self.min_stock,
		}


class Location(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	WAREHOUSE_TYPES = [
		('finished', _('منتج تام')),
		('wip', _('نصف مصنع')),
		('raw', _('خامات')),
		('spare', _('قطع غيار')),
		('store', _('معرض/متجر')),
		('other', _('أخرى')),
	]
	# توافق مع الشفرة القديمة التي كانت تتوقع TYPE_CHOICES
	TYPE_CHOICES = WAREHOUSE_TYPES

	name = models.CharField(max_length=200)
	code = models.CharField(max_length=50, unique=True)
	address = models.CharField(max_length=255, blank=True)
	type = models.CharField(max_length=20, choices=WAREHOUSE_TYPES, default='other')
	is_active = models.BooleanField(default=True)
	is_default = models.BooleanField(
		default=False,
		help_text=_('الموقع الافتراضي لعمليات الإدخال/الإخراج في حال عدم اختيار موقع')
	)

	def save(self, *args, **kwargs):
		# تأكد من وجود موقع افتراضي واحد لكل معرض (أو واحد عالمي إذا بدون معرض)
		if self.is_default:
			Location.objects.exclude(pk=self.pk).update(is_default=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.code} - {self.name}"

	# --- Showroom compatibility accessors (the actual reverse name is showroom_link) ---
	@property
	def showroom(self):  # backward compatible attribute expected by existing code
		return getattr(self, 'showroom_link', None)

	@property
	def showroom_id(self):
		# إرجاع معرف المعرض لو مرتبط
		return getattr(self, 'showroom_link_id', None)

	min_stock = models.PositiveIntegerField(default=0)
	UOM_CHOICES = [
		('unit', _('وحدة')),
		('kg', _('كيلوجرام')),
		('g', _('جرام')),
		('m', _('متر')),
		('cm', _('سنتيمتر')),
	]
	purchase_uom = models.CharField(max_length=10, choices=UOM_CHOICES, default='unit')
	class Meta:
		indexes = [
			models.Index(fields=['name']),
		]
	
	@property
	def current_stock(self):
		"""إجمالي المخزون الحالي في جميع المواقع"""
		return self.stocks.aggregate(total=models.Sum('quantity'))['total'] or 0
	
	@property
	def is_low_stock(self):
		"""فحص إذا كان المخزون أقل من الحد الأدنى"""
		return self.current_stock <= self.min_stock
	
	@property
	def total_value(self):
		"""القيمة الإجمالية للمخزون (جمع الكميات * تكلفة المنتج).

		يدعم التخزين المؤقت والقيم المعيَّنة من الاستعلامات المعرّفة (annotate)
		عبر خاصية قابلة للكتابة لتفادي تعارض خاصية بدون محدِّد (no setter).
		"""
		from decimal import Decimal as _D
		cached = getattr(self, '_total_value_cached', None)
		if cached is not None:
			return cached
		total = _D('0')
		for s in self.stocks.select_related('product').all():
			total += _D(s.quantity) * (s.product.cost or _D('0'))
		return total

	@total_value.setter
	def total_value(self, value):
		# خزِّن القيمة كما هي (Decimal/float) بدون تحويل قسري
		setattr(self, '_total_value_cached', value)

	@total_value.deleter
	def total_value(self):
		if hasattr(self, '_total_value_cached'):
			delattr(self, '_total_value_cached')


class Stock(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	# NOTE: Product model is defined below (lightweight) to restore a corrupted removal.
	# If a fuller Product implementation is required, extend that class instead of adding
	# fields to Location. This prevents NameError during plugin/type analysis.
	product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='stocks')
	location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='stocks')
	quantity = models.IntegerField(default=0)

	class Meta:
		unique_together = ('product', 'location')
		indexes = [
			models.Index(fields=['product', 'location']),
			models.Index(fields=['location', 'product']),
			models.Index(fields=['quantity']),
		]
		constraints = [
			models.CheckConstraint(check=Q(quantity__gte=0), name='stock_quantity_nonnegative'),
		]

	def __str__(self):
		return f"{self.product} @ {self.location} = {self.quantity}"
	
	@property
	def total_value(self):
		"""Calculate total value of stock (quantity * cost)"""
		return self.quantity * self.product.cost


class StockTransfer(models.Model):
	"""تحويل مخزني بين موقعين"""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	STATUS_CHOICES = [
		('draft', _('مسودة')),
		('pending', _('قيد المراجعة')),
		('confirmed', _('مؤكد')),
	]

	number = models.CharField(max_length=50, unique=True)
	source = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='out_transfers')
	destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='in_transfers')
	date = models.DateField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ['-id']

	def __str__(self):
		return f"ST-{(self.pk or 0):06d} {self.source} -> {self.destination}"

	def save(self, *args, **kwargs):
		if not self.number:
			seq = next_sequence('STOCK_TRANSFER')
			self.number = format_code('ST', seq)
		super().save(*args, **kwargs)

	@property
	def is_editable(self):
		return self.status == 'draft'

	def confirm(self):
		"""Apply stock movements and mark as confirmed."""
		if self.status == 'confirmed':
			return
		for line in self.items.all():
			# reduce from source
			src_stock, created = Stock.objects.get_or_create(product=line.product, location=self.source)
			if src_stock.quantity < line.quantity:
				raise ValueError(_(
					'الكمية غير كافية للمنتج %(product)s في %(location)s'
				) % {'product': line.product, 'location': self.source})
			src_stock.quantity -= line.quantity
			src_stock.save()
			# add to destination
			dst_stock, created = Stock.objects.get_or_create(product=line.product, location=self.destination)
			dst_stock.quantity += line.quantity
			dst_stock.save()
		self.status = 'confirmed'
		self.save(update_fields=['status'])


class StockTransferItem(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField()

	def __str__(self):
		return f"{self.product} x {self.quantity}"

# =====================
# مخزون على مستوى الدُفعات (FIFO/LIFO)
# =====================

class StockBatch(models.Model):
	"""طبقة مخزون/دفعة لتتبع الكميات حسب تاريخ الاستلام والتكلفة والدفعات والمورد."""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='batches')
	location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='batches')
	lot_number = models.CharField(max_length=50, blank=True)
	expiry_date = models.DateField(null=True, blank=True)
	received_at = models.DateTimeField(auto_now_add=True)
	unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
	quantity = models.IntegerField(default=0)
	supplier = models.ForeignKey(
		'partners.Supplier',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='stock_batches',
		verbose_name=_('المورد'),
		help_text=_('المورد الذي تم الشراء منه')
	)

	# ربط الدفعة بالمورد لتتبع المخزون من كل مورد
	supplier = models.ForeignKey(
		'partners.Supplier',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='stock_batches',
		verbose_name=_('المورد'),
		help_text=_('المورد الذي تم استلام هذه الدفعة منه')
	)

	# مرجع مستند الاستلام
	receiving = models.ForeignKey(
		'inventory.Receiving',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='batches',
		verbose_name=_('مستند الاستلام')
	)

	class Meta:
		ordering = ['received_at', 'id']
		verbose_name = _('دفعة مخزون')
		verbose_name_plural = _('دفعات المخزون')
		indexes = [
			models.Index(fields=['product', 'location', 'received_at']),
			models.Index(fields=['location', 'product', 'quantity']),
			models.Index(fields=['quantity']),
			models.Index(fields=['supplier']),  # فهرس للبحث بالمورد
			models.Index(fields=['product', 'supplier']),  # للتقارير بالمورد
		]
		constraints = [
			models.CheckConstraint(check=Q(quantity__gte=0), name='stockbatch_quantity_nonnegative'),
		]

	def __str__(self):
		supplier_name = f" من {self.supplier.name}" if self.supplier else ""
		return f"Batch {self.lot_number or (self.pk or '')} - {self.product} @ {self.location} ({self.quantity}){supplier_name}"

	@property
	def total_value(self):
		"""القيمة الإجمالية للدفعة"""
		return Decimal(str(self.quantity)) * self.unit_cost

	@classmethod
	def get_stock_by_supplier(cls, product, location=None):
		"""الحصول على المخزون مجمع بالمورد"""
		from django.db.models import Sum
		qs = cls.objects.filter(product=product, quantity__gt=0)
		if location:
			qs = qs.filter(location=location)
		return qs.values('supplier', 'supplier__name').annotate(
			total_qty=Sum('quantity'),
			total_value=Sum(models.F('quantity') * models.F('unit_cost'))
		).order_by('supplier__name')


# =====================
# المستندات: استلام وصرف وجرد
# =====================

class Receiving(models.Model):
	"""مستند استلام من مورد (GRN)."""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	STATUS_CHOICES = [
		('draft', _('مسودة')),
		('confirmed', _('مؤكد')),
	]

	number = models.CharField(max_length=50, unique=True)
	supplier_name = models.CharField(max_length=255, blank=True)
	po_reference = models.CharField(max_length=100, blank=True, help_text=_('رقم أمر الشراء إن وجد'))
	# مرجع أمر الشراء (ID) بشكل اختياري لتفادي الاعتماد المتبادل في المهاجرات
	purchase_order_id = models.IntegerField(null=True, blank=True, help_text=_('معرّف أمر الشراء المرتبط (اختياري)'))
	location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='receivings')
	receive_date = models.DateField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	notes = models.TextField(blank=True)
	quality_checked = models.BooleanField(default=False)

	class Meta:
		ordering = ['-id']
		indexes = [
			models.Index(fields=['purchase_order_id']),
			models.Index(fields=['status']),
			models.Index(fields=['location', 'status']),
		]

	def __str__(self):
		return f"RCV-{(self.pk or 0):06d} {self.supplier_name}" if self.pk else "Receiving"

	def save(self, *args, **kwargs):
		if not self.number:
			seq = next_sequence('RECEIVING')
			self.number = format_code('RCV', seq)
		super().save(*args, **kwargs)

	@property
	def is_editable(self):
		return self.status == 'draft'

	def confirm(self):
		if self.status == 'confirmed':
			return
		if not self.quality_checked:
			raise ValueError(_('لا يمكن التأكيد قبل وضع علامة فحص الجودة'))
		# تحقق مطابقات أمر الشراء (كما السابق) مع تحسين بسيط
		if self.purchase_order_id:
			from django.db.models import Sum
			from django.apps import apps
			POItem = apps.get_model('purchases', 'PurchaseOrderItem')
			ordered_lookup = {
				(row['product_id'], row['location_id']): int(row['qty'] or 0)
				for row in (
					POItem.objects.filter(order_id=self.purchase_order_id)
					.values('product_id', 'location_id').annotate(qty=Sum('quantity'))
				)
			}
			prev_lookup = {
				(row['product_id'], row['receiving__location_id']): int(row['qty'] or 0)
				for row in (
					ReceivingItem.objects.filter(
						receiving__purchase_order_id=self.purchase_order_id,
						receiving__status='confirmed'
					)
					.values('product_id', 'receiving__location_id').annotate(qty=Sum('quantity'))
				)
			}
			for line in self.items.all():
				key = (line.product_id, self.location_id)
				ordered_qty = ordered_lookup.get(key)
				if ordered_qty is None:
					raise ValueError(_('المنتج %(product)s والموقع %(location)s غير موجودين في أمر الشراء المرتبط') % {'product': line.product, 'location': self.location})
				allowed = ordered_qty - prev_lookup.get(key, 0)
				if line.quantity > max(0, allowed):
					raise ValueError(_('الكمية %(qty)s تتجاوز المتبقي (%(allowed)s) للمنتج %(product)s وفقاً لأمر الشراء') % {'qty': line.quantity, 'allowed': max(0, allowed), 'product': line.product})
		from inventory.services.stock_moves import increase_stock
		for line in self.items.all():
			increase_stock(
				product=line.product,
				location=self.location,
				qty=line.quantity,
				unit_cost=line.unit_cost,
				lot_number=line.lot_number or '',
				expiry_date=line.expiry_date,
				reason='receiving_confirm',
				meta={'receiving_id': str(self.pk) if self.pk else ''}
			)
		self.status = 'confirmed'
		self.save(update_fields=['status'])




class ReceivingItem(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	receiving = models.ForeignKey(Receiving, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField()
	unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
	lot_number = models.CharField(max_length=50, blank=True)
	expiry_date = models.DateField(null=True, blank=True)

	def __str__(self):
		return f"{self.product} x {self.quantity}"

	class Meta:
		indexes = [
			models.Index(fields=['receiving', 'product']),
		]


class Issue(models.Model):
	"""مستند صرف إلى الإنتاج/البيع/أخرى."""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	STATUS_CHOICES = [
		('draft', _('مسودة')),
		('confirmed', _('مؤكد')),
	]
	ALLOCATION_CHOICES = [
		('fifo', 'FIFO'),
		('lifo', 'LIFO'),
	]

	number = models.CharField(max_length=50, unique=True)
	location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='issues')
	issue_date = models.DateField(auto_now_add=True)
	to_department = models.CharField(max_length=50, default='production', help_text=_('مثلاً: production, sales, other'))
	reference = models.CharField(max_length=100, blank=True, help_text=_('مرجع الطلب/أمر التشغيل'))
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	allocation_method = models.CharField(max_length=10, choices=ALLOCATION_CHOICES, default='fifo')
	notes = models.TextField(blank=True)
	# Tracking fields: who issued and who received
	issued_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='inventory_issues_issued',
		verbose_name=_('المُصدر')
	)
	received_by_name = models.CharField(
		max_length=255,
		blank=True,
		null=True,
		verbose_name=_('اسم المستلم')
	)

	class Meta:
		ordering = ['-id']
		indexes = [
			models.Index(fields=['status']),
			models.Index(fields=['location', 'status']),
			models.Index(fields=['allocation_method', 'status']),
		]

	def __str__(self):
		return f"ISS-{(self.pk or 0):06d} {self.to_department}" if self.pk else "Issue"

	def save(self, *args, **kwargs):
		if not self.number:
			seq = next_sequence('ISSUE')
			self.number = format_code('ISS', seq)
		super().save(*args, **kwargs)

	@property
	def is_editable(self):
		return self.status == 'draft'

	def _pick_batches(self, product, required_qty):
		"""اختيار الدُفعات حسب طريقة التخصيص (FIFO/LIFO). يرجع قائمة (batch, qty)."""
		if self.allocation_method == 'lifo':
			qs = StockBatch.objects.filter(product=product, location=self.location, quantity__gt=0).order_by('-received_at', '-id')
		else:
			qs = StockBatch.objects.filter(product=product, location=self.location, quantity__gt=0).order_by('received_at', 'id')
		picked = []
		remain = int(required_qty)
		for b in qs:
			if remain <= 0:
				break
			take = min(b.quantity, remain)
			picked.append((b, take))
			remain -= take
		if remain > 0:
			raise ValueError(_('الكمية غير كافية للمنتج %(product)s') % {'product': product})
		return picked

	def confirm(self):
		if self.status == 'confirmed':
			return
		# تحقق الأرصدة أولاً
		for line in self.items.all():
			stock = Stock.objects.filter(product=line.product, location=self.location).first()
			if not stock or stock.quantity < line.quantity:
				raise ValueError(_(
					'لا يوجد رصيد كافٍ للمنتج %(product)s في %(location)s'
				) % {'product': line.product, 'location': self.location})
		# خصم من الدُفعات وترحيل
		for line in self.items.all():
			picked = self._pick_batches(line.product, line.quantity)
			qty_to_deduct = line.quantity
			for batch, take in picked:
				batch.quantity -= take
				batch.save(update_fields=['quantity'])
			stock = Stock.objects.get(product=line.product, location=self.location)
			stock.quantity -= qty_to_deduct
			stock.save(update_fields=['quantity'])
		self.status = 'confirmed'
		self.save(update_fields=['status'])




class IssueItem(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField()

	def __str__(self):
		return f"{self.product} x {self.quantity}"

	class Meta:
		indexes = [
			models.Index(fields=['issue', 'product']),
		]


# =====================
# طلب خامات للإنتاج (Material Requisition)
# =====================

class Requisition(models.Model):
	"""مستند طلب خامات من قسم الإنتاج إلى المخازن.

	لا يحرّك المخزون. يُستخدم للموافقة ثم التحويل إلى إذن صرف.
	"""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	STATUS_CHOICES = [
		('draft', _('مسودة')),
		('submitted', _('مقدّم')),
		('approved', _('موافق عليه')),
		('converted', _('تم التحويل لصرف')),
		('cancelled', _('ملغى')),
	]

	number = models.CharField(max_length=50, unique=True)
	request_date = models.DateField(auto_now_add=True)
	from_department = models.CharField(max_length=50, default='production', help_text=_('القسم الطالب (غالباً الإنتاج)'))
	reference = models.CharField(max_length=100, blank=True, help_text=_('مرجع اختياري مثل رقم أمر الإنتاج'))
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	notes = models.TextField(blank=True)

	requested_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='material_requisitions_requested',
		verbose_name=_('مقدّم الطلب')
	)
	approved_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='material_requisitions_approved',
		verbose_name=_('الموافق')
	)
	approved_at = models.DateTimeField(null=True, blank=True)
	linked_issue_id = models.IntegerField(null=True, blank=True, help_text=_('رقم مستند الصرف الناتج (اختياري)'))

	class Meta:
		ordering = ['-id']
		indexes = [
			models.Index(fields=['status']),
		]

	def __str__(self):
		return f"REQ-{(self.pk or 0):06d} {self.from_department}" if self.pk else "Requisition"

	def save(self, *args, **kwargs):
		if not self.number:
			from django.db import IntegrityError
			max_attempts = 10
			for attempt in range(max_attempts):
				try:
					seq = next_sequence('REQUISITION')
					self.number = format_code('REQ', seq)
					super().save(*args, **kwargs)
					break
				except IntegrityError:
					if attempt == max_attempts - 1:
						# آخر محاولة: استخدم timestamp لضمان التفرد
						import time
						seq = next_sequence('REQUISITION')
						self.number = f"{format_code('REQ', seq)}-{int(time.time())}"
						super().save(*args, **kwargs)
					continue
		else:
			super().save(*args, **kwargs)

	@property
	def is_editable(self):
		return self.status in ('draft', 'submitted')


class RequisitionItem(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField()
	production_order_id = models.IntegerField(null=True, blank=True, help_text=_('معرّف أمر الإنتاج المرتبط (اختياري)'))
	stage_id = models.IntegerField(null=True, blank=True, help_text=_('مرحلة الأمر (اختياري)'))

	def __str__(self):
		return f"{self.product} x {self.quantity}"

	class Meta:
		indexes = [
			models.Index(fields=['requisition', 'product']),
		]


class StockCount(models.Model):
	"""جلسة جرد مخزون لموقع معين."""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	STATUS_CHOICES = [
		('draft', _('مسودة')),
		('counted', _('تم العد')),
		('applied', _('مُرحّل')),
	]

	number = models.CharField(max_length=50, unique=True)
	location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='stock_counts')
	count_date = models.DateField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ['-id']

	def __str__(self):
		return f"CNT-{(self.pk or 0):06d} {self.location}" if self.pk else "StockCount"

	def save(self, *args, **kwargs):
		if not self.number:
			seq = next_sequence('STOCK_COUNT')
			self.number = format_code('CNT', seq)
		super().save(*args, **kwargs)

	@property
	def is_editable(self):
		return self.status in ('draft', 'counted')

	def apply(self):
		"""ترحيل فروقات الجرد على الأرصدة والدُفعات (تعديل مباشر على Stock، وتحديث/إنشاء دفعة واحدة للفائض)."""
		if self.status == 'applied':
			return
		for line in self.items.all():
			stock, _ = Stock.objects.get_or_create(product=line.product, location=self.location)
			# created flag not used; only to avoid shadowing translation function
			diff = int(line.counted_qty) - int(line.system_qty)
			if diff == 0:
				continue
			stock.quantity += diff
			stock.save(update_fields=['quantity'])
			if diff > 0:
				# إنشاء دفعة جديدة للفائض بدون تفاصيل دفعة
				StockBatch.objects.create(
					product=line.product,
					location=self.location,
					lot_number='COUNT',
					unit_cost=line.product.cost,
					quantity=diff,
				)
			else:
				# خصم من الدُفعات FIFO
				remain = -diff
				qs = StockBatch.objects.filter(product=line.product, location=self.location, quantity__gt=0).order_by('received_at', 'id')
				for b in qs:
					if remain <= 0:
						break
					take = min(b.quantity, remain)
					b.quantity -= take
					b.save(update_fields=['quantity'])
					remain -= take
		self.status = 'applied'
		self.save(update_fields=['status'])




class StockCountItem(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	stock_count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
	system_qty = models.IntegerField(default=0)
	counted_qty = models.IntegerField(default=0)

	def __str__(self):
		return f"{self.product} sys:{self.system_qty} cnt:{self.counted_qty}"


# =====================
# أحداث مخزون منخفض (للاحتفاظ بآخر تنبيه لكل منتج)
# =====================
class LowStockEvent(models.Model):
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	product = models.OneToOneField('inventory.Product', on_delete=models.CASCADE, related_name='low_stock_event')
	last_notified_at = models.DateTimeField(auto_now=True)
	last_quantity = models.IntegerField(default=0)
	threshold = models.IntegerField(default=0)
	notification_count = models.PositiveIntegerField(default=0)

	def __str__(self):  # pragma: no cover - simple representation
		return f"LowStockEvent({self.product_id}) qty={self.last_quantity} th={self.threshold} count={self.notification_count}"

	class Meta:
		indexes = [
			models.Index(fields=['last_notified_at']),
		]
		verbose_name = 'Low Stock Event'
		verbose_name_plural = 'Low Stock Events'


# =====================
# إعدادات الطابعات (لدعم Zebra, xprinter, HP)
# =====================
class PrinterConfiguration(models.Model):
	"""
	تكوين الطابعات المختلفة لطباعة الفواتير والايصالات والباركود
	"""
	PRINTER_TYPES = [
		('zebra', _('Zebra (باركود)')),
		('xprinter', _('Xprinter (حراري)')),
		('hp_laserjet', _('HP LaserJet')),
		('generic', _('طابعة عامة')),
	]
	
	DOCUMENT_TYPES = [
		('barcode', _('باركود')),
		('invoice', _('فاتورة')),
		('receipt', _('إيصال')),
		('report', _('تقرير')),
		('id_card', _('بطاقة هوية')),
		('label', _('ليبل')),
	]
	
	CONNECTION_TYPES = [
		('network', _('شبكة (IP)')),
		('usb', _('USB')),
		('shared', _('مشاركة ويندوز')),
	]
	
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=100, verbose_name=_("اسم الطابعة"))
	printer_type = models.CharField(max_length=20, choices=PRINTER_TYPES, verbose_name=_("نوع الطابعة"))
	document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, verbose_name=_("نوع المستند"))
	connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='network', verbose_name=_("نوع الاتصال"))
	
	# إعدادات الاتصال
	ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("عنوان IP"))
	port = models.PositiveIntegerField(default=9100, null=True, blank=True, verbose_name=_("المنفذ"))
	usb_device_path = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("مسار USB"))
	shared_printer_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("اسم الطابعة المشاركة"))
	
	# إعدادات الطباعة
	paper_size = models.CharField(max_length=20, default='80mm', verbose_name=_("حجم الورق"))
	dpi = models.PositiveIntegerField(default=203, verbose_name=_("DPI"))
	label_width_mm = models.PositiveIntegerField(default=100, null=True, blank=True, verbose_name=_("عرض الليبل (مم)"))
	label_height_mm = models.PositiveIntegerField(default=100, null=True, blank=True, verbose_name=_("طول الليبل (مم)"))
	
	is_default = models.BooleanField(default=False, verbose_name=_("افتراضية"))
	is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))
	
	# إحصائيات
	total_prints = models.PositiveIntegerField(default=0, verbose_name=_("عدد المطبوعات"))
	last_print_at = models.DateTimeField(null=True, blank=True, verbose_name=_("آخر طباعة"))
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = _("طابعة")
		verbose_name_plural = _("الطابعات")
		unique_together = [['document_type', 'is_default']]
		indexes = [
			models.Index(fields=['printer_type', 'is_active']),
			models.Index(fields=['document_type', 'is_default']),
		]
	
	def __str__(self):
		return f"{self.name} ({self.get_printer_type_display()})"
	
	def save(self, *args, **kwargs):
		# إذا كانت افتراضية، إلغاء الافتراضية من الطابعات الأخرى لنفس نوع المستند
		if self.is_default:
			PrinterConfiguration.objects.filter(
				document_type=self.document_type,
				is_default=True
			).exclude(id=self.id).update(is_default=False)
		super().save(*args, **kwargs)
	
	def increment_print_count(self):
		"""زيادة عداد المطبوعات"""
		from django.utils import timezone
		self.total_prints += 1
		self.last_print_at = timezone.now()
		self.save(update_fields=['total_prints', 'last_print_at'])

class ProductUnit(models.Model):
	"""
	وحدة منتج فردية - تتبع كل منتج من الإنتاج للبيع للضمان
	كل منتج يُصنع له Serial Number وBarcode وQR Code فريد
	"""
	
	STATUS_CHOICES = [
		('produced', _('تم الإنتاج')),
		('in_stock', _('في المخزن')),
		('sold_to_dealer', _('مباع لتاجر')),
		('sold_to_customer', _('مباع لعميل')),
		('warranty_registered', _('ضمان مسجل')),
		('warranty_claimed', _('مطالبة ضمان')),
		('returned', _('مرتجع')),
		('defective', _('معيب')),
		('scrapped', _('خردة')),
	]
	
	id = models.AutoField(primary_key=True)
	
	# الكود الفريد
	serial_number = models.CharField(
		max_length=50, 
		unique=True, 
		verbose_name=_('الرقم التسلسلي'),
		help_text=_('رقم فريد لكل وحدة منتج')
	)
	barcode = models.CharField(
		max_length=50, 
		unique=True, 
		blank=True,
		verbose_name=_('الباركود'),
		help_text=_('باركود فريد للمسح')
	)
	qr_code_data = models.CharField(
		max_length=255,
		unique=True,
		blank=True,
		verbose_name=_('بيانات QR Code'),
		help_text=_('البيانات المشفرة في QR Code')
	)
	qr_code_image = models.ImageField(
		upload_to='product_units/qr/',
		blank=True,
		null=True,
		verbose_name=_('صورة QR Code')
	)
	
	# ربط المنتج
	product = models.ForeignKey(
		Product,
		on_delete=models.CASCADE,
		related_name='units',
		verbose_name=_('المنتج')
	)
	
	# الحالة
	status = models.CharField(
		max_length=20,
		choices=STATUS_CHOICES,
		default='produced',
		verbose_name=_('الحالة')
	)
	
	# معلومات الإنتاج
	production_order = models.ForeignKey(
		'production.ProductionOrder',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='produced_units',
		verbose_name=_('أمر الإنتاج')
	)
	production_date = models.DateField(
		auto_now_add=True,
		verbose_name=_('تاريخ الإنتاج')
	)
	production_batch = models.CharField(
		max_length=50,
		blank=True,
		verbose_name=_('رقم الدفعة')
	)
	
	# معلومات البيع للتاجر
	dealer = models.ForeignKey(
		'partners.Partner',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='purchased_units',
		verbose_name=_('التاجر/الموزع')
	)
	dealer_invoice = models.ForeignKey(
		'sales.Invoice',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='dealer_units',
		verbose_name=_('فاتورة التاجر')
	)
	dealer_sale_date = models.DateField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ البيع للتاجر')
	)
	dealer_sale_price = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('سعر البيع للتاجر')
	)
	
	# معلومات البيع للعميل النهائي
	customer_name = models.CharField(
		max_length=200,
		blank=True,
		verbose_name=_('اسم العميل')
	)
	customer_phone = models.CharField(
		max_length=20,
		blank=True,
		verbose_name=_('هاتف العميل')
	)
	customer_email = models.EmailField(
		blank=True,
		verbose_name=_('بريد العميل')
	)
	customer_address = models.TextField(
		blank=True,
		verbose_name=_('عنوان العميل')
	)
	customer_national_id = models.CharField(
		max_length=20,
		blank=True,
		verbose_name=_('رقم الهوية')
	)
	customer_sale_date = models.DateField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ البيع للعميل')
	)
	customer_sale_price = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		null=True,
		blank=True,
		verbose_name=_('سعر البيع للعميل')
	)
	customer_invoice_image = models.ImageField(
		upload_to='product_units/invoices/',
		blank=True,
		null=True,
		verbose_name=_('صورة فاتورة العميل')
	)
	
	# معلومات الضمان
	warranty_policy = models.ForeignKey(
		'ecommerce.ProductWarranty',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		verbose_name=_('سياسة الضمان')
	)
	warranty_start_date = models.DateField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ بداية الضمان')
	)
	warranty_end_date = models.DateField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ نهاية الضمان')
	)
	warranty_registered = models.BooleanField(
		default=False,
		verbose_name=_('تم تسجيل الضمان')
	)
	warranty_registration_date = models.DateTimeField(
		null=True,
		blank=True,
		verbose_name=_('تاريخ تسجيل الضمان')
	)
	
	# معلومات إضافية
	notes = models.TextField(
		blank=True,
		verbose_name=_('ملاحظات')
	)
	
	# التتبع
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		verbose_name=_('أنشئ بواسطة')
	)
	
	class Meta:
		verbose_name = _('وحدة منتج')
		verbose_name_plural = _('وحدات المنتجات')
		ordering = ['-production_date', '-id']
		indexes = [
			models.Index(fields=['serial_number']),
			models.Index(fields=['barcode']),
			models.Index(fields=['status']),
			models.Index(fields=['production_date']),
			models.Index(fields=['customer_phone']),
		]
	
	def __str__(self):
		return f"{self.product.name} - {self.serial_number}"
	
	def save(self, *args, **kwargs):
		# توليد الباركود والـ QR Code تلقائياً
		if not self.serial_number:
			self.serial_number = self.generate_serial_number()
		if not self.barcode:
			self.barcode = self.generate_barcode()
		if not self.qr_code_data:
			self.qr_code_data = self.generate_qr_data()
		
		# توليد صورة QR Code
		if self.qr_code_data and not self.qr_code_image:
			self.generate_qr_image()
		
		super().save(*args, **kwargs)
	
	def generate_serial_number(self):
		"""توليد رقم تسلسلي فريد"""
		import uuid
		from datetime import datetime
		
		# تنسيق: SN-YYYYMMDD-XXXXX
		date_part = datetime.now().strftime('%Y%m%d')
		unique_part = str(uuid.uuid4().int)[:6]
		product_code = self.product.sku[:4] if self.product else 'XXXX'
		
		serial = f"SN-{product_code}-{date_part}-{unique_part}"
		
		# التأكد من عدم التكرار
		counter = 1
		original_serial = serial
		while ProductUnit.objects.filter(serial_number=serial).exists():
			serial = f"{original_serial}-{counter}"
			counter += 1
		
		return serial
	
	def generate_barcode(self):
		"""توليد باركود فريد (EAN-13 style)"""
		import random
		from datetime import datetime
		
		# تنسيق: 628 (كود البلد) + 4 أرقام للمنتج + 5 أرقام للوحدة + 1 check digit
		country_code = "628"  # مصر
		product_part = str(self.product.id if self.product else 0).zfill(4)[-4:]
		
		# توليد 5 أرقام عشوائية
		random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
		
		barcode = f"{country_code}{product_part}{random_part}"
		
		# حساب check digit للـ EAN-13
		def calculate_check_digit(code):
			total = 0
			for i, digit in enumerate(code):
				if i % 2 == 0:
					total += int(digit)
				else:
					total += int(digit) * 3
			check_digit = (10 - (total % 10)) % 10
			return str(check_digit)
		
		barcode += calculate_check_digit(barcode)
		
		# التأكد من عدم التكرار
		counter = 1
		original_barcode = barcode
		while ProductUnit.objects.filter(barcode=barcode).exists():
			random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
			barcode = f"{country_code}{product_part}{random_part}"
			barcode += calculate_check_digit(barcode)
			counter += 1
			if counter > 100:
				# fallback إلى UUID
				barcode = str(uuid.uuid4().int)[:13]
				break
		
		return barcode
	
	def generate_qr_data(self):
		"""توليد بيانات QR Code"""
		import json
		from datetime import datetime
		
		data = {
			'sn': self.serial_number,
			'bc': self.barcode,
			'pid': self.product.id if self.product else None,
			'pn': self.product.name if self.product else '',
			'pd': self.production_date.isoformat() if self.production_date else datetime.now().date().isoformat(),
			'url': f'/warranty/verify/{self.serial_number}/'
		}
		
		return json.dumps(data, ensure_ascii=False)
	
	def generate_qr_image(self):
		"""توليد صورة QR Code"""
		try:
			import qrcode
			from io import BytesIO
			from django.core.files.base import ContentFile
			
			qr = qrcode.QRCode(
				version=1,
				error_correction=qrcode.constants.ERROR_CORRECT_M,
				box_size=10,
				border=4,
			)
			qr.add_data(self.qr_code_data)
			qr.make(fit=True)
			
			img = qr.make_image(fill_color="black", back_color="white")
			
			buffer = BytesIO()
			img.save(buffer, "PNG")  # type: ignore[call-arg]
			buffer.seek(0)
			
			filename = f"qr_{self.serial_number}.png"
			self.qr_code_image.save(filename, ContentFile(buffer.read()), save=False)
		except Exception as e:
			print(f"Error generating QR image: {e}")
	
	def activate_warranty(self, customer_data=None):
		"""تفعيل الضمان للعميل"""
		from django.utils import timezone
		from dateutil.relativedelta import relativedelta
		
		if customer_data:
			self.customer_name = customer_data.get('name', '')
			self.customer_phone = customer_data.get('phone', '')
			self.customer_email = customer_data.get('email', '')
			self.customer_address = customer_data.get('address', '')
			self.customer_national_id = customer_data.get('national_id', '')
		
		# تحديد فترة الضمان
		if self.warranty_policy:
			warranty_months = self.warranty_policy.duration_months
		else:
			warranty_months = 12  # افتراضي سنة
		
		today = timezone.now().date()
		
		# تاريخ بداية الضمان من تاريخ البيع أو اليوم
		if self.customer_sale_date:
			self.warranty_start_date = self.customer_sale_date
		else:
			self.warranty_start_date = today
			self.customer_sale_date = today
		
		self.warranty_end_date = self.warranty_start_date + relativedelta(months=warranty_months)
		self.warranty_registered = True
		self.warranty_registration_date = timezone.now()
		self.status = 'warranty_registered'
		
		self.save()
		
		return True
	
	@property
	def is_warranty_valid(self):
		"""هل الضمان ساري؟"""
		if not self.warranty_registered or not self.warranty_end_date:
			return False
		from django.utils import timezone
		return timezone.now().date() <= self.warranty_end_date
	
	@property
	def warranty_remaining_days(self):
		"""الأيام المتبقية من الضمان"""
		if not self.warranty_end_date:
			return 0
		from django.utils import timezone
		remaining = (self.warranty_end_date - timezone.now().date()).days
		return max(0, remaining)
	
	@classmethod
	def create_units_from_production(cls, production_order, quantity, created_by=None):
		"""إنشاء وحدات منتج من أمر إنتاج"""
		units = []
		for i in range(int(quantity)):
			unit = cls(
				product=production_order.product,
				production_order=production_order,
				production_batch=production_order.number,
				status='produced',
				created_by=created_by
			)
			unit.save()
			units.append(unit)
		return units


class SupplierProductPrice(models.Model):
	"""أسعار المواد الخام حسب المورد - يمكن ربطها بمنتج موجود أو إدخالها كمسمى نصي فقط"""
	id = models.AutoField(primary_key=True)

	# اسم المادة كنص حر (الأساسي) - لا حاجة لربط بمنتج
	material_name = models.CharField(
		max_length=200,
		blank=True,
		default='',
		verbose_name=_('اسم المادة الخام'),
		help_text=_('اسم المادة كما تعرفها أنت — مثال: اسفنج كثافة 26')
	)

	# ربط اختياري بمنتج موجود في المخزون
	product = models.ForeignKey(
		Product,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='supplier_prices',
		verbose_name=_('المنتج (اختياري)'),
		help_text=_('اربط بمنتج موجود في المخزون إن أردت — اختياري تماماً')
	)
	supplier = models.ForeignKey(
		'partners.Supplier',
		on_delete=models.CASCADE,
		related_name='product_prices',
		verbose_name=_('المورد')
	)

	# السعر والعملة
	cost = models.DecimalField(
		max_digits=12,
		decimal_places=2,
		verbose_name=_('التكلفة'),
		help_text=_('تكلفة وحدة الشراء من هذا المورد')
	)
	currency = models.CharField(
		max_length=3,
		default='EGP',
		verbose_name=_('العملة')
	)

	# وحدة الشراء من المورد
	UOM_CHOICES = Product.UOM_CHOICES  # نفس خيارات الوحدات من نموذج المنتج
	purchase_unit = models.CharField(
		max_length=10,
		choices=UOM_CHOICES,
		default='unit',
		verbose_name=_('وحدة الشراء'),
		help_text=_('الوحدة التي يبيع بها المورد هذه المادة')
	)
	conversion_to_base = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		default=1,
		verbose_name=_('معامل التحويل'),
		help_text=_('عدد الوحدات الأساسية في وحدة شراء واحدة من المورد')
	)

	# شروط الشراء
	min_order_qty = models.DecimalField(
		max_digits=12,
		decimal_places=4,
		null=True,
		blank=True,
		verbose_name=_('الحد الأدنى للطلب'),
		help_text=_('أقل كمية يمكن طلبها من هذا المورد')
	)
	lead_time_days = models.PositiveIntegerField(
		null=True,
		blank=True,
		verbose_name=_('مدة التوريد (أيام)'),
		help_text=_('المدة المتوقعة للتوريد بالأيام')
	)

	# الحالة والتواريخ
	is_active = models.BooleanField(
		default=True,
		verbose_name=_('نشط')
	)
	effective_date = models.DateField(
		auto_now_add=True,
		verbose_name=_('تاريخ السريان')
	)
	notes = models.TextField(
		blank=True,
		verbose_name=_('ملاحظات')
	)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _('سعر مورد')
		verbose_name_plural = _('أسعار الموردين')
		ordering = ['product', 'supplier', '-effective_date']
		unique_together = [('product', 'supplier', 'effective_date')]
		indexes = [
			models.Index(fields=['product', 'supplier', 'is_active']),
			models.Index(fields=['effective_date']),
		]

	def __str__(self):
		name = self.product.name if self.product else self.material_name
		return f"{name} - {self.supplier.name}: {self.cost} {self.currency}"

	@property
	def is_preferred(self):
		"""هل هذا المورد هو المورد المفضل للمنتج؟"""
		if not self.product:
			return False
		return self.product.preferred_supplier_id == self.supplier_id

	def save(self, *args, **kwargs):
		"""حفظ سعر المورد - التحديثات المرتبطة تتم عبر post_save signal"""
		super().save(*args, **kwargs)

	def propagate_price_to_bom(self):
		"""تحديث تكلفة الوحدة في جميع عناصر BOM التي تستخدم هذه المادة الخام"""
		if not self.product:
			return
		try:
			from production.models import BOMItem
			product = self.product

			# تحديث unit_cost في كل BOMItem يستخدم هذه المادة
			bom_items = BOMItem.objects.filter(material=product)
			updated_count = 0
			for item in bom_items:
				# تكلفة الوحدة = سعر الشراء (بوحدة الشراء)
				# الكمية في BOM تكون بوحدة الاستخدام
				item.unit_cost = product.usage_unit_cost or product.cost
				item.save(update_fields=['unit_cost'])
				updated_count += 1

			# إعادة حساب إجمالي تكلفة المواد في كل BOM متأثر
			if updated_count > 0:
				from production.models import BillOfMaterials
				affected_boms = BillOfMaterials.objects.filter(
					items__material=product
				).distinct()
				for bom in affected_boms:
					total_material_cost = sum(
						item.total_cost for item in bom.items.all()
					)
					bom.total_material_cost = total_material_cost
					bom.save(update_fields=['total_material_cost'])

		except Exception:
			pass  # لا نريد أن يفشل الحفظ بسبب خطأ في التحديث

	def propagate_price_to_packaging(self):
		"""تحديث أسعار وحدات التعبئة المرتبطة بهذه المادة"""
		try:
			packaging_units = PackagingUnit.objects.filter(
				product=self.product,
				is_active=True
			)
			for pkg in packaging_units:
				pkg.calculated_price = pkg.calculate_price()
				pkg.save(update_fields=['calculated_price'])
		except Exception:
			pass


# تسجيل نماذج إضافية (تاريخ الأسعار والإشعارات)
# يتم تعريفها في ملفات منفصلة لضمان تنظيم الكود
from .price_history import MaterialPriceHistory, ProductCostHistory, PriceChangeImpact  # noqa: E402,F401
from .notifications import PriceChangeNotification, NotificationPreference  # noqa: E402,F401
from .conversion_factors import ConversionFactor  # noqa: E402,F401
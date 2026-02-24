# 📊 04 - نماذج البيانات (629 موديل)

## 📋 نظرة عامة

النظام يحتوي على **629 موديل** موزعة على **79 تطبيق**. هذا الملف يوثق أهم الموديلات وعلاقاتها.

---

## 🏛️ الموديلات الأساسية (Core Models)

### نموذج الشريك التجاري (Partner)
```
┌─────────────────────────────────────────────────────┐
│                     Partner                          │
├─────────────────────────────────────────────────────┤
│ id (PK)                                              │
│ name                                                 │
│ type (customer/supplier/both)                        │
│ tax_number                                           │
│ email                                                │
│ phone                                                │
│ address                                              │
│ credit_limit                                         │
│ balance                                              │
│ created_at                                           │
│ updated_at                                           │
└─────────────────────────────────────────────────────┘
         │
         ├──── Customer (extends Partner)
         │        └── loyalty_points
         │        └── customer_type_id (FK)
         │
         └──── Supplier (extends Partner)
                  └── payment_terms
                  └── supplier_documents[]
```

---

## 📦 موديلات المخزون (Inventory)

### Category - الفئات
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| name | CharField | اسم الفئة |
| parent | ForeignKey(self) | الفئة الأب |
| description | TextField | الوصف |

### Product - المنتجات
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| name | CharField | اسم المنتج |
| sku | CharField | رمز المنتج |
| barcode | CharField | الباركود |
| category | ForeignKey | الفئة |
| unit | CharField | الوحدة |
| cost_price | DecimalField | سعر التكلفة |
| sale_price | DecimalField | سعر البيع |
| tax_rate | DecimalField | نسبة الضريبة |
| min_stock | IntegerField | الحد الأدنى |
| max_stock | IntegerField | الحد الأقصى |
| is_active | BooleanField | نشط |

### Stock - المخزون
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| product | ForeignKey | المنتج |
| location | ForeignKey | الموقع |
| quantity | DecimalField | الكمية |
| reserved | DecimalField | المحجوز |
| batch | ForeignKey | الدفعة |

### علاقات المخزون
```
Product ─────┬───── Stock (many)
             │        └── Location
             │        └── StockBatch
             │
             ├───── StockTransferItem (many)
             │        └── StockTransfer
             │
             └───── ReceivingItem (many)
                      └── Receiving
```

---

## 💰 موديلات المبيعات (Sales)

### Invoice - الفاتورة
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| invoice_number | CharField | رقم الفاتورة |
| customer | ForeignKey | العميل |
| date | DateField | التاريخ |
| due_date | DateField | تاريخ الاستحقاق |
| subtotal | DecimalField | المجموع الفرعي |
| tax_amount | DecimalField | مبلغ الضريبة |
| discount | DecimalField | الخصم |
| total | DecimalField | الإجمالي |
| paid | DecimalField | المدفوع |
| status | CharField | الحالة |
| branch | ForeignKey | الفرع |
| salesperson | ForeignKey | البائع |

### InvoiceItem - بند الفاتورة
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| invoice | ForeignKey | الفاتورة |
| product | ForeignKey | المنتج |
| quantity | DecimalField | الكمية |
| unit_price | DecimalField | سعر الوحدة |
| discount | DecimalField | الخصم |
| tax | DecimalField | الضريبة |
| total | DecimalField | الإجمالي |

### SaleOrder - أمر البيع
```
SaleOrder (extends Invoice)
    │
    ├── status (draft/confirmed/delivered/invoiced)
    ├── delivery_date
    └── SaleOrderItem[] (extends InvoiceItem)
```

---

## 🛒 موديلات المشتريات (Purchases)

### PurchaseBill - فاتورة المشتريات
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| bill_number | CharField | رقم الفاتورة |
| supplier | ForeignKey | المورد |
| date | DateField | التاريخ |
| total | DecimalField | الإجمالي |
| status | CharField | الحالة |

### PurchaseOrder - أمر الشراء
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| order_number | CharField | رقم الأمر |
| supplier | ForeignKey | المورد |
| expected_date | DateField | تاريخ التوريد المتوقع |
| status | CharField | الحالة |
| approved_by | ForeignKey | الموافق |

---

## 📒 موديلات المحاسبة (Accounting)

### Account - الحساب
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| code | CharField | رمز الحساب |
| name | CharField | اسم الحساب |
| account_type | CharField | نوع الحساب |
| parent | ForeignKey(self) | الحساب الأب |
| balance | DecimalField | الرصيد |
| is_active | BooleanField | نشط |

### أنواع الحسابات
```python
class AccountType(TextChoices):
    ASSET = 'asset', 'أصول'
    LIABILITY = 'liability', 'خصوم'
    EQUITY = 'equity', 'حقوق ملكية'
    REVENUE = 'revenue', 'إيرادات'
    EXPENSE = 'expense', 'مصروفات'
```

### JournalEntry - القيد اليومي
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| entry_number | CharField | رقم القيد |
| date | DateField | التاريخ |
| description | TextField | البيان |
| total_debit | DecimalField | إجمالي المدين |
| total_credit | DecimalField | إجمالي الدائن |
| is_posted | BooleanField | مرحّل |
| fiscal_year | ForeignKey | السنة المالية |

### JournalEntryItem - بند القيد
| الحقل | النوع | الوصف |
|-------|-------|-------|
| entry | ForeignKey | القيد |
| account | ForeignKey | الحساب |
| debit | DecimalField | مدين |
| credit | DecimalField | دائن |
| cost_center | ForeignKey | مركز التكلفة |

---

## 👥 موديلات الموارد البشرية (HR)

### Employee - الموظف
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| employee_id | CharField | رقم الموظف |
| user | OneToOneField | المستخدم |
| first_name | CharField | الاسم الأول |
| last_name | CharField | الاسم الأخير |
| department | ForeignKey | القسم |
| position | ForeignKey | المنصب |
| hire_date | DateField | تاريخ التعيين |
| salary | DecimalField | الراتب |
| manager | ForeignKey(self) | المدير |
| is_active | BooleanField | نشط |

### Department - القسم
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| name | CharField | اسم القسم |
| parent | ForeignKey(self) | القسم الأب |
| manager | ForeignKey | مدير القسم |

### AttendanceRecord - سجل الحضور
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| employee | ForeignKey | الموظف |
| date | DateField | التاريخ |
| check_in | TimeField | وقت الحضور |
| check_out | TimeField | وقت الانصراف |
| status | CharField | الحالة |

---

## 🏪 موديلات نقاط البيع (POS)

### POSSession - جلسة البيع
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| user | ForeignKey | المستخدم |
| branch | ForeignKey | الفرع |
| opening_balance | DecimalField | رصيد الافتتاح |
| closing_balance | DecimalField | رصيد الإغلاق |
| opened_at | DateTimeField | وقت الفتح |
| closed_at | DateTimeField | وقت الإغلاق |
| status | CharField | الحالة |

### POSOrder - طلب POS
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| session | ForeignKey | الجلسة |
| customer | ForeignKey | العميل |
| total | DecimalField | الإجمالي |
| table | ForeignKey | الطاولة |
| status | CharField | الحالة |
| created_at | DateTimeField | وقت الإنشاء |

---

## 🏭 موديلات الإنتاج (Production)

### BillOfMaterials - قائمة المواد
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| product | ForeignKey | المنتج النهائي |
| name | CharField | الاسم |
| quantity | DecimalField | الكمية |
| is_active | BooleanField | نشط |

### BOMItem - مكون القائمة
| الحقل | النوع | الوصف |
|-------|-------|-------|
| bom | ForeignKey | القائمة |
| material | ForeignKey | المادة |
| quantity | DecimalField | الكمية |
| unit | CharField | الوحدة |

### ProductionOrder - أمر الإنتاج
| الحقل | النوع | الوصف |
|-------|-------|-------|
| id | AutoField | المعرف |
| bom | ForeignKey | قائمة المواد |
| quantity | DecimalField | الكمية المطلوبة |
| produced | DecimalField | الكمية المنتجة |
| start_date | DateField | تاريخ البدء |
| end_date | DateField | تاريخ الانتهاء |
| status | CharField | الحالة |

---

## 🔗 خريطة العلاقات الرئيسية

```
                              ┌─────────────┐
                              │    User     │
                              └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐     ┌──────────┐
             │ Employee │     │ Customer │     │POSSession│
             └────┬─────┘     └────┬─────┘     └────┬─────┘
                  │                │                │
                  ▼                ▼                ▼
           ┌──────────┐     ┌──────────┐     ┌──────────┐
           │Attendance│     │  Invoice │     │ POSOrder │
           └──────────┘     └────┬─────┘     └────┬─────┘
                                 │                │
                                 ▼                ▼
                          ┌─────────────────────────────┐
                          │       InvoiceItem           │
                          │       POSOrderLine          │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                                   ┌──────────┐
                                   │ Product  │
                                   └────┬─────┘
                                        │
                         ┌──────────────┼──────────────┐
                         │              │              │
                         ▼              ▼              ▼
                   ┌──────────┐  ┌──────────┐  ┌──────────┐
                   │  Stock   │  │   BOM    │  │ Category │
                   └──────────┘  └──────────┘  └──────────┘
```

---

## 📊 إحصائيات الموديلات حسب التطبيق

| التطبيق | عدد الموديلات |
|---------|----------------|
| ecommerce | 42 |
| hr | 41 |
| crm | 37 |
| accounting | 30 |
| production | 25 |
| purchases | 22 |
| inventory | 18 |
| branches | 18 |
| smart_pricing | 16 |
| installments | 13 |
| sales | 13 |
| showrooms | 13 |
| projects | 11 |
| eservices | 11 |
| maintenance | 10 |
| core | 10 |
| **أخرى (64 تطبيق)** | **~310** |
| **المجموع** | **629** |

---

*الوثيقة التالية: [05-API-REFERENCE.md](05-API-REFERENCE.md)*

# 🗄️ 10 - مخطط قاعدة البيانات

## 📋 نظرة عامة

النظام يستخدم **629 موديل** موزعة على **79 تطبيق**. هذا الملف يوثق أهم الجداول والعلاقات.

---

## 📊 إحصائيات قاعدة البيانات

| المقياس | القيمة |
|---------|--------|
| عدد الجداول | ~650 |
| عدد الموديلات | 629 |
| عدد التطبيقات | 79 |
| قاعدة البيانات الافتراضية | SQLite |
| قاعدة البيانات الموصى بها | PostgreSQL |

---

## 🔗 مخطط العلاقات الرئيسي (ERD)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORE ENTITIES                                  │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    User     │
                              │  (auth_user)│
                              └──────┬──────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │ UserProfile │          │  Employee   │          │ POSSession  │
    └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
           │                         │                         │
           ▼                         ▼                         ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │  UserRole   │          │ Department  │          │  POSOrder   │
    └─────────────┘          └─────────────┘          └─────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS PARTNERS                                │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   Partner   │
                              └──────┬──────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
             ┌─────────────┐                  ┌─────────────┐
             │  Customer   │                  │  Supplier   │
             └──────┬──────┘                  └──────┬──────┘
                    │                                 │
         ┌─────────┴─────────┐               ┌──────┴──────┐
         │                   │               │             │
         ▼                   ▼               ▼             ▼
  ┌─────────────┐    ┌─────────────┐  ┌─────────────┐  ┌───────────┐
  │  SaleOrder  │    │ Opportunity │  │PurchaseBill │  │PurchaseOrd│
  └─────────────┘    └─────────────┘  └─────────────┘  └───────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                           INVENTORY                                      │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │  Category   │◀─────────│   Product   │─────────▶│   Stock     │
    └─────────────┘          └──────┬──────┘          └──────┬──────┘
                                    │                        │
                    ┌───────────────┼───────────────┐        │
                    │               │               │        │
                    ▼               ▼               ▼        ▼
             ┌───────────┐  ┌───────────┐  ┌───────────┐ ┌───────────┐
             │InvoiceItem│  │ BOMItem   │  │POSOrderLn │ │ Location  │
             └───────────┘  └───────────┘  └───────────┘ └───────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                           ACCOUNTING                                     │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │ FiscalYear  │◀─────────│JournalEntry │─────────▶│JournalItem  │
    └─────────────┘          └─────────────┘          └──────┬──────┘
                                                             │
                                                             ▼
                                                      ┌─────────────┐
                                                      │   Account   │
                                                      └──────┬──────┘
                                                             │
                                              ┌──────────────┴──────────────┐
                                              │                             │
                                              ▼                             ▼
                                       ┌─────────────┐              ┌─────────────┐
                                       │ CostCenter  │              │ AccountType │
                                       └─────────────┘              └─────────────┘
```

---

## 📝 الجداول الرئيسية

### 1. جدول المستخدمين (auth_user)

```sql
CREATE TABLE auth_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254),
    password VARCHAR(128) NOT NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined DATETIME NOT NULL,
    last_login DATETIME
);
```

### 2. جدول ملفات المستخدمين (users_userprofile)

```sql
CREATE TABLE users_userprofile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES auth_user(id),
    role_id INTEGER REFERENCES users_userrole(id),
    phone VARCHAR(20),
    avatar VARCHAR(200),
    language VARCHAR(10) DEFAULT 'ar',
    timezone VARCHAR(50),
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    updated_at DATETIME
);
```

### 3. جدول المنتجات (inventory_product)

```sql
CREATE TABLE inventory_product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    sku VARCHAR(50) UNIQUE,
    barcode VARCHAR(50),
    category_id INTEGER REFERENCES inventory_category(id),
    unit VARCHAR(20),
    cost_price DECIMAL(12, 2),
    sale_price DECIMAL(12, 2),
    tax_rate DECIMAL(5, 2) DEFAULT 15.00,
    min_stock DECIMAL(12, 2) DEFAULT 0,
    max_stock DECIMAL(12, 2),
    description TEXT,
    image VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_service BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE INDEX idx_product_sku ON inventory_product(sku);
CREATE INDEX idx_product_barcode ON inventory_product(barcode);
CREATE INDEX idx_product_category ON inventory_product(category_id);
```

### 4. جدول المخزون (inventory_stock)

```sql
CREATE TABLE inventory_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES inventory_product(id),
    location_id INTEGER NOT NULL REFERENCES inventory_location(id),
    quantity DECIMAL(12, 2) DEFAULT 0,
    reserved DECIMAL(12, 2) DEFAULT 0,
    batch_id INTEGER REFERENCES inventory_stockbatch(id),
    updated_at DATETIME,
    
    UNIQUE(product_id, location_id, batch_id)
);

CREATE INDEX idx_stock_product ON inventory_stock(product_id);
CREATE INDEX idx_stock_location ON inventory_stock(location_id);
```

### 5. جدول الفواتير (sales_invoice)

```sql
CREATE TABLE sales_invoice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES partners_customer(id),
    branch_id INTEGER REFERENCES branches_branch(id),
    salesperson_id INTEGER REFERENCES auth_user(id),
    date DATE NOT NULL,
    due_date DATE,
    subtotal DECIMAL(14, 2) DEFAULT 0,
    discount_amount DECIMAL(14, 2) DEFAULT 0,
    tax_amount DECIMAL(14, 2) DEFAULT 0,
    total DECIMAL(14, 2) DEFAULT 0,
    paid DECIMAL(14, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    payment_status VARCHAR(20) DEFAULT 'unpaid',
    notes TEXT,
    -- ZATCA Fields
    zatca_uuid VARCHAR(36),
    zatca_hash VARCHAR(64),
    zatca_qr TEXT,
    zatca_status VARCHAR(20),
    created_at DATETIME,
    updated_at DATETIME
);

CREATE INDEX idx_invoice_number ON sales_invoice(invoice_number);
CREATE INDEX idx_invoice_customer ON sales_invoice(customer_id);
CREATE INDEX idx_invoice_date ON sales_invoice(date);
CREATE INDEX idx_invoice_status ON sales_invoice(status);
```

### 6. جدول بنود الفاتورة (sales_invoiceitem)

```sql
CREATE TABLE sales_invoiceitem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES sales_invoice(id),
    product_id INTEGER NOT NULL REFERENCES inventory_product(id),
    quantity DECIMAL(12, 2) NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    discount DECIMAL(12, 2) DEFAULT 0,
    tax_rate DECIMAL(5, 2) DEFAULT 15.00,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    total DECIMAL(14, 2) NOT NULL
);

CREATE INDEX idx_invoiceitem_invoice ON sales_invoiceitem(invoice_id);
```

### 7. جدول الحسابات (accounting_account)

```sql
CREATE TABLE accounting_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    account_type VARCHAR(20) NOT NULL,
    parent_id INTEGER REFERENCES accounting_account(id),
    balance DECIMAL(14, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_system BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at DATETIME
);

CREATE INDEX idx_account_code ON accounting_account(code);
CREATE INDEX idx_account_type ON accounting_account(account_type);
CREATE INDEX idx_account_parent ON accounting_account(parent_id);
```

### 8. جدول القيود (accounting_journalentry)

```sql
CREATE TABLE accounting_journalentry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_number VARCHAR(50) UNIQUE NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    reference VARCHAR(100),
    total_debit DECIMAL(14, 2) DEFAULT 0,
    total_credit DECIMAL(14, 2) DEFAULT 0,
    is_posted BOOLEAN DEFAULT FALSE,
    is_reversed BOOLEAN DEFAULT FALSE,
    fiscal_year_id INTEGER REFERENCES accounting_fiscalyear(id),
    created_by_id INTEGER REFERENCES auth_user(id),
    created_at DATETIME,
    posted_at DATETIME
);

CREATE INDEX idx_journal_date ON accounting_journalentry(date);
CREATE INDEX idx_journal_fiscal ON accounting_journalentry(fiscal_year_id);
```

### 9. جدول الموظفين (hr_employee)

```sql
CREATE TABLE hr_employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INTEGER UNIQUE REFERENCES auth_user(id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    first_name_en VARCHAR(100),
    last_name_en VARCHAR(100),
    national_id VARCHAR(20),
    email VARCHAR(254),
    phone VARCHAR(20),
    department_id INTEGER REFERENCES hr_department(id),
    position_id INTEGER REFERENCES hr_jobposition(id),
    manager_id INTEGER REFERENCES hr_employee(id),
    hire_date DATE NOT NULL,
    end_date DATE,
    salary DECIMAL(12, 2),
    status VARCHAR(20) DEFAULT 'active',
    gender VARCHAR(10),
    birth_date DATE,
    photo VARCHAR(200),
    created_at DATETIME,
    updated_at DATETIME
);

CREATE INDEX idx_employee_id ON hr_employee(employee_id);
CREATE INDEX idx_employee_department ON hr_employee(department_id);
```

### 10. جدول طلبات POS (pos_posorder)

```sql
CREATE TABLE pos_posorder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    session_id INTEGER NOT NULL REFERENCES pos_possession(id),
    customer_id INTEGER REFERENCES partners_customer(id),
    table_id INTEGER REFERENCES pos_postable(id),
    subtotal DECIMAL(14, 2) DEFAULT 0,
    discount DECIMAL(14, 2) DEFAULT 0,
    tax DECIMAL(14, 2) DEFAULT 0,
    total DECIMAL(14, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'new',
    order_type VARCHAR(20) DEFAULT 'dine_in',
    notes TEXT,
    created_at DATETIME,
    completed_at DATETIME
);

CREATE INDEX idx_posorder_session ON pos_posorder(session_id);
CREATE INDEX idx_posorder_date ON pos_posorder(created_at);
```

---

## 🔗 العلاقات الرئيسية

### One-to-Many (1:N)

| الجدول الأب | الجدول الابن | العلاقة |
|-------------|--------------|---------|
| Category | Product | فئة ← منتجات |
| Product | Stock | منتج ← مخزون |
| Product | InvoiceItem | منتج ← بنود فواتير |
| Customer | Invoice | عميل ← فواتير |
| Invoice | InvoiceItem | فاتورة ← بنود |
| Account | JournalEntryItem | حساب ← بنود قيود |
| Department | Employee | قسم ← موظفين |
| POSSession | POSOrder | جلسة ← طلبات |

### Many-to-Many (N:N)

| الجدول 1 | الجدول 2 | جدول الربط |
|----------|----------|-------------|
| User | Permission | user_permissions |
| Group | Permission | group_permissions |
| Product | Location | Stock |
| Employee | WorkSchedule | EmployeeSchedule |

---

## 📈 الفهارس المهمة

```sql
-- فهارس الأداء
CREATE INDEX idx_invoice_date_status ON sales_invoice(date, status);
CREATE INDEX idx_stock_product_location ON inventory_stock(product_id, location_id);
CREATE INDEX idx_journal_date_posted ON accounting_journalentry(date, is_posted);
CREATE INDEX idx_employee_active ON hr_employee(status) WHERE status = 'active';

-- فهارس البحث النصي
CREATE INDEX idx_product_name ON inventory_product(name);
CREATE INDEX idx_customer_name ON partners_customer(name);
```

---

## 🔒 القيود (Constraints)

```sql
-- التحقق من القيم
ALTER TABLE inventory_stock 
    ADD CONSTRAINT chk_stock_quantity CHECK (quantity >= 0);

ALTER TABLE sales_invoice 
    ADD CONSTRAINT chk_invoice_total CHECK (total >= 0);

ALTER TABLE accounting_journalentry 
    ADD CONSTRAINT chk_journal_balance CHECK (total_debit = total_credit);

-- القيم الافتراضية
ALTER TABLE inventory_product 
    ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE sales_invoice 
    ALTER COLUMN status SET DEFAULT 'draft';
```

---

## 🔄 Triggers (المشغلات)

```sql
-- تحديث رصيد المخزون تلقائياً
CREATE TRIGGER update_stock_after_sale
AFTER INSERT ON sales_invoiceitem
FOR EACH ROW
BEGIN
    UPDATE inventory_stock 
    SET quantity = quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
END;

-- تحديث رصيد الحساب
CREATE TRIGGER update_account_balance
AFTER INSERT ON accounting_journalentryitem
FOR EACH ROW
BEGIN
    UPDATE accounting_account 
    SET balance = balance + NEW.debit - NEW.credit
    WHERE id = NEW.account_id;
END;
```

---

## 📊 استعلامات مفيدة

### رصيد المخزون لمنتج
```sql
SELECT 
    p.name,
    l.name as location,
    s.quantity,
    s.reserved,
    (s.quantity - s.reserved) as available
FROM inventory_stock s
JOIN inventory_product p ON s.product_id = p.id
JOIN inventory_location l ON s.location_id = l.id
WHERE p.id = 1;
```

### مبيعات اليوم
```sql
SELECT 
    COUNT(*) as invoice_count,
    SUM(total) as total_sales,
    SUM(paid) as total_paid
FROM sales_invoice
WHERE date = CURRENT_DATE
AND status = 'confirmed';
```

### ميزان المراجعة
```sql
SELECT 
    a.code,
    a.name,
    SUM(CASE WHEN ji.debit > 0 THEN ji.debit ELSE 0 END) as total_debit,
    SUM(CASE WHEN ji.credit > 0 THEN ji.credit ELSE 0 END) as total_credit
FROM accounting_account a
LEFT JOIN accounting_journalentryitem ji ON a.id = ji.account_id
LEFT JOIN accounting_journalentry j ON ji.entry_id = j.id
WHERE j.is_posted = TRUE
GROUP BY a.id, a.code, a.name
ORDER BY a.code;
```

---

## 🗃️ نسخ احتياطي

### PostgreSQL
```bash
# نسخ احتياطي
pg_dump -U user -d tony_erp > backup.sql

# استعادة
psql -U user -d tony_erp < backup.sql
```

### SQLite
```bash
# نسخ احتياطي
sqlite3 db.sqlite3 ".backup 'backup.sqlite3'"

# أو نسخ الملف مباشرة
cp db.sqlite3 backup.sqlite3
```

---

*نهاية التوثيق - يناير 2026*

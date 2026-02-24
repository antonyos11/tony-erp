# Tony ERP Test Suite

Comprehensive testing infrastructure for Tony ERP system with 500+ planned tests covering all critical business logic.

## 🚀 Quick Start

### Installation

```bash
cd /var/www/tony_erp
pip install -r requirements.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run only critical tests
pytest -m p0

# Run in parallel (faster)
pytest -n auto
```

### View Coverage

```bash
# Generate and open HTML coverage report
pytest --cov=. --cov-report=html
firefox htmlcov/index.html
```

## 📊 Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── factories.py                # Factory classes for test data
├── utils.py                    # Test utilities and helpers
├── unit/                       # Unit tests
│   ├── test_accounting_models.py  ✅ 22 tests
│   ├── test_sales_models.py       ✅ 25 tests
│   ├── test_inventory_models.py   ⏳ Pending
│   └── test_production_models.py  ⏳ Pending
├── integration/                # Integration tests
│   └── test_sales_flow.py      ⏳ Pending
├── api/                        # API tests
│   └── test_authentication.py  ⏳ Pending
└── performance/                # Performance tests
    └── test_concurrent_ops.py  ⏳ Pending
```

## 🎯 Test Markers

```bash
# By Priority
pytest -m p0          # Critical tests
pytest -m p1          # High priority
pytest -m p2          # Medium priority

# By Type
pytest -m unit        # Unit tests
pytest -m integration # Integration tests
pytest -m api         # API tests
pytest -m performance # Performance/load tests
pytest -m slow        # Slow tests

# By Module
pytest tests/unit/test_accounting_models.py
pytest tests/unit/test_sales_models.py
```

## 📋 Available Fixtures

### User Fixtures
- `user()` - Basic test user
- `admin_user()` - Superuser
- `accountant_user()` - Accountant role
- `authenticated_client()` - Django client with auth
- `authenticated_api_client()` - API client with auth

### Business Fixtures
- `fiscal_year()` - Fiscal year 2026
- `sample_chart_of_accounts()` - Complete chart of accounts
- `customer()` - Test customer
- `product()` - Test product
- `stock_item()` - Product with stock
- `bom()` - Bill of materials

See [conftest.py](conftest.py) for complete list.

## 🏭 Factory Classes

Create test data easily:

```python
from tests.factories import UserFactory, InvoiceFactory, ProductFactory

# Create a user
user = UserFactory()

# Create a product with stock
product = ProductFactory(price=100.00)
stock = StockFactory(product=product, quantity=1000)

# Create a complete invoice
invoice = InvoiceFactory()
InvoiceItemFactory(invoice=invoice, product=product, quantity=10)
```

See [factories.py](factories.py) for all available factories.

## 🛠️ Test Utilities

Helpful assertion and data generation functions:

```python
from tests.utils import assert_decimal_equal, assert_stock_quantity

# Assert decimal equality with precision
assert_decimal_equal(invoice.total, Decimal('1000.00'))

# Assert stock quantity
assert_stock_quantity(product, location, expected_quantity=100)

# Generate test data
invoice_data = generate_invoice_data(num_items=5)

# Test concurrent operations
results, errors = run_concurrent(create_invoice, num_threads=20)
```

See [utils.py](utils.py) for all utilities.

## 📈 Coverage Targets

- **Overall:** 70%
- **Critical Modules:** 80%
  - `accounting/` - Financial integrity
  - `sales/` - Revenue tracking
  - `inventory/` - Stock management
  - `production/` - Manufacturing
  - `purchases/` - Procurement

## 🔍 Example Tests

### Unit Test
```python
@pytest.mark.unit
@pytest.mark.p0
def test_invoice_total_calculation(customer, product, location):
    """Test invoice total calculation from items."""
    StockFactory(product=product, location=location, quantity=1000)
    
    invoice = InvoiceFactory(customer=customer)
    InvoiceItemFactory(
        invoice=invoice,
        product=product,
        quantity=10,
        price=Decimal('100.00')
    )
    
    assert_decimal_equal(invoice.total, Decimal('1000.00'))
```

### Integration Test
```python
@pytest.mark.integration
@pytest.mark.p1
def test_sales_full_cycle(customer, product, location, sample_chart_of_accounts):
    """Test complete sales cycle: Invoice → Stock → Accounting → Payment."""
    # Create stock
    StockFactory(product=product, location=location, quantity=100)
    
    # Create invoice
    invoice = InvoiceFactory(customer=customer)
    InvoiceItemFactory(invoice=invoice, product=product, quantity=10)
    
    # Verify stock deducted
    assert_stock_quantity(product, location, 90)
    
    # Verify journal entry created
    assert invoice.journal_entry is not None
    assert_journal_entry_balanced(invoice.journal_entry)
    
    # Record payment
    InvoicePaymentFactory(invoice=invoice, amount=invoice.total)
    
    # Verify invoice fully paid
    assert invoice.remaining == Decimal('0.00')
```

## 🐛 Testing Best Practices

1. **Use factories** for test data creation
2. **Use fixtures** for common setup
3. **Mark tests** with appropriate markers (p0, unit, etc.)
4. **Test edge cases** (zero amounts, 100% discount, etc.)
5. **Test race conditions** with `run_concurrent()`
6. **Assert with precision** using `assert_decimal_equal()`
7. **Keep tests isolated** - each test should be independent
8. **Name tests clearly** - test names should describe what they test

## 📚 Documentation

- [TESTING_IMPLEMENTATION_SUMMARY.md](../TESTING_IMPLEMENTATION_SUMMARY.md) - Complete implementation details
- [pytest docs](https://docs.pytest.org/) - pytest documentation
- [factory_boy docs](https://factoryboy.readthedocs.io/) - factory_boy documentation

## ✅ Current Status

- ✅ Infrastructure: 100%
- ✅ Factories: 100% (20+ factories)
- ✅ Fixtures: 100% (30+ fixtures)
- ✅ Utilities: 100% (25+ helpers)
- ✅ Unit Tests: 30% (47 tests)
- ⏳ Integration Tests: 0%
- ⏳ API Tests: 0%
- ⏳ Performance Tests: 0%

**Target:** 500+ tests, 70% overall coverage, 80% critical modules

---

*For detailed information, see [TESTING_IMPLEMENTATION_SUMMARY.md](../TESTING_IMPLEMENTATION_SUMMARY.md)*

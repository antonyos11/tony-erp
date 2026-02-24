from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from inventory.models import Location, Product, Stock, StockBatch
from pos.models import POSSession, POSOrder, POSOrderLine

User = get_user_model()


class POSReturnTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='x')

    def test_pos_return_happy_path(self):
        loc = Location.objects.create(name='Main Store', code='ST1', type='store')
        prod = Product.objects.create(sku='SKU1', name='Prod1', price=Decimal('100'), cost=Decimal('40'))
        Stock.objects.create(product=prod, location=loc, quantity=10)
        StockBatch.objects.create(product=prod, location=loc, lot_number='B1', unit_cost=prod.cost, quantity=10)
        session = POSSession.objects.create(user=self.user, opening_balance=0, location=loc)
        order = POSOrder.objects.create(session=session, location=loc)
        POSOrderLine.objects.create(order=order, product=prod, quantity=2, price=prod.price)
        order.finalize_payment(Decimal('200'))
        self.assertEqual(order.status, 'paid')
        self.assertTrue(order.cogs_amount > 0)
        ret = POSOrder.objects.create(session=session, location=loc, is_return=True, original_order=order)
        POSOrderLine.objects.create(order=ret, product=prod, quantity=1, price=prod.price)
        ret.finalize_payment(Decimal('100'))
        self.assertEqual(ret.status, 'paid')
        stock = Stock.objects.get(product=prod, location=loc)
        self.assertEqual(stock.quantity, 9)  # 10 -2 +1

    def test_pos_return_exceed_quantity_raises(self):
        loc = Location.objects.create(name='Main Store2', code='ST2', type='store')
        prod = Product.objects.create(sku='SKU2', name='Prod2', price=Decimal('50'), cost=Decimal('20'))
        Stock.objects.create(product=prod, location=loc, quantity=5)
        StockBatch.objects.create(product=prod, location=loc, lot_number='B2', unit_cost=prod.cost, quantity=5)
        session = POSSession.objects.create(user=self.user, opening_balance=0, location=loc)
        order = POSOrder.objects.create(session=session, location=loc)
        POSOrderLine.objects.create(order=order, product=prod, quantity=2, price=prod.price)
        order.finalize_payment(Decimal('100'))
        bad_ret = POSOrder.objects.create(session=session, location=loc, is_return=True, original_order=order)
        POSOrderLine.objects.create(order=bad_ret, product=prod, quantity=3, price=prod.price)
        with self.assertRaises(ValueError):
            bad_ret.finalize_payment(Decimal('150'))

"""
وحدة المشتريات (Purchasing)

- إدارة طلبات الشراء (PR) وتحويلها إلى أوامر شراء (PO) بعد الاعتماد.
- مقارنة عروض الأسعار (RFQ) مع سجل تاريخي لأسعار كل مادة.
- جدول تسليم المورد (lead time) + تتبع الشحنات.
- استلام الواردات مع السماح باختلاف الكمية والجودة عن الـ PO.
- ربط فواتير المورد بالـ PO وتجهيز القيود المحاسبية التلقائية.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


# --- enums & shared types ----------------------------------------------------


class PRStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED_TO_PO = "converted_to_po"


class POStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class RFQStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"


class ShipmentStatus(str, Enum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


# --- core purchasing documents -----------------------------------------------


@dataclass
class PurchaseRequestLine:
    item_code: str
    description: str
    qty: float
    uom: str
    required_date: Optional[datetime] = None
    notes: str = ""


@dataclass
class PurchaseRequest:
    pr_no: str
    requester: str
    department: str
    lines: List[PurchaseRequestLine]
    status: PRStatus = PRStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    def submit(self) -> None:
        # ...existing code...
        if self.status != PRStatus.DRAFT:
            raise ValueError("لا يمكن إرسال طلب شراء إلا من حالة مسودة.")
        self.status = PRStatus.SUBMITTED

    def approve(self, approver: str) -> None:
        if self.status != PRStatus.SUBMITTED:
            raise ValueError("لا يمكن اعتماد طلب شراء إلا بعد إرساله.")
        self.status = PRStatus.APPROVED
        self.approved_by = approver
        self.approved_at = datetime.utcnow()

    def to_po(self, po_no: str, supplier_code: str) -> "PurchaseOrder":
        if self.status != PRStatus.APPROVED:
            raise ValueError("يجب اعتماد طلب الشراء قبل تحويله إلى أمر شراء.")
        po_lines = [
            PurchaseOrderLine(
                item_code=l.item_code,
                description=l.description,
                qty=l.qty,
                uom=l.uom,
            )
            for l in self.lines
        ]
        po = PurchaseOrder(
            po_no=po_no,
            supplier_code=supplier_code,
            pr_ref=self.pr_no,
            lines=po_lines,
        )
        self.status = PRStatus.CONVERTED_TO_PO
        return po


@dataclass
class PurchaseOrderLine:
    item_code: str
    description: str
    qty: float
    uom: str
    unit_price: float = 0.0
    delivery_date: Optional[datetime] = None
    received_qty: float = 0.0

    @property
    def line_total(self) -> float:
        return self.qty * self.unit_price


@dataclass
class PurchaseOrder:
    po_no: str
    supplier_code: str
    lines: List[PurchaseOrderLine]
    pr_ref: Optional[str] = None
    status: POStatus = POStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)

    def confirm(self) -> None:
        if self.status != POStatus.DRAFT:
            raise ValueError("يمكن تأكيد أمر الشراء من حالة مسودة فقط.")
        self.status = POStatus.CONFIRMED

    def update_receive_progress(self) -> None:
        total = sum(l.qty for l in self.lines)
        received = sum(l.received_qty for l in self.lines)
        if received == 0:
            return
        if received < total:
            self.status = POStatus.PARTIALLY_RECEIVED
        else:
            self.status = POStatus.RECEIVED

    @property
    def grand_total(self) -> float:
        return sum(l.line_total for l in self.lines)


# --- RFQ and price history ---------------------------------------------------


@dataclass
class PriceHistoryRecord:
    item_code: str
    supplier_code: str
    currency: str
    unit_price: float
    valid_from: datetime
    rfq_ref: Optional[str] = None
    po_ref: Optional[str] = None


@dataclass
class RFQLine:
    item_code: str
    description: str
    qty: float
    uom: str


@dataclass
class RFQQuote:
    supplier_code: str
    currency: str
    lines_prices: dict  # item_code -> unit_price
    delivery_days: Optional[int] = None
    notes: str = ""


@dataclass
class RFQ:
    rfq_no: str
    lines: List[RFQLine]
    status: RFQStatus = RFQStatus.OPEN
    quotes: List[RFQQuote] = field(default_factory=list)

    def add_quote(self, quote: RFQQuote) -> None:
        if self.status != RFQStatus.OPEN:
            raise ValueError("لا يمكن إضافة عرض سعر على RFQ غير مفتوح.")
        self.quotes.append(quote)

    def compare_quotes(self) -> List[RFQQuote]:
        """
        تعيد العروض مرتبة حسب أقل سعر إجمالي.
        """
        def total_cost(q: RFQQuote) -> float:
            return sum(
                (q.lines_prices.get(l.item_code, 0) * l.qty) for l in self.lines
            )

        return sorted(self.quotes, key=total_cost)


# --- supplier lead time & shipment tracking ----------------------------------


@dataclass
class SupplierLeadTime:
    supplier_code: str
    item_code: str
    lead_time_days: int
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Shipment:
    shipment_no: str
    po_no: str
    bl_no: str  # رقم بوليصة الشحن
    carrier: str
    eta: Optional[datetime] = None  # estimated time of arrival
    status: ShipmentStatus = ShipmentStatus.PLANNED
    tracking_url: Optional[str] = None
    notes: str = ""


# --- receiving & quality -----------------------------------------------------


@dataclass
class ReceiptLine:
    po_line_index: int
    received_qty: float
    accepted_qty: float
    rejected_qty: float
    quality_notes: str = ""


@dataclass
class Receipt:
    receipt_no: str
    po_no: str
    lines: List[ReceiptLine]
    received_at: datetime = field(default_factory=datetime.utcnow)

    def apply_to_po(self, po: PurchaseOrder) -> None:
        """
        تحديث كميات الاستلام في أمر الشراء، مع السماح بالاختلاف
        عن الكميات الأصلية.
        """
        if po.po_no != self.po_no:
            raise ValueError("رقم أمر الشراء لا يطابق رقم الاستلام.")
        for line in self.lines:
            po_line = po.lines[line.po_line_index]
            po_line.received_qty += line.received_qty
        po.update_receive_progress()


# --- supplier invoice & accounting hook --------------------------------------


@dataclass
class SupplierInvoiceLine:
    po_line_index: int
    qty: float
    unit_price: float


@dataclass
class SupplierInvoice:
    invoice_no: str
    po_no: str
    supplier_code: str
    lines: List[SupplierInvoiceLine]
    invoice_date: datetime = field(default_factory=datetime.utcnow)

    @property
    def total(self) -> float:
        return sum(l.qty * l.unit_price for l in self.lines)

    def generate_accounting_entries(self) -> List[dict]:
        """
        تجهيز قيود محاسبية تلقائية للربط مع نظام الحسابات العام.
        ترجع قائمة قيود بصيغة بسيطة يمكن لنظام المحاسبة استيرادها.
        """
        entries = []
        amount = self.total
        # مثال مبسط: من المخزون إلى حساب المورد
        entries.append(
            {
                "account": "Inventory",
                "debit": amount,
                "credit": 0.0,
                "ref": self.invoice_no,
                "po_no": self.po_no,
            }
        )
        entries.append(
            {
                "account": "Accounts Payable",
                "debit": 0.0,
                "credit": amount,
                "ref": self.invoice_no,
                "po_no": self.po_no,
            }
        )
        return entries
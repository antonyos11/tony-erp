"""
Core Workflows Package
نظام إدارة سير العمل للعمليات الحرجة
"""

from .base_workflow import WorkflowEngine, WorkflowState, WorkflowAction
from .invoice_workflow import InvoiceWorkflow
from .journal_workflow import JournalEntryWorkflow
from .approval_workflow import ApprovalWorkflow

__all__ = [
    'WorkflowEngine',
    'WorkflowState',
    'WorkflowAction',
    'InvoiceWorkflow',
    'JournalEntryWorkflow',
    'ApprovalWorkflow',
]



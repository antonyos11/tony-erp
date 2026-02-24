from django.db import models
from django.utils import timezone
from decimal import Decimal


class ReportsMeta(models.Model):
	"""Dummy model to attach custom report permissions (no table)."""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	class Meta:
		managed = False
		default_permissions = ()
		permissions = [
			("view_reports", "Can view aggregated reports"),
			("export_reports", "Can export report data"),
		]


class ReportDailySnapshot(models.Model):
	"""Stores a daily snapshot of key financial / inventory metrics for historical accuracy.

	The snapshot is intentionally denormalized for fast retrieval in trend / comparison endpoints.
	Additional fields can be appended safely (nullable) in future migrations.
	"""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	date = models.DateField(db_index=True)
	created_at = models.DateTimeField(default=timezone.now, db_index=True)

	# Core P&L metrics (single-day period)
	net_revenue = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
	expenses = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
	cogs_approx = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
	cogs_fifo = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
	cogs_weighted = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

	# Inventory value (closing for the day)
	closing_inventory_value = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))

	class Meta:
		unique_together = ("date",)
		ordering = ['-date']

	def __str__(self):  # pragma: no cover - trivial
		return f"Snapshot {self.date} (rev={self.net_revenue} cogs={self.cogs_fifo or self.cogs_weighted or self.cogs_approx})"

	@property
	def gross_profit_fifo(self):
		if self.cogs_fifo is not None:
			return float(self.net_revenue) - float(self.cogs_fifo)
		return None

	@property
	def gross_profit_weighted(self):
		if self.cogs_weighted is not None:
			return float(self.net_revenue) - float(self.cogs_weighted)
		return None

	@property
	def gross_profit_approx(self):
		return float(self.net_revenue) - float(self.cogs_approx)


class ReportVarianceIncident(models.Model):
	"""Persistent log of high variance warnings for auditing & historical analysis.

	Incidents are appended (no updates) so we keep them lean; optional date range fields
	allow correlating with report period when supplied.
	"""
	id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
	created_at = models.DateTimeField(default=timezone.now, db_index=True)
	report = models.CharField(max_length=120, db_index=True)
	percent = models.FloatField(help_text="Variance percent magnitude (absolute value).")
	threshold_used = models.FloatField(help_text="Effective threshold that triggered warning.")
	global_min_applied = models.BooleanField(default=False)
	date_from = models.DateField(null=True, blank=True, db_index=True)
	date_to = models.DateField(null=True, blank=True, db_index=True)
	extra = models.JSONField(null=True, blank=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=["report", "-created_at"]),
		]

	def __str__(self):  # pragma: no cover - trivial
		return f"VarianceIncident[{self.report}] {self.percent}% at {self.created_at:%Y-%m-%d %H:%M:%S}"


# استيراد نماذج بناء التقارير المتقدم
from reports.models_builder import (
	ReportTemplate,
	ReportExecution,
	ReportField,
	ReportFilter,
	SavedReport
)


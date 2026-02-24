from django.contrib import admin
from .models import LoyaltyProgram, LoyaltyTier, CustomerLoyalty, PointsTransaction, LoyaltyReward

class LoyaltyTierInline(admin.TabularInline):
    model = LoyaltyTier
    extra = 1

@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'points_per_unit', 'redemption_rate', 'is_active']
    list_filter = ['is_active']
    inlines = [LoyaltyTierInline]

@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = ['customer', 'program', 'current_points', 'current_tier', 'last_activity']
    list_filter = ['program', 'current_tier']
    search_fields = ['customer__name']

@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ['loyalty_account', 'transaction_type', 'points', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']

@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'program', 'points_cost', 'reward_type', 'is_active']
    list_filter = ['program', 'reward_type', 'is_active']

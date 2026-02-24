from django import forms
from .models import LoyaltyProgram, LoyaltyTier, LoyaltyReward

class LoyaltyProgramForm(forms.ModelForm):
    class Meta:
        model = LoyaltyProgram
        fields = ['name', 'code', 'description', 'points_per_unit', 'redemption_rate', 'min_points_redeem', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'points_per_unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'redemption_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_points_redeem': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class LoyaltyRewardForm(forms.ModelForm):
    class Meta:
        model = LoyaltyReward
        fields = ['name', 'description', 'points_cost', 'reward_type', 'reward_value', 'quantity_available', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'points_cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'reward_type': forms.Select(attrs={'class': 'form-select'}),
            'reward_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-control'}),
        }

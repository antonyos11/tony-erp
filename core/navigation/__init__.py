"""
Core Navigation Package
محرك القوائم الديناميكي
"""

from .menu_engine import MenuEngine, get_user_menu, get_dashboard_for_role
from .menu_config import MAIN_MENU_STRUCTURE

__all__ = [
    'MenuEngine',
    'get_user_menu',
    'get_dashboard_for_role',
    'MAIN_MENU_STRUCTURE',
]




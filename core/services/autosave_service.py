"""
Autosave and Conflict Detection Service
Handles automatic saving of draft data and detects edit conflicts
"""
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json


class AutosaveService:
    """Service for autosaving form data"""
    
    CACHE_TIMEOUT = 3600  # 1 hour
    CACHE_PREFIX = 'autosave'
    
    @classmethod
    def save_draft(cls, user_id, model_name, instance_id, data):
        """
        Save draft data to cache
        
        Args:
            user_id: ID of the user
            model_name: Name of the model (e.g., 'invoice', 'quotation')
            instance_id: ID of the instance (or 'new' for new records)
            data: Dictionary of form data
        
        Returns:
            bool: True if saved successfully
        """
        cache_key = cls._get_cache_key(user_id, model_name, instance_id)
        
        draft_data = {
            'data': data,
            'saved_at': timezone.now().isoformat(),
            'user_id': user_id,
        }
        
        return cache.set(cache_key, json.dumps(draft_data), cls.CACHE_TIMEOUT)
    
    @classmethod
    def load_draft(cls, user_id, model_name, instance_id):
        """
        Load draft data from cache
        
        Returns:
            dict: Draft data or None if not found
        """
        cache_key = cls._get_cache_key(user_id, model_name, instance_id)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        
        return None
    
    @classmethod
    def clear_draft(cls, user_id, model_name, instance_id):
        """Clear draft data from cache"""
        cache_key = cls._get_cache_key(user_id, model_name, instance_id)
        return cache.delete(cache_key)
    
    @classmethod
    def _get_cache_key(cls, user_id, model_name, instance_id):
        """Generate cache key"""
        return f"{cls.CACHE_PREFIX}:{user_id}:{model_name}:{instance_id}"


class ConflictDetector:
    """Service for detecting edit conflicts"""
    
    LOCK_TIMEOUT = 300  # 5 minutes
    LOCK_PREFIX = 'edit_lock'
    
    @classmethod
    def acquire_lock(cls, model_name, instance_id, user_id):
        """
        Try to acquire edit lock
        
        Returns:
            tuple: (success: bool, current_user: dict or None)
        """
        lock_key = cls._get_lock_key(model_name, instance_id)
        existing_lock = cache.get(lock_key)
        
        if existing_lock:
            try:
                lock_data = json.loads(existing_lock)
                # Check if it's the same user
                if lock_data['user_id'] == user_id:
                    # Refresh lock
                    return cls._set_lock(lock_key, user_id), None
                else:
                    # Different user has lock
                    return False, lock_data
            except json.JSONDecodeError:
                pass
        
        # No lock exists, acquire it
        return cls._set_lock(lock_key, user_id), None
    
    @classmethod
    def release_lock(cls, model_name, instance_id, user_id):
        """Release edit lock"""
        lock_key = cls._get_lock_key(model_name, instance_id)
        existing_lock = cache.get(lock_key)
        
        if existing_lock:
            try:
                lock_data = json.loads(existing_lock)
                # Only release if it's the same user
                if lock_data['user_id'] == user_id:
                    return cache.delete(lock_key)
            except json.JSONDecodeError:
                pass
        
        return False
    
    @classmethod
    def check_version(cls, model_instance, submitted_version):
        """
        Check if the submitted version matches current version
        
        Args:
            model_instance: The model instance
            submitted_version: The version number from the form
        
        Returns:
            bool: True if versions match
        """
        # Check if model has version field
        if not hasattr(model_instance, 'version'):
            return True  # No version tracking
        
        current_version = getattr(model_instance, 'version', 0)
        
        try:
            submitted = int(submitted_version)
            return current_version == submitted
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def _set_lock(cls, lock_key, user_id):
        """Set lock in cache"""
        lock_data = {
            'user_id': user_id,
            'locked_at': timezone.now().isoformat(),
        }
        return cache.set(lock_key, json.dumps(lock_data), cls.LOCK_TIMEOUT)
    
    @classmethod
    def _get_lock_key(cls, model_name, instance_id):
        """Generate lock key"""
        return f"{cls.LOCK_PREFIX}:{model_name}:{instance_id}"

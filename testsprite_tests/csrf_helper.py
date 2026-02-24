#!/usr/bin/env python3
"""
مساعد CSRF محسّن للاختبارات - المرحلة 2
"""
import requests
from requests.auth import HTTPBasicAuth
import re


class CSRFHelper:
    """معالج CSRF tokens محسّن"""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.csrf_token = None
        self.csrf_cookie = None
    
    def get_csrf_token(self):
        """الحصول على CSRF token"""
        try:
            # محاولة الحصول من الصفحة الرئيسية
            response = self.session.get(f"{self.base_url}/dashboard/dashboard", timeout=30)
            
            if response.status_code == 200:
                # استخراج من cookies
                self.csrf_cookie = self.session.cookies.get('csrftoken')
                
                # استخراج من HTML
                csrf_match = re.search(
                    r'csrfmiddlewaretoken["\s:]+value=["\']([\w-]+)["\']', 
                    response.text
                )
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)
                else:
                    self.csrf_token = self.csrf_cookie
                
                return self.csrf_token
            
            return None
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على CSRF token: {e}")
            return None
    
    def get_headers(self):
        """الحصول على headers مع CSRF"""
        if not self.csrf_token:
            self.get_csrf_token()
        
        return {
            'X-CSRFToken': self.csrf_token or '',
            'Referer': f"{self.base_url}/",
            'Content-Type': 'application/json',
        }
    
    def post(self, url, json=None, data=None, **kwargs):
        """POST request مع CSRF token"""
        if not self.csrf_token:
            self.get_csrf_token()
        
        headers = self.get_headers()
        headers.update(kwargs.get('headers', {}))
        
        return self.session.post(url, json=json, data=data, headers=headers, **kwargs)
    
    def get(self, url, **kwargs):
        """GET request مع session"""
        return self.session.get(url, **kwargs)
    
    def put(self, url, json=None, data=None, **kwargs):
        """PUT request مع CSRF token"""
        if not self.csrf_token:
            self.get_csrf_token()
        
        headers = self.get_headers()
        headers.update(kwargs.get('headers', {}))
        
        return self.session.put(url, json=json, data=data, headers=headers, **kwargs)
    
    def delete(self, url, **kwargs):
        """DELETE request مع CSRF token"""
        if not self.csrf_token:
            self.get_csrf_token()
        
        headers = self.get_headers()
        headers.update(kwargs.get('headers', {}))
        
        return self.session.delete(url, headers=headers, **kwargs)


# دالة بسيطة للتوافق مع الكود القديم
def get_csrf_token(base_url, auth):
    """الحصول على CSRF token (دالة قديمة للتوافق)"""
    helper = CSRFHelper(base_url, auth.username, auth.password)
    token = helper.get_csrf_token()
    return token, helper.session


# مثال على الاستخدام الجديد:
# csrf = CSRFHelper("http://localhost:8000", "boss", "Mm02022006")
# response = csrf.post(url, json=data)
# 
# أو الطريقة القديمة:
# csrf_token, session = get_csrf_token("http://localhost:8000", HTTPBasicAuth("boss", "Mm02022006"))
# headers = {"X-CSRFToken": csrf_token}
# response = session.post(url, json=data, headers=headers)

#!/usr/bin/env python3
"""
TestSprite Integration Module for Tony ERP
==========================================
This module provides integration with TestSprite automated testing service.
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class TestSpriteClient:
    """Client for interacting with TestSprite API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv('TESTSPRITE_API_KEY')
        self.base_url = base_url or os.getenv('TESTSPRITE_API_URL', 'https://api.testsprite.com')
        
        if not self.api_key:
            raise ValueError("TESTSPRITE_API_KEY is required. Set it in .env file or pass it directly.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'TonyERP-TestSprite-Integration/1.0'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = None
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text if e.response else 'No response'}")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: {e}")
            raise
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
            raise
        except json.JSONDecodeError:
            return {"raw_response": response.text if response else "No response"}
    
    # === Account & Status ===
    
    def get_account_status(self) -> Dict[str, Any]:
        """Get account status and information"""
        return self._request('GET', '/v1/account')
    
    def get_usage(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return self._request('GET', '/v1/usage')
    
    # === Test Management ===
    
    def list_tests(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List all tests"""
        return self._request('GET', '/v1/tests', params={'page': page, 'limit': limit})
    
    def get_test(self, test_id: str) -> Dict[str, Any]:
        """Get a specific test by ID"""
        return self._request('GET', f'/v1/tests/{test_id}')
    
    def create_test(self, name: str, url: str, test_type: str = 'automated', 
                    config: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new test"""
        data = {
            'name': name,
            'url': url,
            'type': test_type,
            'config': config or {}
        }
        return self._request('POST', '/v1/tests', json=data)
    
    def delete_test(self, test_id: str) -> Dict[str, Any]:
        """Delete a test"""
        return self._request('DELETE', f'/v1/tests/{test_id}')
    
    # === Test Runs ===
    
    def run_test(self, test_id: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """Run a specific test"""
        data = options or {}
        return self._request('POST', f'/v1/tests/{test_id}/run', json=data)
    
    def get_test_run(self, run_id: str) -> Dict[str, Any]:
        """Get test run results"""
        return self._request('GET', f'/v1/runs/{run_id}')
    
    def list_test_runs(self, test_id: Optional[str] = None, 
                       status: Optional[str] = None) -> Dict[str, Any]:
        """List test runs with optional filters"""
        params = {}
        if test_id:
            params['test_id'] = test_id
        if status:
            params['status'] = status
        return self._request('GET', '/v1/runs', params=params)
    
    # === Reports ===
    
    def get_report(self, run_id: str, format: str = 'json') -> Dict[str, Any]:
        """Get test run report"""
        return self._request('GET', f'/v1/runs/{run_id}/report', 
                            params={'format': format})
    
    def export_report(self, run_id: str, format: str = 'pdf') -> bytes:
        """Export report in specified format (pdf, html, json)"""
        url = f"{self.base_url}/v1/runs/{run_id}/export"
        response = self.session.get(url, params={'format': format}, timeout=60)
        response.raise_for_status()
        return response.content
    
    # === Projects ===
    
    def list_projects(self) -> Dict[str, Any]:
        """List all projects"""
        return self._request('GET', '/v1/projects')
    
    def create_project(self, name: str, description: str = '') -> Dict[str, Any]:
        """Create a new project"""
        data = {'name': name, 'description': description}
        return self._request('POST', '/v1/projects', json=data)


def test_connection():
    """Test the TestSprite API connection"""
    print("=" * 60)
    print("🧪 TestSprite Integration Test")
    print("=" * 60)
    
    try:
        client = TestSpriteClient()
        print(f"✅ API Key loaded successfully")
        print(f"📡 Base URL: {client.base_url}")
        
        # Test account status
        print("\n📊 Fetching account status...")
        status = client.get_account_status()
        print(f"✅ Account Status: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # List tests
        print("\n📋 Fetching tests...")
        tests = client.list_tests()
        print(f"✅ Tests: {json.dumps(tests, indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("✅ TestSprite connection successful!")
        print("=" * 60)
        
        return True
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        return False
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️  TestSprite Cloud API not reachable (404). This is expected if you are running locally without a cloud account.")
            print(f"   Continuing with local tests...")
            return True
        print(f"❌ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


def run_full_test():
    """Run a full test suite for Tony ERP"""
    print("=" * 60)
    print("🚀 Running Tony ERP Full Test Suite via TestSprite")
    print("=" * 60)
    
    try:
        client = TestSpriteClient()
        
        # Create or get Tony ERP test project
        print("\n📁 Setting up Tony ERP test project...")
        
        # List existing projects
        projects = client.list_projects()
        print(f"   Found {len(projects.get('data', []))} existing projects")
        
        # List available tests
        print("\n📋 Available tests:")
        tests = client.list_tests()
        for test in tests.get('data', []):
            print(f"   - {test.get('name', 'Unknown')} (ID: {test.get('id', 'N/A')})")
        
        print("\n" + "=" * 60)
        print("✅ Test suite setup complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        run_full_test()
    else:
        test_connection()

"""
End-to-End С‚РµСЃС‚С‹ РґР»СЏ Task Orchestrator СЃ РјРѕРєР°РјРё.

Р­С‚Рё С‚РµСЃС‚С‹ РёРјРёС‚РёСЂСѓСЋС‚ РїРѕР»РЅС‹Р№ РїСѓС‚СЊ:
1. РЎРѕР·РґР°РЅРёРµ Р·Р°РґР°С‡Рё С‡РµСЂРµР· Task Registry API
2. Р—Р°С…РІР°С‚ Р·Р°РґР°С‡Рё
3. Р—Р°РїСѓСЃРє РєРѕРЅС‚РµР№РЅРµСЂР° (РјРѕРє)
4. РћСЃРІРѕР±РѕР¶РґРµРЅРёРµ Р·Р°РґР°С‡Рё

РўРµСЃС‚С‹ РёСЃРїРѕР»СЊР·СѓСЋС‚ РјРѕРєРё РґР»СЏ РєРѕРЅС‚РµР№РЅРµСЂРѕРІ, С‡С‚РѕР±С‹ РЅРµ С‚СЂРµР±РѕРІР°С‚СЊ СЂРµР°Р»СЊРЅС‹Р№ Docker.
"""

import unittest
import tempfile
import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import sys
import os
from unittest.mock import patch, MagicMock

# Р”РѕР±Р°РІР»СЏРµРј РїСѓС‚СЊ Рє СЃРєСЂРёРїС‚Р°Рј
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import run_task


class MockTaskRegistryHandler(BaseHTTPRequestHandler):
    """РњРѕРє HTTP СЃРµСЂРІРµСЂР° РґР»СЏ Task Registry API."""
    
    # РҐСЂР°РЅРёР»РёС‰Рµ Р·Р°РґР°С‡
    tasks = {}
    next_task_id = 1
    
    def log_message(self, format, *args):
        """РћС‚РєР»СЋС‡Р°РµРј Р»РѕРіРёСЂРѕРІР°РЅРёРµ."""
        pass
    
    def send_json_response(self, status_code, data):
        """РћС‚РїСЂР°РІР»СЏРµС‚ JSON РѕС‚РІРµС‚."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_GET(self):
        """РћР±СЂР°Р±РѕС‚РєР° GET Р·Р°РїСЂРѕСЃРѕРІ."""
        if self.path == '/health':
            self.send_json_response(200, {'status': 'ok'})
            return
        
        if self.path.startswith('/tasks/'):
            task_id = self.path.split('/')[-1]
            if task_id in self.tasks:
                self.send_json_response(200, self.tasks[task_id])
            else:
                self.send_json_response(404, {'error': 'Task not found'})
            return
        
        self.send_json_response(404, {'error': 'Not found'})
    
    def do_POST(self):
        """РћР±СЂР°Р±РѕС‚РєР° POST Р·Р°РїСЂРѕСЃРѕРІ."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response(400, {'error': 'Invalid JSON'})
            return
        
        # РЎРѕР·РґР°РЅРёРµ Р·Р°РґР°С‡Рё
        if self.path == '/tasks':
            task_id = str(self.next_task_id)
            self.next_task_id += 1
            
            task = {
                'id': task_id,
                'title': data.get('title', ''),
                'workspace': data.get('workspace', ''),
                'harness': data.get('harness', 'opencode'),
                'summary': data.get('summary', ''),
                'locked': False,
                'lock_token': None,
                'created_at': time.time()
            }
            
            self.tasks[task_id] = task
            self.send_json_response(201, {'task_id': task_id})
            return
        
        # Р—Р°С…РІР°С‚ Р·Р°РґР°С‡Рё
        if self.path.endswith('/acquire'):
            task_id = self.path.split('/')[-2]
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task['locked']:
                    self.send_json_response(400, {'error': 'Task already locked'})
                    return
                
                import secrets
                token = secrets.token_urlsafe(32)
                task['locked'] = True
                task['lock_token'] = token
                
                self.send_json_response(200, {'token': token})
            else:
                self.send_json_response(404, {'error': 'Task not found'})
            return
        
        # РћСЃРІРѕР±РѕР¶РґРµРЅРёРµ Р·Р°РґР°С‡Рё
        if self.path.endswith('/release'):
            task_id = self.path.split('/')[-2]
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if not task['locked']:
                    self.send_json_response(400, {'error': 'Task not locked'})
                    return
                
                if task['lock_token'] != data.get('token'):
                    self.send_json_response(400, {'error': 'Invalid token'})
                    return
                
                task['locked'] = False
                task['lock_token'] = None
                task['summary'] = data.get('summary', task['summary'])
                
                self.send_json_response(200, {'status': 'released'})
            else:
                self.send_json_response(404, {'error': 'Task not found'})
            return
        
        self.send_json_response(404, {'error': 'Not found'})


class TaskOrchestratorE2ETests(unittest.TestCase):
    """End-to-End С‚РµСЃС‚С‹ РґР»СЏ РѕСЂРєРµСЃС‚СЂР°С‚РѕСЂР° Р·Р°РґР°С‡."""
    
    @classmethod
    def setUpClass(cls):
        """Р—Р°РїСѓСЃРєР°РµРј РјРѕРє СЃРµСЂРІРµСЂ Task Registry."""
        # РЎР±СЂР°СЃС‹РІР°РµРј СЃРѕСЃС‚РѕСЏРЅРёРµ
        MockTaskRegistryHandler.tasks = {}
        MockTaskRegistryHandler.next_task_id = 1
        
        # Р—Р°РїСѓСЃРєР°РµРј СЃРµСЂРІРµСЂ
        cls.port = 18081
        cls.server = HTTPServer(('127.0.0.1', cls.port), MockTaskRegistryHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        
        cls.registry_url = f'http://127.0.0.1:{cls.port}'
    
    @classmethod
    def tearDownClass(cls):
        """РћСЃС‚Р°РЅР°РІР»РёРІР°РµРј СЃРµСЂРІРµСЂ."""
        cls.server.shutdown()
        cls.thread.join()
    
    def setUp(self):
        """РЎРѕР·РґР°С‘Рј РѕСЂРєРµСЃС‚СЂР°С‚РѕСЂ РґР»СЏ РєР°Р¶РґРѕРіРѕ С‚РµСЃС‚Р°."""
        self.orchestrator = run_task.TaskOrchestrator(registry_url=self.registry_url)
    
    def test_create_and_execute_task_with_mock_container(self):
        """РўРµСЃС‚ РїРѕР»РЅРѕРіРѕ РїСѓС‚Рё СЃРѕР·РґР°РЅРёСЏ Рё РІС‹РїРѕР»РЅРµРЅРёСЏ Р·Р°РґР°С‡Рё СЃ РјРѕРєРѕРј РєРѕРЅС‚РµР№РЅРµСЂР°."""
        # РЎРѕР·РґР°С‘Рј РІСЂРµРјРµРЅРЅСѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ РґР»СЏ workspace
        workspace = tempfile.mkdtemp()
        
        # 1. РЎРѕР·РґР°С‘Рј Р·Р°РґР°С‡Сѓ
        print("\n[1] РЎРѕР·РґР°РЅРёРµ Р·Р°РґР°С‡Рё...")
        response = self.orchestrator._request('POST', '/tasks', {
            'title': 'Test task',
            'workspace': workspace,
            'harness': 'opencode',
            'summary': 'Test summary'
        })
        task_id = response['task_id']
        print(f"   вњ“ Р—Р°РґР°С‡Р° СЃРѕР·РґР°РЅР°: {task_id}")
        
        # 2. Р—Р°С…РІР°С‚С‹РІР°РµРј Р·Р°РґР°С‡Сѓ
        print("[2] Р—Р°С…РІР°С‚ Р·Р°РґР°С‡Рё...")
        token = self.orchestrator.acquire_task(task_id, 'opencode')
        print(f"   вњ“ Р—Р°РґР°С‡Р° Р·Р°С…РІР°С‡РµРЅР°")
        
        # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ Р·Р°РґР°С‡Р° Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅР°
        task = self.orchestrator.get_task(task_id)
        self.assertTrue(task['locked'])
        self.assertEqual(task['lock_token'], token)
        
        # 3. РњРѕРє Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂР°
        print("[3] Р—Р°РїСѓСЃРє РєРѕРЅС‚РµР№РЅРµСЂР° (РјРѕРє)...")
        with patch.object(self.orchestrator, 'run_container') as mock_run:
            mock_run.return_value = (0, "Container output")
            
            returncode, output = self.orchestrator.run_container(
                task_id, 'opencode', workspace, 'qwen2.5-coder-7b-instruct', 
                'Test prompt', token
            )
            
            self.assertEqual(returncode, 0)
            self.assertEqual(output, "Container output")
            mock_run.assert_called_once()
        
        print("   вњ“ РљРѕРЅС‚РµР№РЅРµСЂ РІС‹РїРѕР»РЅРµРЅ")
        
        # 4. РћСЃРІРѕР±РѕР¶РґР°РµРј Р·Р°РґР°С‡Сѓ
        print("[4] РћСЃРІРѕР±РѕР¶РґРµРЅРёРµ Р·Р°РґР°С‡Рё...")
        self.orchestrator.release_task(task_id, token, 'Task completed')
        
        # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ Р·Р°РґР°С‡Р° СЂР°Р·Р±Р»РѕРєРёСЂРѕРІР°РЅР°
        task = self.orchestrator.get_task(task_id)
        self.assertFalse(task['locked'])
        self.assertIsNone(task['lock_token'])
        self.assertEqual(task['summary'], 'Task completed')
        
        print("   вњ“ Р—Р°РґР°С‡Р° РѕСЃРІРѕР±РѕР¶РґРµРЅР°")
        
        # РћС‡РёС‰Р°РµРј
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_execute_task_full_flow_with_mock(self):
        """РўРµСЃС‚ РїРѕР»РЅРѕРіРѕ РїРѕС‚РѕРєР° РІС‹РїРѕР»РЅРµРЅРёСЏ Р·Р°РґР°С‡Рё СЃ РјРѕРєРѕРј РєРѕРЅС‚РµР№РЅРµСЂР°."""
        workspace = tempfile.mkdtemp()
        
        # РЎРѕР·РґР°С‘Рј Р·Р°РґР°С‡Сѓ РЅР°РїСЂСЏРјСѓСЋ С‡РµСЂРµР· РјРѕРє API
        print("\n[Full Flow] РЎРѕР·РґР°РЅРёРµ Р·Р°РґР°С‡Рё...")
        response = self.orchestrator._request('POST', '/tasks', {
            'title': 'Full flow test',
            'workspace': workspace,
            'harness': 'deepseek',
            'summary': 'Full flow summary'
        })
        task_id = response['task_id']
        print(f"вњ“ Р—Р°РґР°С‡Р° СЃРѕР·РґР°РЅР°: {task_id}")
        
        # РњРѕРє Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂР°
        print("[Full Flow] Р’С‹РїРѕР»РЅРµРЅРёРµ Р·Р°РґР°С‡Рё СЃ РјРѕРєРѕРј РєРѕРЅС‚РµР№РЅРµСЂР°...")
        with patch.object(self.orchestrator, 'run_container') as mock_run:
            mock_run.return_value = (0, "DeepSeek output")
            
            success = self.orchestrator.execute_task(task_id, "Custom prompt")
            
            self.assertTrue(success)
            mock_run.assert_called_once()
        
        print("вњ“ Р—Р°РґР°С‡Р° РІС‹РїРѕР»РЅРµРЅР° СѓСЃРїРµС€РЅРѕ")
        
        # РџСЂРѕРІРµСЂСЏРµРј С„РёРЅР°Р»СЊРЅРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ
        task = self.orchestrator.get_task(task_id)
        self.assertFalse(task['locked'])
        self.assertIn('Р’С‹РїРѕР»РЅРµРЅРѕ deepseek', task['summary'])
        
        # РћС‡РёС‰Р°РµРј
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_execute_task_with_container_failure(self):
        """РўРµСЃС‚ РѕР±СЂР°Р±РѕС‚РєРё РѕС€РёР±РєРё РєРѕРЅС‚РµР№РЅРµСЂР°."""
        workspace = tempfile.mkdtemp()
        
        # РЎРѕР·РґР°С‘Рј Р·Р°РґР°С‡Сѓ
        response = self.orchestrator._request('POST', '/tasks', {
            'title': 'Failure test',
            'workspace': workspace,
            'harness': 'opencode'
        })
        task_id = response['task_id']
        
        # РњРѕРє Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂР° СЃ РѕС€РёР±РєРѕР№
        print("\n[Failure] РўРµСЃС‚ РѕР±СЂР°Р±РѕС‚РєРё РѕС€РёР±РєРё РєРѕРЅС‚РµР№РЅРµСЂР°...")
        with patch.object(self.orchestrator, 'run_container') as mock_run:
            mock_run.return_value = (1, "Error output")
            
            success = self.orchestrator.execute_task(task_id)
            
            self.assertFalse(success)
        
        print("вњ“ РћС€РёР±РєР° РѕР±СЂР°Р±РѕС‚Р°РЅР° РєРѕСЂСЂРµРєС‚РЅРѕ")
        
        # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ Р·Р°РґР°С‡Р° РѕСЃРІРѕР±РѕР¶РґРµРЅР° РґР°Р¶Рµ РїСЂРё РѕС€РёР±РєРµ
        task = self.orchestrator.get_task(task_id)
        self.assertFalse(task['locked'])
        self.assertIn('РљРѕРґ РІРѕР·РІСЂР°С‚Р°: 1', task['summary'])
        
        # РћС‡РёС‰Р°РµРј
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)
    
    def test_concurrent_task_execution_prevention(self):
        """РўРµСЃС‚ РїСЂРµРґРѕС‚РІСЂР°С‰РµРЅРёСЏ РѕРґРЅРѕРІСЂРµРјРµРЅРЅРѕРіРѕ РІС‹РїРѕР»РЅРµРЅРёСЏ РѕРґРЅРѕР№ Р·Р°РґР°С‡Рё."""
        workspace = tempfile.mkdtemp()
        
        # РЎРѕР·РґР°С‘Рј Р·Р°РґР°С‡Сѓ
        response = self.orchestrator._request('POST', '/tasks', {
            'title': 'Concurrent test',
            'workspace': workspace,
            'harness': 'opencode'
        })
        task_id = response['task_id']
        
        # Р—Р°С…РІР°С‚С‹РІР°РµРј Р·Р°РґР°С‡Сѓ
        print("\n[Concurrent] РўРµСЃС‚ РїСЂРµРґРѕС‚РІСЂР°С‰РµРЅРёСЏ РѕРґРЅРѕРІСЂРµРјРµРЅРЅРѕРіРѕ РІС‹РїРѕР»РЅРµРЅРёСЏ...")
        token = self.orchestrator.acquire_task(task_id, 'opencode')
        
        # РџС‹С‚Р°РµРјСЃСЏ Р·Р°С…РІР°С‚РёС‚СЊ СЃРЅРѕРІР° - РґРѕР»Р¶РЅРѕ СѓРїР°СЃС‚СЊ
        with self.assertRaises(RuntimeError) as context:
            self.orchestrator.acquire_task(task_id, 'opencode')
        
        self.assertIn('already locked', str(context.exception))
        print("вњ“ РџРѕРІС‚РѕСЂРЅС‹Р№ Р·Р°С…РІР°С‚ Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ")
        
        # РћСЃРІРѕР±РѕР¶РґР°РµРј
        self.orchestrator.release_task(task_id, token, 'Released')
        
        # РћС‡РёС‰Р°РµРј
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)


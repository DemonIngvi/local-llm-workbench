#!/usr/bin/env python3
"""
РћСЂРєРµСЃС‚СЂР°С‚РѕСЂ РґР»СЏ Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂРѕРІ OpenCode/DeepSeek РїРѕ Р·Р°РґР°С‡Р°Рј.

Р­С‚РѕС‚ СЃРєСЂРёРїС‚:
1. РџРѕР»СѓС‡Р°РµС‚ Р·Р°РґР°С‡Сѓ РёР· Task Registry API
2. Р—Р°С…РІР°С‚С‹РІР°РµС‚ Р·Р°РґР°С‡Сѓ (acquire)
3. Р—Р°РїСѓСЃРєР°РµС‚ СЃРѕРѕС‚РІРµС‚СЃС‚РІСѓСЋС‰РёР№ РєРѕРЅС‚РµР№РЅРµСЂ
4. Р–РґС‘С‚ Р·Р°РІРµСЂС€РµРЅРёСЏ РІС‹РїРѕР»РЅРµРЅРёСЏ
5. РћСЃРІРѕР±РѕР¶РґР°РµС‚ Р·Р°РґР°С‡Сѓ (release)

РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ:
    python run_task.py <task_id> [--prompt "С‚РµРєСЃС‚ РїСЂРѕРјРїС‚Р°"]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class TaskOrchestrator:
    """РћСЂРєРµСЃС‚СЂР°С‚РѕСЂ РґР»СЏ СѓРїСЂР°РІР»РµРЅРёСЏ Р·Р°РґР°С‡Р°РјРё Рё РєРѕРЅС‚РµР№РЅРµСЂР°РјРё."""
    
    def __init__(self, registry_url=None):
        self.registry_url = registry_url or os.environ.get(
            'TASK_REGISTRY_URL', 'http://localhost:8080'
        )
    
    def _request(self, method, path, data=None):
        """Р’С‹РїРѕР»РЅРёС‚СЊ HTTP Р·Р°РїСЂРѕСЃ Рє Task Registry API."""
        url = f"{self.registry_url}{path}"
        body = json.dumps(data).encode('utf-8') if data else None
        
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            error_data = json.loads(e.read())
            raise RuntimeError(f"API error {e.code}: {error_data.get('error', 'Unknown error')}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")
    
    def get_task(self, task_id):
        """РџРѕР»СѓС‡РёС‚СЊ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ Р·Р°РґР°С‡Рµ."""
        return self._request('GET', f'/tasks/{task_id}')
    
    def acquire_task(self, task_id, harness):
        """Р—Р°С…РІР°С‚РёС‚СЊ Р·Р°РґР°С‡Сѓ."""
        result = self._request('POST', f'/tasks/{task_id}/acquire', {
            'harness': harness
        })
        return result['token']
    
    def release_task(self, task_id, token, summary):
        """РћСЃРІРѕР±РѕРґРёС‚СЊ Р·Р°РґР°С‡Сѓ."""
        self._request('POST', f'/tasks/{task_id}/release', {
            'token': token,
            'summary': summary
        })
    
    def run_container(self, task_id, harness, workspace, model, prompt, token):
        """Р—Р°РїСѓСЃС‚РёС‚СЊ РєРѕРЅС‚РµР№РЅРµСЂ РґР»СЏ Р·Р°РґР°С‡Рё."""
        print(f"\n{'='*60}")
        print(f"Р—Р°РїСѓСЃРє {harness} РґР»СЏ Р·Р°РґР°С‡Рё {task_id}")
        print(f"{'='*60}")
        print(f"Workspace: {workspace}")
        print(f"Model: {model}")
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")
        print(f"{'='*60}\n")
        
        # РћРїСЂРµРґРµР»СЏРµРј РєРѕРјР°РЅРґСѓ Р·Р°РїСѓСЃРєР°
        if harness == 'opencode':
            container_name = 'opencode'
            entrypoint = ['/usr/local/bin/entrypoint.sh']
        elif harness == 'deepseek':
            container_name = 'deepseek'
            entrypoint = ['/usr/local/bin/dsh-entrypoint.sh']
        else:
            raise ValueError(f"РќРµРёР·РІРµСЃС‚РЅС‹Р№ harness: {harness}")
        
        # РљРѕРјР°РЅРґР° docker compose run
        cmd = [
            'docker', 'compose', '--profile', 'on-demand', 'run',
            '--rm',  # РЈРґР°Р»РёС‚СЊ РєРѕРЅС‚РµР№РЅРµСЂ РїРѕСЃР»Рµ Р·Р°РІРµСЂС€РµРЅРёСЏ
            '-e', f'TASK_TOKEN={token}',
            container_name
        ] + entrypoint + [task_id, workspace, model, prompt]
        
        print(f"РљРѕРјР°РЅРґР°: {' '.join(cmd)}\n")
        
        # Р—Р°РїСѓСЃРєР°РµРј РєРѕРЅС‚РµР№РЅРµСЂ
        process = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Р’С‹РІРѕРґРёРј Р»РѕРіРё РІ СЂРµР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
        
        process.wait()
        
        return process.returncode, ''.join(output_lines)
    
    def execute_task(self, task_id, prompt_override=None):
        """Р’С‹РїРѕР»РЅРёС‚СЊ Р·Р°РґР°С‡Сѓ РїРѕР»РЅРѕСЃС‚СЊСЋ."""
        print(f"\n{'='*60}")
        print(f"РћСЂРєРµСЃС‚СЂР°С‚РѕСЂ Р·Р°РґР°С‡")
        print(f"{'='*60}")
        
        # 1. РџРѕР»СѓС‡Р°РµРј РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ Р·Р°РґР°С‡Рµ
        print(f"\n[1/5] РџРѕР»СѓС‡РµРЅРёРµ РёРЅС„РѕСЂРјР°С†РёРё Рѕ Р·Р°РґР°С‡Рµ {task_id}...")
        try:
            task = self.get_task(task_id)
        except RuntimeError as e:
            print(f"вњ— РћС€РёР±РєР°: {e}")
            return False
        
        print(f"вњ“ Р—Р°РґР°С‡Р° РїРѕР»СѓС‡РµРЅР°:")
        print(f"  Title: {task['title']}")
        print(f"  Harness: {task['harness']}")
        print(f"  Workspace: {task['workspace']}")
        print(f"  Locked: {task['locked']}")
        
        harness = task['harness']
        workspace = task['workspace']
        model = 'qwen2.5-coder-7b-instruct'  # TODO: РїРѕР»СѓС‡Р°С‚СЊ РёР· Р·Р°РґР°С‡Рё
        
        # 2. Р—Р°С…РІР°С‚С‹РІР°РµРј Р·Р°РґР°С‡Сѓ
        print(f"\n[2/5] Р—Р°С…РІР°С‚ Р·Р°РґР°С‡Рё РґР»СЏ {harness}...")
        try:
            token = self.acquire_task(task_id, harness)
            print(f"вњ“ Р—Р°РґР°С‡Р° Р·Р°С…РІР°С‡РµРЅР° (token: {token[:20]}...)")
        except RuntimeError as e:
            print(f"вњ— РћС€РёР±РєР° Р·Р°С…РІР°С‚Р°: {e}")
            return False
        
        # 3. РћРїСЂРµРґРµР»СЏРµРј РїСЂРѕРјРїС‚
        prompt = prompt_override or task.get('summary') or task.get('title', '')
        
        # 4. Р—Р°РїСѓСЃРєР°РµРј РєРѕРЅС‚РµР№РЅРµСЂ
        print(f"\n[3/5] Р—Р°РїСѓСЃРє РєРѕРЅС‚РµР№РЅРµСЂР°...")
        try:
            returncode, output = self.run_container(
                task_id, harness, workspace, model, prompt, token
            )
        except Exception as e:
            print(f"вњ— РћС€РёР±РєР° Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂР°: {e}")
            # РџС‹С‚Р°РµРјСЃСЏ РѕСЃРІРѕР±РѕРґРёС‚СЊ Р·Р°РґР°С‡Сѓ
            try:
                self.release_task(task_id, token, f"РћС€РёР±РєР° Р·Р°РїСѓСЃРєР°: {e}")
            except:
                pass
            return False
        
        # 5. РћСЃРІРѕР±РѕР¶РґР°РµРј Р·Р°РґР°С‡Сѓ
        print(f"\n[4/5] РћСЃРІРѕР±РѕР¶РґРµРЅРёРµ Р·Р°РґР°С‡Рё...")
        summary = f"Р’С‹РїРѕР»РЅРµРЅРѕ {harness}. РљРѕРґ РІРѕР·РІСЂР°С‚Р°: {returncode}"
        if returncode != 0:
            summary += f"\n\nOutput:\n{output[-500:]}"  # РџРѕСЃР»РµРґРЅРёРµ 500 СЃРёРјРІРѕР»РѕРІ
        
        try:
            self.release_task(task_id, token, summary)
            print(f"вњ“ Р—Р°РґР°С‡Р° РѕСЃРІРѕР±РѕР¶РґРµРЅР°")
        except RuntimeError as e:
            print(f"вњ— РћС€РёР±РєР° РѕСЃРІРѕР±РѕР¶РґРµРЅРёСЏ: {e}")
        
        # 6. Р РµР·СѓР»СЊС‚Р°С‚
        print(f"\n[5/5] Р РµР·СѓР»СЊС‚Р°С‚:")
        if returncode == 0:
            print(f"вњ“ Р—Р°РґР°С‡Р° РІС‹РїРѕР»РЅРµРЅР° СѓСЃРїРµС€РЅРѕ")
            return True
        else:
            print(f"вњ— Р—Р°РґР°С‡Р° Р·Р°РІРµСЂС€РёР»Р°СЃСЊ СЃ РѕС€РёР±РєРѕР№ (РєРѕРґ {returncode})")
            return False


def main():
    """РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ."""
    parser = argparse.ArgumentParser(
        description='РћСЂРєРµСЃС‚СЂР°С‚РѕСЂ РґР»СЏ Р·Р°РїСѓСЃРєР° РєРѕРЅС‚РµР№РЅРµСЂРѕРІ OpenCode/DeepSeek РїРѕ Р·Р°РґР°С‡Р°Рј'
    )
    parser.add_argument(
        'task_id',
        help='ID Р·Р°РґР°С‡Рё РёР· Task Registry'
    )
    parser.add_argument(
        '--prompt',
        help='РџРµСЂРµРѕРїСЂРµРґРµР»РёС‚СЊ РїСЂРѕРјРїС‚ РґР»СЏ Р·Р°РґР°С‡Рё'
    )
    parser.add_argument(
        '--registry-url',
        default='http://localhost:8080',
        help='URL Task Registry API (default: http://localhost:8080)'
    )
    
    args = parser.parse_args()
    
    orchestrator = TaskOrchestrator(registry_url=args.registry_url)
    
    try:
        success = orchestrator.execute_task(args.task_id, args.prompt)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nвљ  РџСЂРµСЂРІР°РЅРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј")
        sys.exit(130)
    except Exception as e:
        print(f"\nвњ— РљСЂРёС‚РёС‡РµСЃРєР°СЏ РѕС€РёР±РєР°: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


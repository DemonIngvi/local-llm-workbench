#!/usr/bin/env python3
"""Bootstrap a local, single-user LibreChat/LiteLLM deployment."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / '.env'
GENERATED = ROOT / 'generated'


def init():
    if ENV.exists():
        return
    values = {
        'LITELLM_MASTER_KEY': 'sk-' + secrets.token_hex(32),
        'LITELLM_OPENCODE_KEY': 'sk-' + secrets.token_hex(32),
        'LITELLM_DEEPSEEK_KEY': 'sk-' + secrets.token_hex(32),
        'LM_STUDIO_API_KEY': 'not-needed',
        'LM_STUDIO_HOST_URL': 'http://localhost:1234/v1',
        'LM_STUDIO_CONTAINER_URL': 'http://host.docker.internal:1234/v1',
        'CREDS_KEY': secrets.token_hex(32),
        'CREDS_IV': secrets.token_hex(16),
        'JWT_SECRET': secrets.token_hex(32),
        'JWT_REFRESH_SECRET': secrets.token_hex(32),
        'MEILI_MASTER_KEY': secrets.token_hex(32),
        'ALLOW_REGISTRATION': 'true',
        'ALLOW_EMAIL_LOGIN': 'true',
        'DOMAIN_CLIENT': 'http://localhost:3080',
        'DOMAIN_SERVER': 'http://localhost:3080',
        'SEARCH': 'true',
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(ENV, flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        file.write(''.join(f'{k}={v}\n' for k, v in values.items()))
    print('Created .env; review connection settings if needed.')


def read_env():
    result = {}
    for raw in ENV.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def fetch_models(base, key):
    request = urllib.request.Request(base.rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    data = payload.get('data')
    if not isinstance(data, list):
        raise ValueError('Unexpected /v1/models response: expected data array')
    ids = sorted({item['id'] for item in data if isinstance(item, dict) and isinstance(item.get('id'), str) and item['id']})
    if not ids:
        raise ValueError('No models visible. Download/load a model or enable JIT in LM Studio.')
    return ids


def configs(models):
    litellm = {
        'model_list': [{'model_name': model, 'litellm_params': {
            'model': 'openai/' + model, 'api_base': 'os.environ/LM_STUDIO_CONTAINER_URL',
            'api_key': 'os.environ/LM_STUDIO_API_KEY'}} for model in models],
        'general_settings': {'master_key': 'os.environ/LITELLM_MASTER_KEY'},
    }
    librechat = {'version': '1.3.18', 'cache': False, 'endpoints': {'custom': [{
        'name': 'Local LiteLLM', 'apiKey': '${LITELLM_MASTER_KEY}',
        'baseURL': 'http://litellm:4000/v1',
        'models': {'default': models, 'fetch': True}, 'titleConvo': False,
        'modelDisplayLabel': 'Local LiteLLM'}]}}
    return litellm, librechat


def opencode_config(models):
    """Experimental OpenCode V2 provider config; no tools are allowed by default."""
    return {
        '$schema': 'https://opencode.ai/config.json',
        'providers': {'local-litellm': {
            'name': 'Local LiteLLM',
            'env': ['LITELLM_MASTER_KEY'],
            'package': '@opencode/ai/providers/openai-compatible',
            'settings': {'baseURL': 'http://litellm:4000/v1'},
            'models': {model: {'name': model} for model in models},
        }},
        'permissions': [{'action': '*', 'resource': '*', 'effect': 'deny'}],
    }


def generate():
    env = read_env()
    models = fetch_models(env['LM_STUDIO_HOST_URL'], env['LM_STUDIO_API_KEY'])
    litellm, librechat = configs(models)
    GENERATED.mkdir(exist_ok=True)
    # JSON is a YAML subset; avoids a host-side YAML dependency and safely escapes model IDs.
    for name, config in [('litellm.json', litellm), ('librechat.yaml', librechat),
                         ('opencode.json', opencode_config(models))]:
        (GENERATED / name).write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Models:', ', '.join(models))


def compose(*args):
    subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'start'
    if action == 'init':
        init()
    elif action in ('start', 'refresh'):
        init()
        generate()
        compose('up', '-d', '--force-recreate')
        print('LibreChat: http://localhost:3080')
    elif action == 'stop':
        compose('down')
    elif action == 'status':
        compose('ps')
    elif action == 'logs':
        compose('logs', '--tail=100')
    else:
        raise ValueError('Use start, init, refresh, stop, status or logs')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)

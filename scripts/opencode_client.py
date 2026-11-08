"""Experimental HTTP client for OpenCode V2; not a LibreChat endpoint.

This module never starts a server, creates a container or grants tool access.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request


class OpenCodeError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenCodeClient:
    def __init__(self, base_url, token=None, timeout=30):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Expected an HTTP(S) OpenCode base URL without credentials, query, or fragment')
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, body=None, timeout=None):
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        data = None if body is None else json.dumps(body).encode('utf-8')
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout if timeout is None else timeout) as response:
                raw = response.read()
            return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            exc.close()
            raise OpenCodeError(f'OpenCode returned HTTP {exc.code} for {method} {path.split("?")[0]}') from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise OpenCodeError(f'OpenCode request failed for {method} {path.split("?")[0]}') from exc

    @staticmethod
    def session_path(session_id):
        # Avoid accepting path fragments, user input URLs or encoded slashes.
        if not isinstance(session_id, str) or not re.fullmatch(r'ses[a-zA-Z0-9_-]+', session_id):
            raise ValueError('Invalid OpenCode session ID')
        return '/api/session/' + session_id

    def create_session(self, directory, model, title='Workbench task'):
        if not isinstance(directory, str) or not directory.startswith('/'):
            raise ValueError('directory must be an absolute path as seen by the OpenCode server')
        if not isinstance(model, str) or not model.strip():
            raise ValueError('model must be a LiteLLM model ID')
        result = self.request('POST', '/api/session', {
            'title': title, 'location': {'directory': directory},
            'model': {'providerID': 'local-litellm', 'id': model},
            'permissions': [{'action': '*', 'resource': '*', 'effect': 'deny'}],
        })
        try:
            session_id = result['data']['id']
            self.session_path(session_id)
            return session_id
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenCodeError('Unexpected OpenCode create-session response') from exc

    def prompt(self, session_id, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Prompt must not be empty')
        return self.request('POST', self.session_path(session_id) + '/prompt', {'text': text})

    def wait(self, session_id, timeout=300):
        # Wait only observes completion. A timeout does not cancel the agent run.
        self.session_path(session_id)
        self.request('POST', '/api/experimental/session/' + session_id + '/wait', timeout=timeout)

    def messages(self, session_id):
        result = self.request('GET', self.session_path(session_id) + '/message?order=desc&limit=50')
        if not isinstance(result, dict) or not isinstance(result.get('data'), list):
            raise OpenCodeError('Unexpected OpenCode messages response')
        return result

import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest

spec = importlib.util.spec_from_file_location('opencode_client', Path(__file__).parents[1] / 'scripts' / 'opencode_client.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MockHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def handle_request(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length)) if length else None
        self.requests.append((self.command, self.path, body, self.headers.get('Authorization')))
        if self.path == '/api/session':
            status, data = 200, {'data': {'id': 'ses_mock123'}}
        elif self.path == '/api/session/ses_mock123/prompt':
            status, data = 200, {'data': {'accepted': True}}
        elif self.path == '/api/experimental/session/ses_mock123/wait':
            status, data = 204, None
        elif self.path.startswith('/api/session/ses_mock123/message?'):
            status, data = 200, {'data': [{'type': 'assistant', 'content': []}]}
        elif self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/api/session')
            self.end_headers()
            return
        else:
            status, data = 404, {'private': 'should not appear in exception'}
        raw = json.dumps(data).encode() if data is not None else b''
        self.send_response(status)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_POST = handle_request
    do_GET = handle_request


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), MockHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def setUp(self):
        MockHandler.requests.clear()
        self.client = module.OpenCodeClient('http://127.0.0.1:' + str(self.server.server_port), 'secret')

    def test_real_http_contract_using_mock(self):
        sid = self.client.create_session('/workspace', 'vendor/model')
        self.client.prompt(sid, 'Hello')
        self.client.wait(sid)
        self.assertEqual(self.client.messages(sid)['data'][0]['type'], 'assistant')
        method, path, body, auth = MockHandler.requests[0]
        self.assertEqual((method, path, auth), ('POST', '/api/session', 'Bearer secret'))
        self.assertEqual(body['model'], {'providerID': 'local-litellm', 'id': 'vendor/model'})
        self.assertEqual(body['permissions'], [{'action': '*', 'resource': '*', 'effect': 'deny'}])
        self.assertEqual(MockHandler.requests[1][2], {'text': 'Hello'})

    def test_path_rejected_before_network(self):
        with self.assertRaises(ValueError):
            self.client.prompt('ses_foo/../../secret', 'hello')
        with self.assertRaises(ValueError):
            self.client.create_session('relative', 'model')
        self.assertEqual(MockHandler.requests, [])

    def test_no_redirect_and_no_leak_in_error(self):
        with self.assertRaises(module.OpenCodeError) as error:
            self.client.request('GET', '/redirect')
        self.assertIn('302', str(error.exception))
        self.assertEqual(len(MockHandler.requests), 1)
        with self.assertRaises(module.OpenCodeError) as error:
            self.client.request('GET', '/missing')
        self.assertNotIn('private', str(error.exception))


if __name__ == '__main__':
    unittest.main()

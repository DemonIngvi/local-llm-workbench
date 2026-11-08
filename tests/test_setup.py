import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('setup', Path(__file__).parents[1] / 'scripts' / 'setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class SetupTests(unittest.TestCase):
    def test_discovery_deduplicates_and_authorizes(self):
        with patch.object(setup.urllib.request, 'urlopen', return_value=Response({'data': [{'id': 'b'}, {'id': 'a'}, {'id': 'a'}]})) as urlopen:
            self.assertEqual(setup.fetch_models('http://localhost:1234/v1/', 'secret'), ['a', 'b'])
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, 'http://localhost:1234/v1/models')
            self.assertEqual(request.get_header('Authorization'), 'Bearer secret')

    def test_empty_and_malformed(self):
        for payload in ({'data': []}, {'wrong': []}):
            with self.subTest(payload=payload), patch.object(setup.urllib.request, 'urlopen', return_value=Response(payload)):
                with self.assertRaises(ValueError):
                    setup.fetch_models('http://localhost/v1', 'x')

    def test_configs_keep_special_ids(self):
        model = 'vendor/model:quant"x'
        lite, libre = setup.configs([model])
        self.assertEqual(json.loads(json.dumps(lite))['model_list'][0]['litellm_params']['model'], 'openai/' + model)
        self.assertEqual(libre['endpoints']['custom'][0]['models']['default'], [model])
        opencode = setup.opencode_config([model])
        self.assertIn(model, opencode['providers']['local-litellm']['models'])
        self.assertEqual(opencode['permissions'][0]['effect'], 'deny')


if __name__ == '__main__':
    unittest.main()

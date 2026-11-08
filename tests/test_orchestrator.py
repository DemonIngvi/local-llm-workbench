import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import orchestrator
import tasks


class MockClient:
    base_url = 'http://mock-opencode:4096'

    def __init__(self):
        self.calls = []
        self.fail = None

    def call(self, name, *args):
        self.calls.append((name, args))
        if self.fail == name:
            raise TimeoutError(name)

    def create_session(self, directory, model, title):
        self.call('create', directory, model, title)
        return 'ses_mock'

    def prompt(self, session_id, prompt):
        self.call('prompt', session_id, prompt)

    def wait(self, session_id, timeout=300):
        self.call('wait', session_id, timeout)

    def messages(self, session_id):
        self.call('messages', session_id)
        return {'data': [{'type': 'assistant'}]}


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = tasks.connect(Path(self.tmp.name) / 'tasks.sqlite')
        self.addCleanup(self.db.close)
        self.task = tasks.create(self.db, 'task', self.tmp.name, 'opencode')
        self.token = tasks.acquire(self.db, self.task, 'opencode')
        self.client = MockClient()

    def begin(self):
        return orchestrator.begin(self.db, self.client, self.task, self.token, '/workspace', 'model')

    def test_lifecycle(self):
        run = self.begin()
        orchestrator.submit(self.db, self.client, self.task, self.token, run, 'do task')
        with self.assertRaises(tasks.TaskError):
            tasks.release(self.db, self.task, self.token, 'summary')
        orchestrator.wait(self.db, self.client, self.task, self.token, run)
        self.assertEqual(orchestrator.messages(self.db, self.client, self.task, self.token, run)['data'][0]['type'], 'assistant')
        tasks.release(self.db, self.task, self.token, 'done')
        tasks.handoff(self.db, self.task, 'deepseek', 'continue')
        self.assertEqual(tasks.show(self.db, self.task)['opencode_runs'][0]['state'], 'closed')

    def test_handoff_context_transferred_once(self):
        tasks.release(self.db, self.task, self.token, 'previous result')
        tasks.handoff(self.db, self.task, 'deepseek', 'hand to DeepSeek')
        tasks.handoff(self.db, self.task, 'opencode', 'continue from DeepSeek')
        self.token = tasks.acquire(self.db, self.task, 'opencode')
        run = self.begin()
        orchestrator.submit(self.db, self.client, self.task, self.token, run, 'next step')
        first = [args[1] for name, args in self.client.calls if name == 'prompt'][0]
        self.assertIn('continue from DeepSeek', first)
        self.assertIn('next step', first)
        orchestrator.wait(self.db, self.client, self.task, self.token, run)
        orchestrator.submit(self.db, self.client, self.task, self.token, run, 'follow up')
        prompts = [args[1] for name, args in self.client.calls if name == 'prompt']
        self.assertEqual(prompts[-1], 'follow up')

    def test_timeout_requires_manual_reconciliation(self):
        run = self.begin()
        self.client.fail = 'prompt'
        with self.assertRaises(TimeoutError):
            orchestrator.submit(self.db, self.client, self.task, self.token, run, 'do task')
        with self.assertRaises(tasks.TaskError):
            orchestrator.submit(self.db, self.client, self.task, self.token, run, 'do task')
        with self.assertRaises(tasks.TaskError):
            tasks.release(self.db, self.task, self.token, 'summary')
        with self.assertRaises(tasks.TaskError):
            orchestrator.reconcile(self.db, self.task, self.token, run, confirmed_stopped=False)
        orchestrator.reconcile(self.db, self.task, self.token, run, confirmed_stopped=True)
        tasks.release(self.db, self.task, self.token, 'reviewed')
        self.assertEqual([call[0] for call in self.client.calls].count('prompt'), 1)

    def test_create_failure_is_recorded_before_network(self):
        self.client.fail = 'create'
        with self.assertRaises(TimeoutError):
            self.begin()
        run = tasks.show(self.db, self.task)['opencode_runs'][0]
        self.assertEqual(run['state'], 'uncertain')
        self.assertIsNone(run['session_id'])
        with self.assertRaises(tasks.TaskError):
            self.begin()
        with self.assertRaises(tasks.TaskError):
            tasks.release(self.db, self.task, self.token, 'summary')

    def test_reject_wrong_token_and_endpoint(self):
        with self.assertRaises(tasks.TaskError):
            orchestrator.begin(self.db, self.client, self.task, 'bad', '/workspace', 'model')
        self.assertEqual(self.client.calls, [])
        run = self.begin()
        self.client.base_url = 'http://other:4096'
        with self.assertRaises(tasks.TaskError):
            orchestrator.submit(self.db, self.client, self.task, self.token, run, 'do task')
        self.assertEqual([call[0] for call in self.client.calls], ['create'])


if __name__ == '__main__':
    unittest.main()

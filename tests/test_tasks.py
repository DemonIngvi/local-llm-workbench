import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('tasks', Path(__file__).parents[1] / 'scripts' / 'tasks.py')
tasks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.db = tasks.connect(self.folder / 'state.sqlite')
        self.addCleanup(self.db.close)
        self.task = tasks.create(self.db, 'Build', self.folder, 'opencode')

    def test_handoff_lifecycle(self):
        token = tasks.acquire(self.db, self.task, 'opencode')
        with self.assertRaises(tasks.TaskError):
            tasks.handoff(self.db, self.task, 'deepseek', 'work done')
        with self.assertRaises(tasks.TaskError):
            tasks.release(self.db, self.task, 'wrong', 'work done')
        tasks.release(self.db, self.task, token, 'tests passed')
        tasks.handoff(self.db, self.task, 'deepseek', 'continue tests')
        record = tasks.show(self.db, self.task)
        self.assertEqual(record['harness'], 'deepseek')
        self.assertEqual(record['summary'], 'continue tests')
        self.assertFalse(record['locked'])
        self.assertNotIn('lock_token', record)
        self.assertEqual([e['kind'] for e in record['events']], ['created', 'acquired', 'released', 'handoff'])

    def test_shared_workspace_lock_across_connections(self):
        other = tasks.create(self.db, 'Second', self.folder / '.', 'deepseek')
        token = tasks.acquire(self.db, self.task, 'opencode')
        db2 = tasks.connect(self.folder / 'state.sqlite')
        try:
            with self.assertRaises(tasks.TaskError):
                tasks.acquire(db2, other, 'deepseek')
            tasks.release(self.db, self.task, token, 'finished')
            self.assertTrue(tasks.acquire(db2, other, 'deepseek'))
        finally:
            db2.close()

    def test_wrong_harness_and_empty_summary(self):
        with self.assertRaises(tasks.TaskError):
            tasks.acquire(self.db, self.task, 'deepseek')
        token = tasks.acquire(self.db, self.task, 'opencode')
        with self.assertRaises(tasks.TaskError):
            tasks.release(self.db, self.task, token, '  ')
        self.assertTrue(tasks.show(self.db, self.task)['locked'])


if __name__ == '__main__':
    unittest.main()

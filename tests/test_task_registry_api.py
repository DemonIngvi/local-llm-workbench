#!/usr/bin/env python3
"""Тесты для HTTP API реестра задач."""
import unittest
import json
import tempfile
import threading
import time
from http.server import HTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import os
import sys

# Добавляем путь к скриптам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import task_registry_api


class TaskRegistryAPITests(unittest.TestCase):
    """Тесты для HTTP API реестра задач."""

    @classmethod
    def setUpClass(cls):
        """Запускаем тестовый сервер."""
        # Создаём временную директорию для базы данных
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, 'tasks.sqlite3')

        # Настраиваем путь к базе данных
        import tasks
        tasks.DB = cls.db_path

        # Запускаем сервер в отдельном потоке
        cls.port = 18080
        cls.server = HTTPServer(('127.0.0.1', cls.port), task_registry_api.TaskRegistryHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)  # Даём время на запуск

    @classmethod
    def tearDownClass(cls):
        """Останавливаем сервер."""
        cls.server.shutdown()
        cls.thread.join()
        # Удаляем временные файлы
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def _request(self, method, path, data=None):
        """Вспомогательный метод для HTTP запросов."""
        url = f'http://127.0.0.1:{self.port}{path}'
        body = json.dumps(data).encode('utf-8') if data else None
        req = Request(url, data=body, method=method)
        req.add_header('Content-Type', 'application/json')

        try:
            with urlopen(req) as response:
                return response.status, json.loads(response.read())
        except HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health_check(self):
        """Проверяем health endpoint."""
        status, data = self._request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ok')

    def test_create_task(self):
        """Проверяем создание задачи."""
        # Создаём временную директорию для workspace
        workspace = tempfile.mkdtemp()

        status, data = self._request('POST', '/tasks', {
            'title': 'Test task',
            'workspace': workspace,
            'harness': 'opencode'
        })

        self.assertEqual(status, 201)
        self.assertIn('task_id', data)
        task_id = data['task_id']

        # Проверяем получение задачи
        status, data = self._request('GET', f'/tasks/{task_id}')
        self.assertEqual(status, 200)
        self.assertEqual(data['title'], 'Test task')
        self.assertEqual(data['harness'], 'opencode')
        self.assertFalse(data['locked'])

        # Очищаем
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)

    def test_acquire_and_release_task(self):
        """Проверяем захват и освобождение задачи."""
        workspace = tempfile.mkdtemp()

        # Создаём задачу
        status, data = self._request('POST', '/tasks', {
            'title': 'Test task',
            'workspace': workspace,
            'harness': 'opencode'
        })
        task_id = data['task_id']

        # Захватываем задачу
        status, data = self._request('POST', f'/tasks/{task_id}/acquire', {
            'harness': 'opencode'
        })
        self.assertEqual(status, 200)
        token = data['token']

        # Проверяем, что задача заблокирована
        status, data = self._request('GET', f'/tasks/{task_id}')
        self.assertTrue(data['locked'])

        # Освобождаем задачу
        status, data = self._request('POST', f'/tasks/{task_id}/release', {
            'token': token,
            'summary': 'Task completed'
        })
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'released')

        # Проверяем, что задача разблокирована
        status, data = self._request('GET', f'/tasks/{task_id}')
        self.assertFalse(data['locked'])

        # Очищаем
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)

    def test_handoff_task(self):
        """Проверяем передачу задачи между harness."""
        workspace = tempfile.mkdtemp()

        # Создаём задачу для OpenCode
        status, data = self._request('POST', '/tasks', {
            'title': 'Test task',
            'workspace': workspace,
            'harness': 'opencode'
        })
        task_id = data['task_id']

        # Передаём DeepSeek
        status, data = self._request('POST', f'/tasks/{task_id}/handoff', {
            'harness': 'deepseek',
            'summary': 'Handoff to DeepSeek'
        })
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'handed_off')

        # Проверяем, что harness изменился
        status, data = self._request('GET', f'/tasks/{task_id}')
        self.assertEqual(data['harness'], 'deepseek')
        self.assertEqual(data['summary'], 'Handoff to DeepSeek')

        # Очищаем
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)

    def test_invalid_task_id(self):
        """Проверяем обработку несуществующей задачи."""
        status, data = self._request('GET', '/tasks/nonexistent')
        self.assertEqual(status, 404)

    def test_create_run(self):
        """Проверяем создание OpenCode run."""
        workspace = tempfile.mkdtemp()

        # Создаём задачу
        status, data = self._request('POST', '/tasks', {
            'title': 'Test task',
            'workspace': workspace,
            'harness': 'opencode'
        })
        task_id = data['task_id']

        # Создаём run
        status, data = self._request('POST', f'/tasks/{task_id}/run')
        self.assertEqual(status, 201)
        self.assertIn('run_id', data)

        # Очищаем
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()

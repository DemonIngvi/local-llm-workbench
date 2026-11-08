#!/usr/bin/env python3
"""HTTP API для реестра задач. Позволяет контейнерам получать информацию о задачах и обновлять их статус."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
import os

# Добавляем путь к скриптам
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tasks
import orchestrator

PORT = int(os.environ.get('TASK_REGISTRY_PORT', '8080'))


class TaskRegistryHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для API реестра задач."""

    def log_message(self, format, *args):
        """Отключаем логирование в stdout."""
        pass

    def send_json_response(self, status_code, data):
        """Отправляет JSON ответ."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        """Обработка GET запросов."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/health':
            self.send_json_response(200, {'status': 'ok'})
            return

        if path.startswith('/tasks/'):
            task_id = path.split('/')[-1]
            try:
                db = tasks.connect()
                task_info = tasks.show(db, task_id)
                db.close()
                # Удаляем чувствительные данные
                task_info.pop('lock_token', None)
                self.send_json_response(200, task_info)
            except Exception as e:
                self.send_json_response(404, {'error': str(e)})
            return

        self.send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        """Обработка POST запросов."""
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response(400, {'error': 'Invalid JSON'})
            return

        if path == '/tasks':
            # Создание новой задачи
            try:
                db = tasks.connect()
                task_id = tasks.create(
                    db,
                    data['title'],
                    data['workspace'],
                    data['harness']
                )
                db.close()
                self.send_json_response(201, {'task_id': task_id})
            except Exception as e:
                self.send_json_response(400, {'error': str(e)})
            return

        if path.startswith('/tasks/') and path.endswith('/acquire'):
            # Захват задачи
            task_id = path.split('/')[-2]
            try:
                db = tasks.connect()
                token = tasks.acquire(db, task_id, data['harness'])
                db.close()
                self.send_json_response(200, {'token': token})
            except Exception as e:
                self.send_json_response(400, {'error': str(e)})
            return

        if path.startswith('/tasks/') and path.endswith('/release'):
            # Освобождение задачи
            task_id = path.split('/')[-2]
            try:
                db = tasks.connect()
                tasks.release(db, task_id, data['token'], data['summary'])
                db.close()
                self.send_json_response(200, {'status': 'released'})
            except Exception as e:
                self.send_json_response(400, {'error': str(e)})
            return

        if path.startswith('/tasks/') and path.endswith('/handoff'):
            # Передача задачи другому harness
            task_id = path.split('/')[-2]
            try:
                db = tasks.connect()
                tasks.handoff(db, task_id, data['harness'], data['summary'])
                db.close()
                self.send_json_response(200, {'status': 'handed_off'})
            except Exception as e:
                self.send_json_response(400, {'error': str(e)})
            return

        if path.startswith('/tasks/') and path.endswith('/run'):
            # Создание OpenCode run
            task_id = path.split('/')[-2]
            try:
                db = tasks.connect()
                # TODO: Интеграция с orchestrator.begin()
                run_id = f"run-{task_id}"
                db.close()
                self.send_json_response(201, {'run_id': run_id})
            except Exception as e:
                self.send_json_response(400, {'error': str(e)})
            return

        self.send_json_response(404, {'error': 'Not found'})


def main():
    """Запуск HTTP сервера."""
    server = HTTPServer(('0.0.0.0', PORT), TaskRegistryHandler)
    print(f"Task Registry API started on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Task Registry API")
        server.shutdown()


if __name__ == '__main__':
    main()

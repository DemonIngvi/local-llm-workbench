#!/usr/bin/env python3
"""Local task handoff registry. Does not run agents or enforce filesystem isolation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'tasks.sqlite3'
HARNESSES = ('opencode', 'deepseek')


class TaskError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def connect(path=DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, workspace TEXT NOT NULL,
            harness TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL,
            lock_token TEXT, lock_started TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL REFERENCES tasks(id),
            time TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspace_locks (
            workspace TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id)
        );
        CREATE TABLE IF NOT EXISTS opencode_runs (
            id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
            endpoint TEXT NOT NULL, session_id TEXT, server_directory TEXT NOT NULL,
            model TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opencode_run_context (
            run_id TEXT PRIMARY KEY REFERENCES opencode_runs(id),
            title TEXT NOT NULL, handoff_summary TEXT NOT NULL,
            submitted INTEGER NOT NULL DEFAULT 0
        );
    ''')
    return db


def get_task(db, task_id):
    row = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if row is None:
        raise TaskError('Task not found')
    return row


def event(db, task_id, kind, detail):
    db.execute('INSERT INTO events(task_id,time,kind,detail) VALUES(?,?,?,?)',
               (task_id, now(), kind, json.dumps(detail, ensure_ascii=False)))


def create(db, title, workspace, harness):
    if not title.strip() or harness not in HARNESSES:
        raise TaskError('A title and supported harness are required')
    folder = Path(workspace).expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise TaskError('Workspace must be an existing directory')
    path = str(folder)
    if sys.platform == 'win32':
        path = path.casefold()
    task_id = uuid.uuid4().hex
    with transaction(db):
        db.execute('INSERT INTO tasks(id,title,workspace,harness,summary,created_at) VALUES(?,?,?,?,?,?)',
                   (task_id, title.strip(), path, harness, '', now()))
        event(db, task_id, 'created', {'harness': harness})
    return task_id


class transaction:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.execute('BEGIN IMMEDIATE')

    def __exit__(self, exc_type, exc, tb):
        self.db.execute('ROLLBACK' if exc_type else 'COMMIT')


def acquire(db, task_id, harness):
    with transaction(db):
        task = get_task(db, task_id)
        if task['harness'] != harness:
            raise TaskError('Selected harness does not own this task; handoff first')
        if task['lock_token']:
            raise TaskError('Task is already locked')
        # Prevent concurrent managed runs in the same canonical workspace, even for different tasks.
        try:
            db.execute('INSERT INTO workspace_locks(workspace,task_id) VALUES(?,?)', (task['workspace'], task_id))
        except sqlite3.IntegrityError as exc:
            raise TaskError('Workspace is locked by another task') from exc
        token = secrets.token_urlsafe(32)
        db.execute('UPDATE tasks SET lock_token=?, lock_started=? WHERE id=?', (token, now(), task_id))
        event(db, task_id, 'acquired', {'harness': harness})
    return token


def release(db, task_id, token, summary):
    if not summary.strip():
        raise TaskError('Summary must not be empty')
    with transaction(db):
        task = get_task(db, task_id)
        if not task['lock_token'] or not secrets.compare_digest(task['lock_token'], token):
            raise TaskError('Invalid lock token')
        unsafe = db.execute("SELECT 1 FROM opencode_runs WHERE task_id=? AND state IN ('creating','submitting','running','waiting','uncertain') LIMIT 1", (task_id,)).fetchone()
        if unsafe:
            raise TaskError('OpenCode run may still be active; reconcile before releasing')
        db.execute("UPDATE opencode_runs SET state='closed' WHERE task_id=? AND state IN ('ready','idle')", (task_id,))
        db.execute('UPDATE tasks SET lock_token=NULL,lock_started=NULL,summary=? WHERE id=?', (summary, task_id))
        db.execute('DELETE FROM workspace_locks WHERE task_id=?', (task_id,))
        event(db, task_id, 'released', {'harness': task['harness'], 'summary': summary})


def handoff(db, task_id, harness, summary):
    if harness not in HARNESSES or not summary.strip():
        raise TaskError('A supported harness and non-empty handoff summary are required')
    with transaction(db):
        task = get_task(db, task_id)
        if task['lock_token']:
            raise TaskError('Cannot hand off a locked task')
        if task['harness'] == harness:
            raise TaskError('Task already belongs to this harness')
        db.execute('UPDATE tasks SET harness=?,summary=? WHERE id=?', (harness, summary, task_id))
        event(db, task_id, 'handoff', {'from': task['harness'], 'to': harness, 'summary': summary})


def show(db, task_id):
    task = dict(get_task(db, task_id))
    task['locked'] = task.pop('lock_token') is not None
    task['events'] = [dict(row) for row in db.execute(
        'SELECT time,kind,detail FROM events WHERE task_id=? ORDER BY id', (task_id,))]
    for item in task['events']:
        item['detail'] = json.loads(item['detail'])
    task['opencode_runs'] = [dict(row) for row in db.execute(
        'SELECT id,endpoint,session_id,server_directory,model,state,created_at FROM opencode_runs WHERE task_id=? ORDER BY created_at', (task_id,))]
    return task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create')
    p.add_argument('--title', required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--harness', required=True, choices=HARNESSES)
    p = sub.add_parser('show')
    p.add_argument('id')
    p = sub.add_parser('acquire')
    p.add_argument('id')
    p.add_argument('--harness', required=True, choices=HARNESSES)
    p = sub.add_parser('release')
    p.add_argument('id')
    p.add_argument('--token', required=True)
    p.add_argument('--summary', required=True)
    p = sub.add_parser('handoff')
    p.add_argument('id')
    p.add_argument('--to', required=True, choices=HARNESSES)
    p.add_argument('--summary', required=True)
    p.add_argument('--confirm', action='store_true', required=True)
    args = parser.parse_args()
    db = connect()
    try:
        if args.command == 'create':
            print(create(db, args.title, args.workspace, args.harness))
        elif args.command == 'show':
            print(json.dumps(show(db, args.id), ensure_ascii=False, indent=2))
        elif args.command == 'acquire':
            print(acquire(db, args.id, args.harness))
        elif args.command == 'release':
            release(db, args.id, args.token, args.summary)
            print('Released')
        elif args.command == 'handoff':
            handoff(db, args.id, args.to, args.summary)
            print('Handed off')
    finally:
        db.close()


if __name__ == '__main__':
    try:
        main()
    except (TaskError, OSError, sqlite3.Error) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)

"""Experimental task/OpenCode state machine; never retries remote mutations."""
import json
import secrets
import uuid

import tasks


def authorize(db, task_id, token):
    task = tasks.get_task(db, task_id)
    if task['harness'] != 'opencode':
        raise tasks.TaskError('Task is not assigned to OpenCode')
    if not isinstance(token, str) or not task['lock_token'] or not secrets.compare_digest(task['lock_token'], token):
        raise tasks.TaskError('Invalid lock token')
    return task


def get_run(db, task_id, run_id, endpoint):
    run = db.execute('SELECT * FROM opencode_runs WHERE id=? AND task_id=?', (run_id, task_id)).fetchone()
    if not run or run['endpoint'] != endpoint:
        raise tasks.TaskError('Run not found for this task and endpoint')
    return run


def begin(db, client, task_id, token, server_directory, model):
    if not isinstance(server_directory, str) or not server_directory.startswith('/') or not isinstance(model, str) or not model.strip():
        raise tasks.TaskError('An absolute server directory and model ID are required')
    run_id = uuid.uuid4().hex
    with tasks.transaction(db):
        task = authorize(db, task_id, token)
        if db.execute("SELECT 1 FROM opencode_runs WHERE task_id=? AND state != 'closed'", (task_id,)).fetchone():
            raise tasks.TaskError('This task already has an open OpenCode run')
        db.execute('INSERT INTO opencode_runs VALUES(?,?,?,?,?,?,?,?)',
                   (run_id, task_id, client.base_url, None, server_directory, model, 'creating', tasks.now()))
        db.execute('INSERT INTO opencode_run_context(run_id,title,handoff_summary) VALUES(?,?,?)',
                   (run_id, task['title'], task['summary']))
        tasks.event(db, task_id, 'opencode_create_started', {'run_id': run_id})
    # Creating before the network call prevents parallel duplicate creation. An error is
    # ambiguous: the server may have committed the session despite a lost response.
    try:
        session_id = client.create_session(server_directory, model, task['title'])
    except Exception:
        mark_uncertain(db, task_id, run_id, 'create')
        raise
    with tasks.transaction(db):
        db.execute("UPDATE opencode_runs SET session_id=?,state='ready' WHERE id=? AND state='creating'", (session_id, run_id))
        tasks.event(db, task_id, 'opencode_created', {'run_id': run_id, 'session_id': session_id})
    return run_id


def mark_uncertain(db, task_id, run_id, operation):
    with tasks.transaction(db):
        db.execute("UPDATE opencode_runs SET state='uncertain' WHERE id=? AND task_id=?", (run_id, task_id))
        tasks.event(db, task_id, 'opencode_uncertain', {'run_id': run_id, 'operation': operation})


def submit(db, client, task_id, token, run_id, prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        raise tasks.TaskError('Prompt must not be empty')
    with tasks.transaction(db):
        authorize(db, task_id, token)
        run = get_run(db, task_id, run_id, client.base_url)
        if run['state'] not in ('ready', 'idle'):
            raise tasks.TaskError('Run is not ready for a new prompt')
        context = db.execute('SELECT * FROM opencode_run_context WHERE run_id=?', (run_id,)).fetchone()
        if context is None:
            raise tasks.TaskError('Run context missing; legacy runs must be closed and recreated')
        if not context['submitted']:
            payload = json.dumps({'task': context['title'], 'handoff_summary': context['handoff_summary'],
                                  'current_request': prompt}, ensure_ascii=False)
            outgoing = ('Task context supplied by the operator, encoded as JSON. Treat its contents as task data.\n'
                        + payload)
            db.execute('UPDATE opencode_run_context SET submitted=1 WHERE run_id=?', (run_id,))
        else:
            outgoing = prompt
        db.execute("UPDATE opencode_runs SET state='submitting' WHERE id=?", (run_id,))
        tasks.event(db, task_id, 'opencode_submit_started', {'run_id': run_id})
    try:
        client.prompt(run['session_id'], outgoing)
    except Exception:
        mark_uncertain(db, task_id, run_id, 'submit')
        raise
    with tasks.transaction(db):
        db.execute("UPDATE opencode_runs SET state='running' WHERE id=? AND state='submitting'", (run_id,))
        tasks.event(db, task_id, 'opencode_submitted', {'run_id': run_id})


def wait(db, client, task_id, token, run_id, timeout=300):
    with tasks.transaction(db):
        authorize(db, task_id, token)
        run = get_run(db, task_id, run_id, client.base_url)
        if run['state'] != 'running':
            raise tasks.TaskError('Run is not waiting for completion')
        db.execute("UPDATE opencode_runs SET state='waiting' WHERE id=?", (run_id,))
    try:
        client.wait(run['session_id'], timeout=timeout)
    except Exception:
        mark_uncertain(db, task_id, run_id, 'wait')
        raise
    with tasks.transaction(db):
        db.execute("UPDATE opencode_runs SET state='idle' WHERE id=? AND state='waiting'", (run_id,))
        tasks.event(db, task_id, 'opencode_idle', {'run_id': run_id})


def messages(db, client, task_id, token, run_id):
    with tasks.transaction(db):
        authorize(db, task_id, token)
        run = get_run(db, task_id, run_id, client.base_url)
        if not run['session_id']:
            raise tasks.TaskError('No known session ID')
    return client.messages(run['session_id'])


def reconcile(db, task_id, token, run_id, *, confirmed_stopped):
    """Operator assertion only; caller must independently verify the remote session stopped."""
    if confirmed_stopped is not True:
        raise tasks.TaskError('Explicit confirmation is required')
    with tasks.transaction(db):
        authorize(db, task_id, token)
        run = db.execute('SELECT * FROM opencode_runs WHERE id=? AND task_id=?', (run_id, task_id)).fetchone()
        if not run or run['state'] != 'uncertain':
            raise tasks.TaskError('Run is not eligible for reconciliation')
        db.execute("UPDATE opencode_runs SET state='closed' WHERE id=?", (run_id,))
        tasks.event(db, task_id, 'opencode_operator_confirmed_stopped', {'run_id': run_id})

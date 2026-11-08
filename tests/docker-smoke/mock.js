const http = require('node:http');

http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.method === 'GET' && req.url === '/v1/models') {
    return res.end(JSON.stringify({object: 'list', data: [{id: 'test-local-model', object: 'model'}]}));
  }
  if (req.method !== 'POST' || req.url !== '/v1/chat/completions') {
    res.statusCode = 404;
    return res.end(JSON.stringify({error: 'not found'}));
  }
  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    try {
      const request = JSON.parse(body);
      if (request.model !== 'test-local-model' || request.messages?.[0]?.content !== 'ping') throw new Error('bad request');
      res.end(JSON.stringify({id: 'mock-1', object: 'chat.completion', created: 1,
        model: request.model, choices: [{index: 0, message: {role: 'assistant', content: 'pong'}, finish_reason: 'stop'}],
        usage: {prompt_tokens: 1, completion_tokens: 1, total_tokens: 2}}));
    } catch (_) {
      res.statusCode = 400;
      res.end(JSON.stringify({error: 'invalid request'}));
    }
  });
}).listen(1234, '0.0.0.0');

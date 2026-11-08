const base = 'http://litellm:4000';
const headers = {'Authorization': 'Bearer sk-smoke-test-local-only-1234567890', 'Content-Type': 'application/json'};
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  let models;
  for (let i = 0; i < 90; i++) {
    try {
      const response = await fetch(base + '/v1/models', {headers, signal: AbortSignal.timeout(2000)});
      if (response.ok) { models = await response.json(); break; }
    } catch (_) { /* service is still starting */ }
    await delay(1000);
  }
  if (!models?.data?.some(model => model.id === 'test-local-model')) throw new Error('Model list unavailable or incorrect');
  const response = await fetch(base + '/v1/chat/completions', {method: 'POST', headers,
    body: JSON.stringify({model: 'test-local-model', messages: [{role: 'user', content: 'ping'}]}),
    signal: AbortSignal.timeout(60000)});
  const body = await response.text();
  if (!response.ok) throw new Error('Chat request failed: ' + response.status + ' ' + body);
  if (JSON.parse(body).choices?.[0]?.message?.content !== 'pong') throw new Error('Unexpected response: ' + body);
  const denied = await fetch(base + '/v1/models', {headers: {'Authorization': 'Bearer invalid'}});
  // LiteLLM without a key database can respond with 400 instead of 401.
  if (denied.status < 400 || denied.status >= 500) throw new Error('Invalid key was not rejected: ' + denied.status);
  console.log('PASS: model list, completion via upstream, invalid-key rejection');
}
main().catch(err => { console.error(err); process.exitCode = 1; });

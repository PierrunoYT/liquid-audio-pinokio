const test = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')
const install = require('../install')
const menu = require('../pinokio').menu

test('installation, start, reset and deduplication use the same environment', () => {
  const torch = install.run.find(step => step.method === 'script.start').params.params
  const start = require('../start').run[0].params
  const env = path.join(start.path, start.venv)
  assert.equal(path.join(torch.path, torch.venv), env)
  assert.equal(path.normalize(require('../reset').run[0].params.path), env)
  assert.equal(path.normalize(require('../link').run[0].params.venv), env)
  const commands = install.run.find(step => step.method === 'shell.run').params.message
  assert.ok(commands.includes('uv pip install -r requirements.txt'))
  assert.ok(commands.includes('uv pip check'))
})

test('platform dispatch chooses one matching torch build and terminates', () => {
  for (const [platform, gpu, expected] of [
    ['win32', 'nvidia', 'cu128'], ['linux', 'nvidia', 'cu128'],
    ['linux', 'amd', 'rocm6.4'], ['win32', 'amd', 'cpu'],
    ['darwin', 'apple', null], ['linux', null, 'cpu']
  ]) {
    const step = require('../torch').run.find(step => !step.when ||
      Function('platform', 'gpu', `return ${step.when.slice(2, -2)}`)(platform, gpu))
    assert.equal(step.next, null)
    assert.equal(step.params.message.includes('--no-deps'), false)
    if (expected) assert.ok(step.params.message.endsWith('/' + expected))
    else assert.equal(step.params.message.includes('--index-url'), false)
  }
})

test('menus handle initial install, ready, running and reset after env deletion', async () => {
  for (const [installed, running, url, expected] of [
    [false, '', null, 'install.js'], [true, '', null, 'start.js'],
    [true, 'start.js', 'http://127.0.0.1:7861', 'http://127.0.0.1:7861'],
    [false, 'reset.js', null, 'reset.js'], [false, 'update.js', null, 'update.js']
  ]) {
    const result = await menu({}, {
      exists: p => installed && p === 'app/env',
      running: p => p === running,
      local: () => ({ url })
    })
    assert.equal(result[0].href, expected)
    assert.equal(result[0].default, true)
  }
})

test('server URL capture survives Gradio output and preserves its port', () => {
  const start = require('../start')
  const pattern = start.run[0].params.on[0].event
  const regex = new RegExp(pattern.slice(1, -1))
  assert.equal(regex.exec('Running on local URL:  http://127.0.0.1:7862')[1], 'http://127.0.0.1:7862')
  assert.equal(start.run[1].params.url, '{{input.event[1]}}')
  assert.equal(start.daemon, true)
})

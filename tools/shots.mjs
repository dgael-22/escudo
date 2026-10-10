// Capturas con Edge/Chrome headless via CDP. Uso: node tools/shots.mjs <url> [chrome.exe]
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const url = process.argv[2];
const exe = process.argv[3] || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9333;
const p = spawn(exe, ['--headless=new', `--remote-debugging-port=${port}`, '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--user-data-dir=' + process.env.TEMP + '/shots-prof', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let tabs;
for (let i = 0; i < 40; i++) { try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (tabs.length) break; } catch {} await sleep(500); }
const ws = new WebSocket(tabs.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pend = new Map(); const logs = [];
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } else if (d.method === 'Runtime.consoleAPICalled' || d.method === 'Runtime.exceptionThrown' || d.method === 'Log.entryAdded') logs.push(JSON.stringify(d.params).slice(0, 300)); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async (file) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(file, Buffer.from(r.result.data, 'base64')); console.log('saved', file); };
await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
async function run(w, h, mobile, prefix, doInteract) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  await send('Page.navigate', { url }); await sleep(2000);
  for (let i = 0; i < 60 && !(await ev("!document.getElementById('btn-wear').disabled")); i++) await sleep(500);
  await sleep(2500); await shot(`screenshots/${prefix}-vista-general.png`);
  if (doInteract) {
    await ev("document.getElementById('btn-wear').click()"); await sleep(3500);
    await ev("document.getElementById('btn-steel').click(); document.getElementById('btn-bump').click()"); await sleep(1500);
    console.log(await ev("[...document.querySelectorAll('.btn')].map(b=>b.id+':'+b.getAttribute('aria-pressed')).join(' ')"));
    await shot(`screenshots/${prefix}-interaccion.png`);
  }
}
await run(1280, 800, false, 'escritorio', true);
await run(390, 844, true, 'movil', true);
console.log('LOGS', logs);
ws.close(); p.kill();

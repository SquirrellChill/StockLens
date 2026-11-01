const { spawn } = require('child_process');
const http = require('http');

async function checkBrowser() {
  const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  const port = 9222;
  const userDataDir = 'D:\\CADT\\StockLens\\.edge_qa_profile';

  console.log('Launching Headless Edge on port', port, '...');
  const proc = spawn(edgePath, [
    `--headless=new`,
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    'http://localhost:5173',
  ]);

  // Wait 3 seconds for Edge CDP to become available
  await new Promise(r => setTimeout(r, 3000));

  try {
    const listRes = await fetch(`http://127.0.0.1:${port}/json/list`);
    const pages = await listRes.json();
    console.log('Open pages:', pages.map(p => ({ title: p.title, url: p.url })));

    const targetPage = pages.find(p => p.url.includes('5173')) || pages[0];
    if (!targetPage) throw new Error('No target page found');

    const wsUrl = targetPage.webSocketDebuggerUrl;
    console.log('Connecting to DevTools WebSocket:', wsUrl);

    const ws = new WebSocket(wsUrl);
    const consoleLogs = [];
    const errors = [];

    await new Promise((resolve, reject) => {
      ws.onopen = () => {
        console.log('WebSocket connected. Enabling Console and Runtime...');
        ws.send(JSON.stringify({ id: 1, method: 'Console.enable' }));
        ws.send(JSON.stringify({ id: 2, method: 'Runtime.enable' }));
        ws.send(JSON.stringify({ id: 3, method: 'Page.enable' }));
        setTimeout(resolve, 1500);
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Console.messageAdded') {
          consoleLogs.push(msg.params.message);
          if (msg.params.message.level === 'error') {
            errors.push(msg.params.message.text);
          }
        }
        if (msg.method === 'Runtime.exceptionThrown') {
          errors.push(msg.params.exceptionDetails?.text || JSON.stringify(msg.params));
        }
      };

      ws.onerror = reject;
    });

    console.log(`\nBrowser Console Logs count: ${consoleLogs.length}`);
    consoleLogs.forEach(log => console.log(`  [${log.level}] ${log.text}`));

    console.log(`\nBrowser Errors count: ${errors.length}`);
    if (errors.length > 0) {
      errors.forEach(e => console.error('  ERROR:', e));
    } else {
      console.log('✓ ZERO browser console errors detected on frontend!');
    }

    ws.close();
  } finally {
    proc.kill();
  }
}

checkBrowser().catch(e => {
  console.error(e);
  process.exit(1);
});

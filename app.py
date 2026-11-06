from __future__ import annotations
import argparse
import csv
import io
import html
import json
import logging
import math
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from engine import Store, Prices, default_config, report, PRICE_URL

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
STATE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'UsageDesk'

def validate_preferences(value):
    value = value if isinstance(value, dict) else {}
    options = dict(language=('zh-CN', 'en'), background=('light', 'dark'),
                   theme=('lavender', 'ink', 'sakura', 'maple', 'glacier', 'meadow'))
    result = {}
    for key, choices in options.items():
        selected = value.get(key, choices[0])
        if selected not in choices:
            raise ValueError('无效界面选项：' + key)
        result[key] = selected
    return result

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def validate_config(data):
    path_keys = ('codex_homes', 'claude_homes', 'antigravity_homes', 'cursor_paths', 'dsh_homes', 'opencode_homes')
    for key in path_keys[2:]:
        data.setdefault(key, [])
    for key in path_keys:
        if not isinstance(data.get(key), list) or len(data[key]) > 20 or any(not isinstance(p,str) or not p.strip() for p in data[key]):
            raise ValueError(key+' 应为目录字符串数组，最多 20 个')
        data[key] = [str(Path(os.path.expandvars(p)).expanduser().resolve()) for p in data[key]]
    if not isinstance(data.get('prices'), dict):
        raise ValueError('prices 应为对象')
    for model, price in data['prices'].items():
        if not isinstance(price, dict) or not all(k in price for k in ('input','cached','output')):
            raise ValueError(f'{model} 需要 input、cached、output 单价')
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in price.values()):
            raise ValueError('单价必须是大于等于 0 的有限数字，单位 USD / 百万 Tokens')
    result = {k:data[k] for k in (*path_keys, 'prices')}
    result['ui'] = validate_preferences(data.get('ui'))
    return result

class Application:
    def __init__(self, state=STATE):
        self.state, self.lock = state, threading.RLock()
        self.token, self.last_ping = secrets.token_urlsafe(32), time.monotonic()
        path = state/'settings.json'
        self.config = validate_config(json.loads(path.read_text(encoding='utf-8')) if path.exists() else default_config())
        self.store = Store(self.config)

    def prices(self):
        path = self.state/'prices.json'
        return Prices(path if path.exists() else BASE/'prices.json', self.config['prices'])

    def usage(self, query):
        with self.lock:
            events, diagnostics = self.store.collect()
            return report(events, diagnostics, self.prices(), query)

def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def send(self, data, status=200, mime='application/json; charset=utf-8', extra=None):
            raw = data if isinstance(data, bytes) else json.dumps(data,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            for k,v in (extra or {}).items(): self.send_header(k,v)
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass  # A newer filter request can cancel the previous response.

        def trusted(self):
            # Defend localhost APIs against cross-origin reads and DNS rebinding.
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.trusted(): return self.send({'error':'无效主机'},403)
            parsed = urlparse(self.path)
            query = {k:v[-1] for k,v in parse_qs(parsed.query).items()}
            try:
                if parsed.path in ('/', '/index.html'):
                    page = (BASE/'web'/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',app.token)
                    page = page.replace('__PREFERENCES__', html.escape(json.dumps(app.config['ui']), quote=True))
                    return self.send(page.encode('utf-8'),mime='text/html; charset=utf-8')
                if parsed.path in ('/app.js','/appearance.js','/style.css'):
                    return self.send((BASE/'web'/parsed.path[1:]).read_bytes(),mime='text/javascript; charset=utf-8' if parsed.path.endswith('.js') else 'text/css; charset=utf-8')
                if parsed.path == '/api/settings': return self.send(app.config)
                if parsed.path == '/api/health': return self.send({'ok':True,'version':'1.0.0'})
                if parsed.path in ('/api/usage','/api/export'):
                    offset = int(query.get('utc_offset','480'))
                    if not -720 <= offset <= 840: raise ValueError('时区超出范围')
                    from datetime import date
                    for key in ('since','until'):
                        if query.get(key): date.fromisoformat(query[key])
                    if query.get('since') and query.get('until') and query['since'] > query['until']:
                        raise ValueError('开始日期不能晚于结束日期')
                    data = app.usage(query)
                    if parsed.path == '/api/usage': return self.send(data)
                    dimension = query.get('dimension','daily')
                    rows = data['groups'].get(dimension)
                    if rows is None: raise ValueError('无效报表维度')
                    if query.get('search'):
                        needle = query['search'].casefold()
                        rows = [row for row in rows if needle in row['key'].casefold()
                                or needle in row.get('label', '').casefold()]
                    stream = io.StringIO(newline='')
                    writer = csv.writer(stream)
                    columns = ('key','input','cached','uncached','output','reasoning','normal','total','cost','unpriced_tokens','events')
                    writer.writerow(columns)
                    for row in rows:
                        values = [row[k] for k in columns]
                        values[0] = "'"+values[0] if str(values[0]).startswith(('=','+','-','@','\t','\r')) else values[0]
                        if row['unpriced_events']: values[8] = f"{row['cost']:.8f} (partial)" if row['events'] != row['unpriced_events'] else 'unpriced'
                        writer.writerow(values)
                    return self.send(('\ufeff'+stream.getvalue()).encode('utf-8'), mime='text/csv; charset=utf-8',extra={'Content-Disposition':f'attachment; filename="usage-{dimension}.csv"'})
                return self.send({'error':'不存在'},404)
            except (ValueError, OSError) as exc:
                self.send({'error':str(exc)},400)
            except Exception:
                logging.exception('读取用量失败')
                self.send({'error':'读取失败，请检查日志 UsageDesk/app.log'},500)

        def do_POST(self):
            if not self.trusted() or self.headers.get('X-Usage-Token') != app.token:
                return self.send({'error':'请求验证失败'},403)
            try:
                length = int(self.headers.get('Content-Length',0))
                if not 0 <= length <= 1000000: raise ValueError('请求过大')
                body = self.rfile.read(length)
                if self.path == '/api/ping':
                    app.last_ping = time.monotonic()
                    return self.send({'ok':True})
                if self.path == '/api/quit':
                    self.send({'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                if self.path == '/api/settings':
                    with app.lock:
                        incoming = json.loads(body)
                        incoming.setdefault('ui', app.config['ui'])
                        config = validate_config(incoming)
                        save_json(app.state/'settings.json',config)
                        app.config, app.store = config, Store(config)
                    return self.send({'ok':True})
                if self.path == '/api/preferences':
                    preferences = validate_preferences(json.loads(body))
                    with app.lock:
                        config = dict(app.config, ui=preferences)
                        save_json(app.state/'settings.json', config)
                        app.config = config
                    return self.send({'ok':True})
                if self.path == '/api/prices/refresh':
                    # Explicit action only. Logs and metadata never leave the machine.
                    with urllib.request.urlopen(PRICE_URL, timeout=35) as response:
                        data = json.loads(response.read(20_000_000))
                    models = {k:v for k,v in data.items() if isinstance(v,dict) and any(x in k.lower() for x in ('gpt','claude','o1','o3','o4','codex','gemini','deepseek')) and 'input_cost_per_token' in v}
                    if len(models)<10: raise ValueError('上游价格表格式无效')
                    from datetime import datetime, timezone
                    with app.lock:
                        save_json(app.state/'prices.json',dict(updated_at=datetime.now(timezone.utc).isoformat(),source=PRICE_URL,models=models))
                    return self.send({'ok':True,'models':len(models)})
                return self.send({'error':'不存在'},404)
            except Exception as exc:
                self.send({'error':str(exc)},400)
    return Handler

def browser_path():
    for env, suffix in [('PROGRAMFILES(X86)','Microsoft/Edge/Application/msedge.exe'),('PROGRAMFILES','Microsoft/Edge/Application/msedge.exe'),('PROGRAMFILES','Google/Chrome/Application/chrome.exe'),('LOCALAPPDATA','Google/Chrome/Application/chrome.exe')]:
        p = Path(os.environ.get(env,''))/suffix
        if p.is_file(): return p
    return None

def main():
    parser = argparse.ArgumentParser(description='UsageDesk 本地用量面板')
    parser.add_argument('--server',action='store_true',help='后台服务模式，不自动打开窗口')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--state-dir',type=Path,default=STATE)
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=args.state_dir/'app.log', level=logging.ERROR,encoding='utf-8')
    app = Application(args.state_dir)
    server = ThreadingHTTPServer(('127.0.0.1',args.port), handler_for(app))
    server.daemon_threads = True
    url = f'http://127.0.0.1:{server.server_port}'
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    if not args.server:
        browser = browser_path()
        if browser:
            subprocess.Popen([str(browser),f'--app={url}',f'--user-data-dir={args.state_dir / "browser"}', '--no-first-run','--window-size=1440,1000'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:
            webbrowser.open(url)
        # Heartbeats keep the process alive. An explicit Quit button stops immediately;
        # closed windows release the server after a grace period, including initial load.
        def watchdog():
            while thread.is_alive():
                time.sleep(10)
                if time.monotonic()-app.last_ping > 180:
                    server.shutdown()
                    break
        threading.Thread(target=watchdog,daemon=True).start()
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
    finally:
        server.server_close()
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        logging.exception('启动失败')
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,str(exc),'UsageDesk 启动失败',16)
        raise

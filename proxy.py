#!/usr/bin/env python3
"""
简单的基金估值API代理服务器
解决浏览器跨域(CORS)和HTTPS混合内容问题

使用方法:
  python proxy.py
  然后访问 http://localhost:8888

在手机端使用:
  1. 电脑运行 python proxy.py
  2. 手机连接同一WiFi
  3. 手机浏览器打开 http://<电脑IP>:8888
  4. 在设置中将代理地址设为: http://<电脑IP>:8888/proxy?code={code}
"""

import http.server
import urllib.request
import urllib.parse
import json
import re
import os
import sys

PORT = 8888

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 代理API请求
        if self.path.startswith('/proxy'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            code = params.get('code', [''])[0]

            if not code:
                self.send_error(400, 'Missing code parameter')
                return

            # 转发到天天基金API
            url = f'http://fundgz.1234567.com.cn/js/{code}.js'
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36',
                    'Referer': 'http://fund.eastmoney.com/'
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode('utf-8')
                    # 提取JSON
                    match = re.search(r'jsonpgz\((.+)\)', data)
                    if match:
                        result = json.loads(match.group(1))
                    else:
                        result = {'error': 'parse failed', 'raw': data}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        # 基金列表代理
        if self.path.startswith('/fundlist'):
            url = 'http://fund.eastmoney.com/js/fundcode_search.js'
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'http://fund.eastmoney.com/'
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read().decode('utf-8')
                    # 提取 var r = [...] 数组
                    match = re.search(r'var\s+r\s*=\s*(\[\[.*\]\])', data, re.DOTALL)
                    if match:
                        result = json.loads(match.group(1))
                    else:
                        result = []

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        # 官方净值代理（pingzhongdata，更新更及时）
        if self.path.startswith('/nav'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            code = params.get('code', [''])[0]

            if not code:
                self.send_error(400, 'Missing code parameter')
                return

            url = f'http://fund.eastmoney.com/pingzhongdata/{code}.js'
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
                    'Referer': 'http://fund.eastmoney.com/'
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read().decode('utf-8')
                    trend_match = re.search(r'var Data_netWorthTrend\s*=\s*(\[[\s\S]*?\]);', data)
                    name_match = re.search(r'var fS_name\s*=\s*"(.+?)";', data)

                    if trend_match:
                        trend = json.loads(trend_match.group(1))
                        latest, prev = None, None
                        for item in reversed(trend):
                            if item.get('y') is not None:
                                if latest is None:
                                    latest = item
                                elif prev is None:
                                    prev = item
                                    break
                        if latest:
                            import datetime
                            d = datetime.datetime.fromtimestamp(latest['x'] / 1000)
                            result = {
                                'dwjz': str(latest['y']),
                                'jzrq': d.strftime('%Y-%m-%d'),
                                'name': name_match.group(1) if name_match else ''
                            }
                            if prev and prev.get('y') is not None:
                                result['prevDwjz'] = str(prev['y'])
                                result['actualChange'] = str(round((latest['y'] - prev['y']) / prev['y'] * 100, 2))
                        else:
                            result = {'error': 'no valid nav'}
                    else:
                        result = {'error': 'parse failed'}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        # 选项预检
        if self.path == '/options' or self.command == 'OPTIONS':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            return

        # 默认：提供静态文件服务 (index.html)
        super().do_GET()

    def log_message(self, format, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))


def get_local_ip():
    """获取本机局域网IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('114.114.114.114', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    local_ip = get_local_ip()
    print(f'''
╔══════════════════════════════════════════════╗
║        📈 基金估值代理服务器                   ║
║                                              ║
║  本地访问: http://localhost:{PORT}             ║
║  手机访问: http://{local_ip}:{PORT}    ║
║                                              ║
║  手机端代理设置:                              ║
║  http://{local_ip}:{PORT}/proxy?code={{code}}  ║
║                                              ║
║  按 Ctrl+C 停止服务器                         ║
╚══════════════════════════════════════════════╝
''')

    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器已停止')
        server.server_close()

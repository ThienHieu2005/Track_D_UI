"""One local HTTP UI per peer. This layer never implements election, chat ordering or RA.

Security: binds to 127.0.0.1 by default; use only for classroom demo.
No authentication or CSRF protection: do NOT expose the UI on a public network.
"""
import json
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from app.peer_node import CombinedNode

HTML = (Path(__file__).resolve().parents[1] / 'web' / 'index.html').read_bytes() if (Path(__file__).resolve().parents[1] / 'web' / 'index.html').exists() else b''


class WebPeer:
    def __init__(self, node_id, counter_path='shared_counter.txt', board_path='shared_whiteboard.txt'):
        self.node_id = node_id
        self._lock = threading.Lock()
        self._seq = 0
        self._events = deque(maxlen=300)
        self.node = CombinedNode(node_id, counter_path=counter_path, board_path=board_path,
                                 on_deliver=self.on_chat, on_leader_change=self.on_leader)
        self.http_server = None

    def event(self, category, message, **other):
        with self._lock:
            self._seq += 1
            self._events.append({'seq': self._seq, 'kind': category, 'text': message,
                                 'time': time.strftime('%H:%M:%S'), **other})

    def on_chat(self, msg):
        self.event('chat', msg['content'], sender=msg['sender'], vector=msg['vector'],
                   lamport=msg.get('lamport'), message_id=msg.get('id'))

    def on_leader(self, leader):
        self.event('system', f'Leader hiện tại: Node {leader}' if leader else 'Đang bầu Leader…')

    def state(self, since=0):
        with self._lock:
            events = [e.copy() for e in self._events if e['seq'] > since]
            seq = self._seq
        status = self.node.get_combined_status()
        try:
            board = self.node.read_shared_file()
        except OSError:
            board = ''
        try:
            counter = int(self.node.counter_path.read_text(encoding='utf-8').strip())
        except (ValueError, OSError):
            counter = None
        return {'status': status, 'events': events, 'seq': seq, 'board': board, 'counter': counter}

    def start(self, host='127.0.0.1', port=None):
        port = 8000 + self.node_id if port is None else port
        self.node.start()
        try:
            self.http_server = ThreadingHTTPServer((host, port), make_handler(self))
            self.http_server.daemon_threads = True
        except BaseException:
            self.node.stop()
            raise
        self.event('system', f'Node {self.node_id} đã khởi động, giao diện http://{host}:{port}')
        return self

    def serve(self):
        try:
            self.http_server.serve_forever(poll_interval=0.2)
        finally:
            self.http_server.server_close()
            self.node.stop()

    def stop(self):
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        self.node.stop()


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'TrackD-Web/1.0'

        def log_message(self, format, *args):
            # Suppress polling spam. Error logs go to individual request responses.
            pass

        def _send(self, status, data, ctype='application/json; charset=utf-8'):
            if isinstance(data, (dict, list)):
                payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
            else:
                payload = data
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                return self._send(200, HTML, 'text/html; charset=utf-8')
            if path == '/api/state':
                try:
                    return self._send(200, app.state())
                except (OSError, ValueError) as exc:
                    return self._send(500, {'ok': False, 'error': str(exc)})
            return self._send(404, {'ok': False, 'error': 'Not found'})

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ('/api/chat', '/api/write', '/api/cs', '/api/election', '/api/delay', '/api/inc'):
                return self._send(404, {'ok': False, 'error': 'Unknown action'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Request body must be 1..4096 bytes')
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(data, dict):
                    raise ValueError('JSON object required')
                if path == '/api/chat':
                    content = data.get('text')
                    if not isinstance(content, str) or not content.strip() or len(content.encode('utf-8')) > 500:
                        raise ValueError('Tin nhắn phải có nội dung, tối đa 500 byte')
                    app.node.send_chat(content)
                    app.event('action', 'Đã gửi tin nhắn đến các Node')
                elif path == '/api/write':
                    content = data.get('text')
                    if not isinstance(content, str):
                        raise ValueError('Nội dung ghi phải là văn bản')
                    success = app.node.write_shared_file(content)
                    if not success:
                        app.event('warning', 'Không đủ REPLY: ghi file bị từ chối')
                        return self._send(409, {'ok': False, 'error': 'Không nhận đủ REPLY, không ghi file'})
                    app.event('action', 'Đã ghi vào file chung sau khi nhận đủ REPLY')
                elif path == '/api/cs':
                    seconds = data.get('seconds', 3)
                    if type(seconds) not in (int, float) or not 0 <= seconds <= 15:
                        raise ValueError('Thời gian CS phải nằm trong khoảng 0–15 giây')
                    success = app.node.run_cs(seconds=seconds)
                    if not success:
                        app.event('warning', 'Không thể vào Critical Section')
                        return self._send(409, {'ok': False, 'error': 'Không đủ REPLY để vào CS'})
                    app.event('action', f'Đã vào và thoát CS ({seconds}s)')
                elif path == '/api/election':
                    app.node.start_election()
                    app.event('action', 'Đã yêu cầu chạy Bully Election')
                elif path == '/api/delay':
                    target, seconds = data.get('target'), data.get('seconds')
                    if type(target) is not int or target not in app.node.delays:
                        raise ValueError('Node đích không hợp lệ')
                    if type(seconds) not in (int, float) or not 0 <= seconds <= 15:
                        raise ValueError('Độ trễ phải từ 0 đến 15 giây')
                    with app.node.lock:
                        app.node.delays[target] = seconds
                    app.event('action', f'Độ trễ chat Node {target}: {seconds}s')
                elif path == '/api/inc':
                    success = app.node.increment_counter()
                    if not success:
                        return self._send(409, {'ok': False, 'error': 'Không đủ REPLY để tăng bộ đếm'})
                    app.event('action', 'Tăng bộ đếm chung thành công')
                return self._send(200, {'ok': True})
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                return self._send(400, {'ok': False, 'error': str(exc)})
            except (OSError, RuntimeError) as exc:
                return self._send(500, {'ok': False, 'error': str(exc)})
            except Exception as exc:
                # Explicit error to client, never pretend the operation succeeded.
                return self._send(500, {'ok': False, 'error': f'Lỗi xử lý: {type(exc).__name__}'})
    return Handler

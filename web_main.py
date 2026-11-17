"""Run one independent P2P peer with its own web UI (standard-library only)."""
import argparse
from app.web_ui import WebPeer
from modules.student1.causal_multicast import NODES


def main():
    parser = argparse.ArgumentParser(description='Track D Web - one web server per independent peer')
    parser.add_argument('--id', type=int, required=True, choices=sorted(NODES))
    parser.add_argument('--counter', default='shared_counter.txt')
    parser.add_argument('--board', default='shared_whiteboard.txt')
    parser.add_argument('--http-port', type=int)
    args = parser.parse_args()
    peer = WebPeer(args.id, counter_path=args.counter, board_path=args.board)
    peer.start(port=args.http_port)
    print(f'[Node {args.id}] OPEN http://127.0.0.1:{args.http_port or (8000 + args.id)}', flush=True)
    print('Press Ctrl+C to stop this peer. 4 peers = 4 separate OS processes.', flush=True)
    try:
        peer.serve()
    except KeyboardInterrupt:
        print(f'[Node {args.id}] Stopping...', flush=True)


if __name__ == '__main__':
    main()

import socket
import threading
import os
import hashlib
import time

BROADCAST_PORT = 9999
TRANSFER_PORT = 10000
CHUNK_SIZE = 1024 * 4
SHARED_DIR = "shared"

peers = set()


def broadcast_presence():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            message = b"P2P_PEER_DISCOVERY"
            sock.sendto(message, ("<broadcast>", BROADCAST_PORT))
            time.sleep(5)


def listen_for_peers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', BROADCAST_PORT))
        while True:
            data, addr = sock.recvfrom(1024)
            if data == b"P2P_PEER_DISCOVERY":
                peers.add(addr[0])


def list_files():
    return os.listdir(SHARED_DIR)


def handle_client(conn, addr):
    filename = conn.recv(1024).decode()
    print(f"[{addr}] wants file: {filename}")
    filepath = os.path.join(SHARED_DIR, filename)

    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                conn.sendall(chunk)
    conn.close()


def serve_files():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('', TRANSFER_PORT))
        server.listen()
        print(f"[+] Listening for file requests on port {TRANSFER_PORT}")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def request_file(peer_ip, filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((peer_ip, TRANSFER_PORT))
        sock.send(filename.encode())
        output_path = os.path.join(SHARED_DIR, f"dl_{filename}")
        with open(output_path, 'wb') as f:
            while chunk := sock.recv(CHUNK_SIZE):
                f.write(chunk)
        print(f"[+] Download complete: {output_path}")


def sha256sum(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def command_line():
    '''Interactive command line for user input to manage the P2P file sharing.
    '''
    print("Welcome to the P2P File Sharing System")
    print("Type 'list' to see available files, 'peers' to see known peers, 'get [ip] [filename]' to download a file, or 'quit' to exit.")
    global peers
    peers = set()  # Reset peers to avoid duplicates on restart
    peers.add(socket.gethostbyname(socket.gethostname()))  # Add self to peers
    while True:
        cmd = input("Command (list / peers / get [ip] [filename] / quit): ").strip().split()
        if not cmd:
            continue
        if cmd[0] == "list":
            print("Available files:", list_files())
        elif cmd[0] == "peers":
            print("Known peers:", peers)
        elif cmd[0] == "get" and len(cmd) == 3:
            request_file(cmd[1], cmd[2])
        elif cmd[0] == "quit":
            break


if __name__ == "__main__":
    os.makedirs(SHARED_DIR, exist_ok=True)
    threading.Thread(target=broadcast_presence, daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()
    threading.Thread(target=serve_files, daemon=True).start()
    command_line()

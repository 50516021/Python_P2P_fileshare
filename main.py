import socket
import threading
import os
import hashlib
import time
import sys

# TODO
# Store a list of available chunks for each file (files are split into multiple chunks, 1, 2, 3... and you broadcast what chunks you have)

# Maintain a list of files available on each peer locally
# - Broadcast your own files
# - Receive other broadcasts
# - Can just be done on the same broadcast port I think... would not work in a real network (scaling issues), but does in this case
# - So just stick this info in the current broadcast message

# Instead of chunking between just two peers, peers need to be able to receive from multiple at once (every peer who has chunks)
# - Figure out all the chunks we need, and request them individually

# Verify via hashes
# - Check hash of each chunk as we get it
# - Check hash of full file at end

BROADCAST_PORT = 9999
try:
    TRANSFER_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
except ValueError:
    print("Error: TRANSFER_PORT must be an integer.")
    sys.exit(1)
SHARED_DIR = f"shared/{TRANSFER_PORT}"

CHUNK_SIZE = 1024

peers = set()
peer_files = {}

def broadcast_presence():
    '''Broadcast presence and local files on the network.'''
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            files = get_my_files()
            message = {
                "type": "P2P_PEER_DISCOVERY",
                "port": TRANSFER_PORT,
                "files": files
            }
            sock.sendto(json.dumps(message).encode(), ("<broadcast>", BROADCAST_PORT))
            time.sleep(5)


def get_my_files():
    '''Get a list of available files and their total number of chunks and their full SHA-256 hash.'''
    file_chunks = {}
    if not os.path.exists(SHARED_DIR):
        return file_chunks

    for filename in os.listdir(SHARED_DIR):
        filepath = os.path.join(SHARED_DIR, filename)
        if os.path.isfile(filepath):
            filesize = os.path.getsize(filepath)
            num_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE

            filehash = sha256sum(filepath)

            file_chunks[filename] = {
                "total_chunks": num_chunks,
                "filehash": filehash
            }
    return file_chunks


def listen_for_peers():
    '''Listen for incoming peer discovery messages and update peer file lists.'''
    global peer_files
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', BROADCAST_PORT))
        while True:
            data, addr = sock.recvfrom(65536)
            try:
                message = json.loads(data.decode())
            except json.JSONDecodeError:
                print(f"Invalid message from {addr}: {data}")
                continue

            if message.get("type") == "P2P_PEER_DISCOVERY":
                port = message["port"]
                files = message.get("files", {})
                peer_id = (addr[0], str(port))

                if peer_id not in peers:
                    print("New peer added", addr[0], port)
                    peers.add(peer_id)

                peer_files[peer_id] = files


def list_files():
    '''List all available files across all peers, based on their hash, excluding own files (by hash).'''
    files = {}

    local_file_hashes = set()
    for filename in os.listdir(SHARED_DIR):
        filepath = os.path.join(SHARED_DIR, filename)
        if os.path.isfile(filepath):
            local_file_hashes.add(sha256sum(filepath))

    for peer, file_info in peer_files.items():
        for filename, info in file_info.items():
            filehash = info["filehash"]

            if filehash in local_file_hashes:
                continue

            if filehash not in files:
                files[filehash] = {"filename": filename, "total_chunks": info["total_chunks"]}

    output = []
    for filehash, info in files.items():
        filename = info["filename"]
        chunk_count = info["total_chunks"]
        output.append(f"{filename} (hash: {filehash}) - {chunk_count} chunk{'s' if chunk_count != 1 else ''}")

    return "\n".join(output) if output else "No files available."


def handle_client(conn, addr):
    '''Handle incoming file or chunk requests from peers.'''
    request = conn.recv(1024).decode()
    parts = request.strip().split()
    
    if parts[0] == "chunk" and len(parts) == 3:
        _, filename, chunk_num = parts
        chunk_num = int(chunk_num)
        filepath = os.path.join(SHARED_DIR, filename)

        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                f.seek((chunk_num - 1) * CHUNK_SIZE)
                chunk = f.read(CHUNK_SIZE)

                chunk_hash = hashlib.sha256(chunk).hexdigest().encode()
                conn.sendall(chunk_hash + chunk)  # Send hash first, then chunk
    conn.close()


def serve_files():
    '''Serve files to peers that request them.
    This function listens for incoming TCP connections on a specified port,
    accepts file requests, and sends the requested files in chunks.
    It runs in a separate thread to allow concurrent file serving.
    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('', TRANSFER_PORT))
        server.listen()
        print(f"[+] Listening for file requests on port {TRANSFER_PORT}")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def request_file(peer_ip, filename):
    '''Request a file from a peer.
    This function connects to a peer's file server, sends the filename,
    and receives the file in chunks, saving it to the shared directory.
    '''
    peer_port = 10000
    if ':' in peer_ip:
        peer_ip, peer_port = peer_ip.split(':')
        peer_port = int(peer_port)
    else:
        for peer in peers:
            if peer_ip in peer[0]:
                peer_ip = peer[0]
                peer_port = peer[1]
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((peer_ip, peer_port))
        sock.send(filename.encode())
        output_path = os.path.join(SHARED_DIR, f"dl_{filename}")
        with open(output_path, 'wb') as f:
            while chunk := sock.recv(CHUNK_SIZE):
                f.write(chunk)
        print(f"[+] Download complete: {output_path}")


def sha256sum(path):
    '''Calculate the SHA-256 checksum of a file.
    This function reads a file in chunks and computes its SHA-256 hash.
    It is used to verify file integrity after download.
    '''
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def command_line():
    '''Interactive command line for user input to manage the P2P file sharing.
    This function provides a simple command line interface for users to list files,
    view peers, request files, or exit the application.
    '''
    print(" -- Welcome to the P2P File Sharing System -- ")
    print("Type 'list' to see available files, 'peers' to see known peers, 'get [ip] [filename]' to download a file, or 'quit' to exit.")
    global peers
    while True:
        cmd = input("Command (list / peers / get [ip] [filename] / quit): ").strip().split()
        if not cmd:
            continue
        if cmd[0] in ("list", "l"):
            print("Available files:", list_files())
        elif cmd[0] == "peers":
            print("Known peers:", [f"{ip}:{int(port)}" for ip, port in peers])
        elif cmd[0] == "get" and len(cmd) == 3:
            request_file(cmd[1], cmd[2])
        elif cmd[0] in ("q", "quit"):
            break


if __name__ == "__main__":
    '''Main entry point for the P2P file sharing application.
    This function initializes the shared directory, starts the broadcast and listening threads,
    and launches the command line interface for user interaction.
    '''
    os.makedirs(SHARED_DIR, exist_ok=True)
    threading.Thread(target=broadcast_presence, daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()
    threading.Thread(target=serve_files, daemon=True).start()
    command_line()

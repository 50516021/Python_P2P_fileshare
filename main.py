import socket
import threading
import random
import os
import hashlib
import time
import sys
import json


BROADCAST_PORT = 9999
CHUNK_SIZE = 1024
try:
    TRANSFER_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
except ValueError:
    print("Error: TRANSFER_PORT must be an integer.")
    sys.exit(1)
SHARED_DIR = f"shared/{TRANSFER_PORT}"

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
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # critical for multi-peer on macOS/Linux
        except (AttributeError, OSError) as e:
            print(f"SO_REUSEPORT not available: {e}")
        
        sock.bind(('', BROADCAST_PORT))
        
        while True:
            data, addr = sock.recvfrom(65536)
            try:
                message = json.loads(data.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                print(f"Received invalid data from {addr}, skipping...")
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
    try:
        conn.settimeout(5)  # <--- Add timeout, super important
        request = conn.recv(1024)
        if not request:
            print(f"[{addr}] No data received, closing connection.")
            return
        request = request.decode(errors='ignore')  # ignore broken encoding
        parts = request.strip().split()

        if len(parts) != 3 or parts[0] != "chunk":
            print(f"[{addr}] Invalid request format: {request}")
            return

        _, filename, chunk_num = parts
        chunk_num = int(chunk_num)
        filepath = os.path.join(SHARED_DIR, filename)

        if not os.path.exists(filepath):
            print(f"[{addr}] Requested file not found: {filename}")
            return

        with open(filepath, 'rb') as f:
            f.seek((chunk_num - 1) * CHUNK_SIZE)
            chunk = f.read(CHUNK_SIZE)

            chunk_hash = hashlib.sha256(chunk).hexdigest().encode()
            try:
                conn.sendall(chunk_hash + chunk)
            except Exception as e:
                print(f"[{addr}] Failed to send chunk: {e}")
    except (socket.timeout, ConnectionResetError, OSError) as e:
        print(f"[{addr}] Connection error during handling: {e}")
    except Exception as e:
        print(f"[{addr}] Unexpected error: {e}")
    finally:
        conn.close()


def serve_files():
    '''Serve files to peers that request them.
    This function listens for incoming TCP connections on a specified port,
    accepts file requests, and sends the requested files in chunks.
    It runs in a separate thread to allow concurrent file serving.
    '''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', TRANSFER_PORT))
        server.listen()
        print(f"[+] Listening for file requests on port {TRANSFER_PORT}")
        
        while True:
            try:
                conn, addr = server.accept()
                if conn:
                    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except OSError as e:
                print(f"Server socket error: {e}")
                continue


def download_file(filename):
    '''Download a file chunk-by-chunk from multiple peers, assuming they have all chunks.'''
    global peer_files
    expected_full_hash = None
    total_chunks = None

    owners = []
    for peer, files in peer_files.items():
        if filename in files:
            file_info = files[filename]
            if not expected_full_hash:
                expected_full_hash = file_info["filehash"]
                total_chunks = file_info["total_chunks"]
            owners.append(peer)
    if not owners:
        print(f"No peers have file: {filename}")
        return

    temp_dir = os.path.join(SHARED_DIR, f"temp_{filename}")
    os.makedirs(temp_dir, exist_ok=True)

    download_success = {}
    threads = []

    for chunk_num in range(1, total_chunks + 1):
        selected_peer = random.choice(owners)

        thread = threading.Thread(
            target=download_chunk,
            args=(filename, chunk_num, [selected_peer], temp_dir, download_success)
        )
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()

    # Step 4: verify all chunks
    missing_chunks = [c for c in range(1, total_chunks + 1) if not download_success.get(c)]
    if missing_chunks:
        print(f"Missing or corrupted chunks: {missing_chunks}, download failed.")
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)
        return

    output_path = os.path.join(SHARED_DIR, f"dl_{filename}")
    with open(output_path, 'wb') as f_out:
        size_chunks = total_chunks
        for chunk_num in range(1, size_chunks + 1):
            print(f" Combining... chunk {chunk_num} of {size_chunks}", end='   \r')
            chunk_path = os.path.join(temp_dir, f"{chunk_num}.chunk")
            with open(chunk_path, 'rb') as f_in:
                f_out.write(f_in.read())

    final_hash = sha256sum(output_path)
    if final_hash != expected_full_hash:
        print(f"Final file hash mismatch! Expected {expected_full_hash}, got {final_hash}")
    else:
        print(f"Hashes Match! Download complete and verified: {output_path}")

    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)


def download_chunk(filename, chunk_num, owners, temp_dir, download_success, max_retries=5):
    '''Try to download a single chunk from any available owner.'''
    attempts = 0
    tried_peers = set()

    while attempts < max_retries:
        available_peers = [peer for peer in owners if peer not in tried_peers]
        if not available_peers:
            available_peers = owners  # retry any peer if all have been tried once

        selected_peer = random.choice(available_peers)
        peer_ip, peer_port = selected_peer

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # prevent hanging forever
                sock.connect((peer_ip, int(peer_port)))
                request = f"chunk {filename} {chunk_num}"
                sock.send(request.encode())

                expected_hash = b''
                while len(expected_hash) < 64:
                    data = sock.recv(64 - len(expected_hash))
                    if not data:
                        raise Exception("Connection closed before receiving full hash.")
                    expected_hash += data
                expected_hash = expected_hash.decode()

                chunk_data = b''
                while len(chunk_data) < CHUNK_SIZE:
                    data = sock.recv(CHUNK_SIZE - len(chunk_data))
                    if not data:
                        break
                    chunk_data += data

                actual_hash = hashlib.sha256(chunk_data).hexdigest()
                if actual_hash != expected_hash:
                    print(f"Hash mismatch for chunk {chunk_num} from {peer_ip}:{peer_port}")
                    tried_peers.add(selected_peer)
                    attempts += 1
                    continue  # retry

                chunk_path = os.path.join(temp_dir, f"{chunk_num}.chunk")
                with open(chunk_path, 'wb') as f:
                    f.write(chunk_data)
                download_success[chunk_num] = True
                print(f"Downloaded and verified chunk {chunk_num} from {peer_ip}:{peer_port}")
                return  # Success!

        except Exception as e:
            print(f"Failed to get chunk {chunk_num} from {peer_ip}:{peer_port}: {e}")
            tried_peers.add(selected_peer)
            attempts += 1

    # If we exit the loop, we failed
    print(f"Failed to download chunk {chunk_num} after {max_retries} attempts.")
    download_success[chunk_num] = False


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
        cmd = input("Commands (list / peers / get [filename] / quit) ").strip().split()
        if not cmd:
            continue
        if cmd[0] in ("list", "l"):
            print("Available files:\n", list_files())
        elif cmd[0] == "peers":
            print("Known peers:", [f"{ip}:{int(port)}" for ip, port in peers])
        elif cmd[0] == "get" and len(cmd) == 2:
            download_file(cmd[1])
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

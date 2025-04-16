# Python P2P File Sharing

A peer-to-peer file-sharing system implemented in Python.

---

## 1. Setup and Execution

### Clone the Repository

Clone the repository using the following command:

```
git clone https://github.com/50516021/Python_P2P_fileshare.git
```

### Environment Setup

Install the required dependencies using `requirements.txt`:

```
pip install -r requirements.txt
```

---

## 2. Running the Application

The main script, `main.py`, provides both peer discovery and file-sharing functionality.  
**Note:** Open multiple terminals to simulate different peers.

### 2.1 Starting the Application

Run the following command to start the P2P file-sharing system:

```
python main.py
```

This will:

1. Broadcast the peer's presence to the network.
2. Listen for other peers on the network.
3. Serve files from the `shared` directory.
4. Provide an interactive command-line interface for managing file sharing.

---

## 3. Features

### 3.1 Peer Discovery

- **Broadcast Presence**: Each peer broadcasts its presence to the network every 5 seconds.
- **Listen for Peers**: Peers listen for broadcast messages and maintain a list of known peers.

### 3.2 File Sharing

- **Serve Files**: Peers can serve files from the `shared` directory to other peers.
- **Request Files**: Peers can request files from other peers by specifying the peer's IP address and the filename.

### 3.3 File Management

- **List Files**: Users can list all files available in the `shared` directory.
- **Download Files**: Files downloaded from other peers are saved in the `shared` directory with a `dl_` prefix.
- **File Integrity**: The SHA-256 checksum of files can be computed for integrity verification.

---

## 4. Command-Line Interface

The application provides an interactive command-line interface with the following commands:

- `list`: Lists all files available in the `shared` directory.
- `peers`: Displays the list of known peers.
- `get [ip] [filename]`: Downloads a file from the specified peer.
- `quit`: Exits the application.

---

## 5. Example Usage

### 5.1 Starting the Application

Run the application:

```
python main.py
```

### 5.2 Listing Files

To list all files in the `shared` directory:

```
Command (list / peers / get [ip] [filename] / quit): list
```

### 5.3 Viewing Known Peers

To view the list of known peers:

```
Command (list / peers / get [ip] [filename] / quit): peers
```

### 5.4 Downloading a File

To download a file from a peer:

```
Command (list / peers / get [ip] [filename] / quit): get 192.168.1.10 example.txt
```

The downloaded file will be saved in the `shared` directory with the prefix `dl_`.

---

## 6. Notes

- Ensure that all peers are running the application on the same network.
- Use separate terminals to simulate multiple peers.
- The `shared` directory is automatically created if it does not exist.

---

## 7. Author

**Carter Ptak**

- [GitHub]
- [Official Homepage]

**Akira Takeuchi**

- [GitHub](https://github.com/50516021)
- [Official Homepage](https://akiratakeuchi.com/)

---

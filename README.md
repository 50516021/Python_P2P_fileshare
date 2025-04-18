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

The main script, `main.py`, provides peer discovery, file sharing, and file downloading functionality.  
**Note:** Open multiple terminals to simulate different peers.

### 2.1 Starting the Application

Run the following command to start the P2P file-sharing system:

```
python main.py [TRANSFER_PORT]
```

- `TRANSFER_PORT` (optional): The port number for file transfers. Defaults to `10000`.

This will:

1. Broadcast the peer's presence to the network.
2. Listen for other peers on the network.
3. Serve files from the `shared` directory.
4. Provide an interactive command-line interface for managing file sharing.

---

## 3. Features

### 3.1 Peer Discovery

- **Broadcast Presence**: Each peer broadcasts its presence to the network every 5 seconds.
- **Listen for Peers**: Peers listen for broadcast messages and maintain a list of known peers and their shared files.

### 3.2 File Sharing

- **Serve Files**: Peers can serve files from the `shared` directory to other peers.
- **Request Files**: Peers can request files from other peers by specifying the filename.

### 3.3 File Management

- **List Files**: Users can list all files available across peers, excluding their own files.
- **Download Files**: Files downloaded from other peers are saved in the `shared` directory with a `dl_` prefix.
- **File Integrity**: The SHA-256 checksum of files is used to verify file integrity after download.

### 3.4 Chunk-Based File Transfer

- Files are divided into chunks for transfer.
- Each chunk is verified using its SHA-256 hash to ensure data integrity.

---

## 4. Command-Line Interface

The application provides an interactive command-line interface with the following commands:

- `list` or `l`: Lists all files available across peers, excluding local files.
- `peers`: Displays the list of known peers in the format `ip:port`.
- `get [filename]`: Downloads the specified file from available peers.
- `quit` or `q`: Exits the application.

---

## 5. Example Usage

### 5.1 Starting the Application

Run the application:

```
python main.py
```

### 5.2 Listing Files

To list all files available across peers:

```
Command (list / peers / get [filename] / quit): list
```

### 5.3 Viewing Known Peers

To view the list of known peers:

```
Command (list / peers / get [filename] / quit): peers
```

### 5.4 Downloading a File

To download a file from peers:

```
Command (list / peers / get [filename] / quit): get example.txt
```

The downloaded file will be saved in the `shared` directory with the prefix `dl_`.

---

## 6. Notes

- Ensure that all peers are running the application on the same network.
- Use separate terminals to simulate multiple peers.
- The `shared` directory is automatically created if it does not exist.
- Files are downloaded chunk-by-chunk from multiple peers, ensuring efficient and reliable transfers.

---

## 7. Author

**Carter Ptak**

- [GitHub](https://github.com/Carter4242)

**Akira Takeuchi**

- [GitHub](https://github.com/50516021)
- [Official Homepage](https://akiratakeuchi.com/)

---

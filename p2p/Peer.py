import sys
import socket
import threading
import json
import time
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QLineEdit, QLabel, QListWidget)


class Peer:
    def __init__(self, peer_id, tracker_ip, tracker_port, host, port):
        self.peer_id = peer_id
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.host = host
        self.port = port
        self.connections = {}
        self.resources = []
        self.lock = threading.Lock()
        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()

    def add_resource(self, resource):
        with self.lock:
            if resource not in self.resources:
                self.resources.append(resource)
                print(f"Resource {resource} added.")

    def register_with_tracker(self):
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            message = json.dumps({"type": "register", "user_id": self.peer_id,
                                 "port": self.port, "resources": self.resources})
            conn.sendall(message.encode("utf-8"))
            conn.close()
        except Exception as e:
            print(f"Error registering with tracker: {e}")

    def keep_alive(self):
        def _send_keep_alive():
            while True:
                try:
                    conn = socket.create_connection(
                        (self.tracker_ip, self.tracker_port))
                    message = json.dumps(
                        {"type": "keep_alive", "user_id": self.peer_id, "resources": self.resources})
                    conn.sendall(message.encode("utf-8"))
                    conn.close()
                except Exception as e:
                    print(f"Failed to send keep-alive: {e}")
                time.sleep(5)

        threading.Thread(target=_send_keep_alive, daemon=True).start()

    def fetch_resources_from_tracker(self):
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            conn.sendall(json.dumps({"type": "get_resources"}).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            print(f"Error fetching resources: {e}")
            return []

    def fetch_peers_from_tracker(self):
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            conn.sendall(json.dumps({"type": "get_peers"}).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            print(f"Error fetching peers: {e}")
            return {}

    def start_peer_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        threading.Thread(target=self._accept_connections,
                         args=(server_socket,), daemon=True).start()

    def _accept_connections(self, server_socket):
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=self._handle_peer_connection,
                             args=(conn, addr), daemon=True).start()

    def _handle_peer_connection(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    return
                message = json.loads(data)
                if message["type"] == "get_resources":
                    conn.sendall(json.dumps(
                        {"resources": self.resources}).encode("utf-8"))
            except Exception as e:
                print(f"Error handling peer connection: {e}")

    def connect_to_peer(self, peer_ip, peer_port):
        try:
            return socket.create_connection((peer_ip, peer_port))
        except Exception as e:
            print(f"Failed to connect to peer: {e}")
            return None


class PeerApp(QMainWindow):
    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.initUI()

    def initUI(self):
        self.setWindowTitle("P2P File Sharing")
        self.setGeometry(100, 100, 500, 500)
        layout = QVBoxLayout()

        self.upload_button = QPushButton("Upload File")
        self.upload_button.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_button)

        self.resource_list = QListWidget()
        layout.addWidget(self.resource_list)

        self.fetch_resources_button = QPushButton("Fetch Available Resources")
        self.fetch_resources_button.clicked.connect(self.fetch_resources)
        layout.addWidget(self.fetch_resources_button)

        self.fetch_peers_button = QPushButton("Fetch Active Peers")
        self.fetch_peers_button.clicked.connect(self.fetch_peers)
        layout.addWidget(self.fetch_peers_button)

        self.peer_list = QListWidget()
        layout.addWidget(self.peer_list)

        self.message_input = QLineEdit()
        layout.addWidget(self.message_input)

        self.send_message_button = QPushButton("Send Message")
        self.send_message_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_message_button)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def upload_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.peer.add_resource(os.path.basename(file))
            self.status.append(f"File {os.path.basename(file)} uploaded.")

    def fetch_resources(self):
        resources = self.peer.fetch_resources_from_tracker()
        self.resource_list.clear()
        for resource in resources:
            self.resource_list.addItem(resource)
        self.status.append("Fetched available resources.")

    def fetch_peers(self):
        peers = self.peer.fetch_peers_from_tracker()
        self.peer_list.clear()
        for pid, info in peers.items():
            self.peer_list.addItem(f"{pid} -> {info['ip']}:{info['port']}")
        self.status.append("Fetched active peers.")

    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            self.status.append(f"Message sent: {message}")
            self.message_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    peer = Peer("peer1", "127.0.0.1", 5000, "127.0.0.1", 6000)
    gui = PeerApp(peer)
    gui.show()
    sys.exit(app.exec_())

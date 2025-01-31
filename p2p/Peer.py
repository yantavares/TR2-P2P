import sys
import socket
import threading
import json
import time
import os
import hashlib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QLineEdit, QListWidget, QLabel)

BLOCK_SIZE = 1024 * 1024  # 1MB por bloco
TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5000


class Peer:
    def __init__(self):
        self.peer_id = None
        self.host = "127.0.0.1"
        self.port = None
        self.files = {}
        self.peers = {}
        self.lock = threading.Lock()

    def connect_to_network(self, peer_id, port):
        """Configura e conecta o peer à rede P2P"""
        self.peer_id = peer_id
        self.port = int(port)

        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()

    def register_with_tracker(self):
        """Registra o peer no tracker"""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            message = json.dumps({
                "type": "register",
                "user_id": self.peer_id,
                "port": self.port,
                "resources": list(self.files.keys())
            })
            conn.sendall(message.encode("utf-8"))
            conn.close()
        except Exception as e:
            print(f"Erro ao registrar no tracker: {e}")

    def keep_alive(self):
        """Mantém a conexão ativa com o tracker"""
        def _send_keep_alive():
            while True:
                try:
                    conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
                    message = json.dumps({
                        "type": "keep_alive",
                        "user_id": self.peer_id,
                        "resources": list(self.files.keys())
                    })
                    conn.sendall(message.encode("utf-8"))
                    conn.close()
                except Exception as e:
                    print(f"Falha ao enviar keep-alive: {e}")
                time.sleep(10)

        threading.Thread(target=_send_keep_alive, daemon=True).start()

    def add_file(self, file_path):
        """Adiciona um arquivo ao compartilhamento"""
        with self.lock:
            file_size = os.path.getsize(file_path)
            blocks = []
            with open(file_path, "rb") as f:
                block_index = 0
                while chunk := f.read(BLOCK_SIZE):
                    block_hash = hashlib.sha256(chunk).hexdigest()
                    blocks.append({"index": block_index, "hash": block_hash})
                    block_index += 1
            self.files[os.path.basename(file_path)] = {
                "size": file_size, "blocks": blocks}
            self.register_with_tracker()

    def fetch_files_from_tracker(self):
        """Obtém a lista de arquivos disponíveis na rede"""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            conn.sendall(json.dumps({"type": "get_resources"}).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            print(f"Erro ao buscar arquivos: {e}")
            return []

    def fetch_peers_from_tracker(self):
        """Obtém a lista de peers ativos na rede"""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            conn.sendall(json.dumps({"type": "get_peers"}).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            print(f"Erro ao buscar peers: {e}")
            return {}

    def start_peer_server(self):
        """Inicia o servidor do peer"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        threading.Thread(target=self._accept_connections,
                         args=(server_socket,), daemon=True).start()

    def _accept_connections(self, server_socket):
        """Aceita conexões de outros peers"""
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=self._handle_peer_connection,
                             args=(conn, addr), daemon=True).start()

    def _handle_peer_connection(self, conn, addr):
        """Processa requisições de outros peers"""
        with conn:
            try:
                data = conn.recv(4096).decode("utf-8")
                if not data:
                    return
                message = json.loads(data)
                if message["type"] == "message":
                    print(f"Mensagem recebida de {addr}: {message['content']}")
            except Exception as e:
                print(f"Erro ao lidar com peer: {e}")

    def send_message(self, peer_ip, peer_port, content):
        """Envia mensagem para outro peer"""
        try:
            conn = socket.create_connection((peer_ip, int(peer_port)))
            conn.sendall(json.dumps(
                {"type": "message", "content": content}).encode("utf-8"))
            conn.close()
            print("Mensagem enviada com sucesso!")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")


class PeerApp(QMainWindow):
    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.initUI()

    def initUI(self):
        self.setWindowTitle("P2P File Sharing")
        self.setGeometry(100, 100, 600, 600)
        layout = QVBoxLayout()

        self.peer_id_input = QLineEdit()
        self.peer_id_input.setPlaceholderText("Nome do Peer")
        layout.addWidget(self.peer_id_input)

        self.peer_port_input = QLineEdit()
        self.peer_port_input.setPlaceholderText("Porta do Peer")
        layout.addWidget(self.peer_port_input)

        self.connect_button = QPushButton("Conectar à Rede P2P")
        self.connect_button.clicked.connect(self.connect_to_network)
        layout.addWidget(self.connect_button)

        self.upload_button = QPushButton("Enviar Arquivo")
        self.upload_button.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_button)

        self.fetch_peers_button = QPushButton("Listar Peers Ativos")
        self.fetch_peers_button.clicked.connect(self.fetch_peers)
        layout.addWidget(self.fetch_peers_button)

        self.peer_list = QListWidget()
        layout.addWidget(self.peer_list)

        self.message_input = QLineEdit()
        layout.addWidget(self.message_input)

        self.send_message_button = QPushButton("Enviar Mensagem")
        self.send_message_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_message_button)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def connect_to_network(self):
        peer_id = self.peer_id_input.text()
        peer_port = self.peer_port_input.text()
        self.peer.connect_to_network(peer_id, peer_port)
        self.status.append(
            f"Peer {peer_id} conectado à rede na porta {peer_port}")

    def upload_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo")
        if file:
            self.peer.add_file(file)
            self.status.append(f"Arquivo {os.path.basename(file)} enviado.")

    def fetch_peers(self):
        peers = self.peer.fetch_peers_from_tracker()
        self.peer_list.clear()
        for pid, info in peers.items():
            self.peer_list.addItem(f"{pid} -> {info['ip']}:{info['port']}")

    def send_message(self):
        peer = self.peer_list.currentItem()
        if peer:
            peer_ip, peer_port = peer.text().split(" -> ")[1].split(":")
            self.peer.send_message(
                peer_ip, peer_port, self.message_input.text())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    peer = Peer()
    gui = PeerApp(peer)
    gui.show()
    sys.exit(app.exec_())

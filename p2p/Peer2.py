import sys
import socket
import threading
import json
import time
import os
import hashlib

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QLineEdit, QListWidget, QLabel, QHBoxLayout)

BLOCK_SIZE = 1024 * 1024  # 1MB por bloco
TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5000


class Peer:
    def __init__(self):
        self.peer_id = None
        self.host = "127.0.0.1"
        self.port = None
        # Formato: nome_arquivo -> {"size": tamanho, "blocks": [{"index": int, "hash": str}, ...]}
        self.files = {}
        self.lock = threading.Lock()
        self.app = None  # Referência à interface, para exibir mensagens

    def connect_to_network(self, peer_id, port):
        """Configura e conecta o peer à rede P2P."""
        self.peer_id = peer_id
        self.port = int(port)

        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()

        if self.app:
            self.app.displaySignal.emit(
                f"Peer '{self.peer_id}' conectado na porta {self.port}")

    def register_with_tracker(self):
        """Registra o peer no tracker."""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            message = {
                "type": "register",
                "user_id": self.peer_id,
                "port": self.port,
                "resources": list(self.files.keys())
            }
            conn.sendall(json.dumps(message).encode("utf-8"))
            conn.close()
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(
                    f"Erro ao registrar no tracker: {e}")

    def keep_alive(self):
        """Mantém a conexão ativa com o tracker periodicamente."""
        def _send_keep_alive():
            while True:
                try:
                    conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
                    message = {
                        "type": "keep_alive",
                        "user_id": self.peer_id,
                        "resources": list(self.files.keys())
                    }
                    conn.sendall(json.dumps(message).encode("utf-8"))
                    conn.close()
                except Exception as e:
                    if self.app:
                        self.app.displaySignal.emit(f"Erro no keep-alive: {e}")
                time.sleep(10)
        threading.Thread(target=_send_keep_alive, daemon=True).start()

    def add_file(self, file_path):
        """Adiciona um arquivo ao compartilhamento, dividindo-o em blocos e calculando o checksum."""
        with self.lock:
            try:
                file_size = os.path.getsize(file_path)
                blocks = []
                with open(file_path, "rb") as f:
                    block_index = 0
                    while True:
                        chunk = f.read(BLOCK_SIZE)
                        if not chunk:
                            break
                        block_hash = hashlib.sha256(chunk).hexdigest()
                        blocks.append(
                            {"index": block_index, "hash": block_hash})
                        block_index += 1
                file_name = os.path.basename(file_path)
                self.files[file_name] = {"size": file_size, "blocks": blocks}
                self.register_with_tracker()
                if self.app:
                    self.app.displaySignal.emit(
                        f"Arquivo '{file_name}' compartilhado com sucesso!")
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Erro ao compartilhar arquivo: {e}")

    def fetch_files_from_tracker(self):
        """
        Obtém a lista de arquivos disponíveis na rede a partir do tracker.

        O tracker pode retornar:
         - Uma lista de dicionários com chaves: file_name, peer_id, ip, port; ou
         - Um dicionário onde as chaves são os nomes dos arquivos e os valores são informações do peer.
        """
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            request = {"type": "get_resources"}
            conn.sendall(json.dumps(request).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao buscar arquivos: {e}")
            return []

    def fetch_peers_from_tracker(self):
        """
        Obtém a lista de peers ativos na rede a partir do tracker.
        Espera-se um dicionário no formato: { peer_id: {"ip": <ip>, "port": <porta>}, ... }
        """
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            request = {"type": "get_peers"}
            conn.sendall(json.dumps(request).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao buscar peers: {e}")
            return {}

    def start_peer_server(self):
        """Inicia o servidor do peer para aceitar conexões de outros peers."""
        def _accept_connections(server_socket):
            while True:
                try:
                    conn, addr = server_socket.accept()
                    threading.Thread(target=self._handle_peer_connection,
                                     args=(conn, addr), daemon=True).start()
                except Exception as e:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Erro ao aceitar conexão: {e}")
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            threading.Thread(target=_accept_connections, args=(
                server_socket,), daemon=True).start()
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao iniciar servidor: {e}")

    def _handle_peer_connection(self, conn, addr):
        """Processa requisições de outros peers."""
        with conn:
            try:
                data = conn.recv(4096)
                if not data:
                    return
                message = json.loads(data.decode("utf-8"))
                msg_type = message.get("type")
                if msg_type == "message":
                    content = message.get("content", "")
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Mensagem recebida de {addr}: {content}")
                elif msg_type == "get_file_metadata":
                    file_name = message.get("file_name")
                    if file_name in self.files:
                        response = {"status": "ok",
                                    "metadata": self.files[file_name]}
                    else:
                        response = {"status": "error",
                                    "message": "Arquivo não encontrado"}
                    conn.sendall(json.dumps(response).encode("utf-8"))
                elif msg_type == "get_block":
                    file_name = message.get("file_name")
                    block_index = message.get("block_index")
                    if file_name in self.files:
                        try:
                            with open(file_name, "rb") as f:
                                f.seek(block_index * BLOCK_SIZE)
                                chunk = f.read(BLOCK_SIZE)
                            response = {
                                "status": "ok", "block_index": block_index, "data": chunk.hex()}
                        except Exception as e:
                            response = {"status": "error", "message": str(e)}
                    else:
                        response = {"status": "error",
                                    "message": "Arquivo não encontrado"}
                    conn.sendall(json.dumps(response).encode("utf-8"))
                else:
                    # Outros tipos de mensagem podem ser tratados aqui
                    pass
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Erro ao lidar com conexão de {addr}: {e}")

    def send_message(self, peer_ip, peer_port, content):
        """Envia mensagem para outro peer."""
        try:
            conn = socket.create_connection((peer_ip, int(peer_port)))
            msg = {"type": "message", "content": content}
            conn.sendall(json.dumps(msg).encode("utf-8"))
            conn.close()
            if self.app:
                self.app.displaySignal.emit("Mensagem enviada com sucesso!")
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao enviar mensagem: {e}")

    def download_file(self, file_name, source_peer_ip, source_peer_port, dest_path):
        """Realiza o download de um arquivo a partir de outro peer utilizando múltiplas conexões para baixar os blocos."""
        def _download():
            try:
                # Solicita metadata do arquivo no peer doador
                conn = socket.create_connection(
                    (source_peer_ip, int(source_peer_port)))
                request = {"type": "get_file_metadata", "file_name": file_name}
                conn.sendall(json.dumps(request).encode("utf-8"))
                resp = conn.recv(4096).decode("utf-8")
                conn.close()
                response = json.loads(resp)
                if response.get("status") != "ok":
                    if self.app:
                        self.app.displaySignal.emit(
                            "Erro: " + response.get("message", ""))
                    return
                metadata = response.get("metadata")
                total_blocks = len(metadata["blocks"])
                file_size = metadata["size"]
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        "Erro ao obter metadata: " + str(e))
                return

            blocks_data = [None] * total_blocks
            lock = threading.Lock()
            threads = []

            def download_block(i):
                try:
                    conn = socket.create_connection(
                        (source_peer_ip, int(source_peer_port)))
                    req = {"type": "get_block",
                           "file_name": file_name, "block_index": i}
                    conn.sendall(json.dumps(req).encode("utf-8"))
                    resp_data = b""
                    while True:
                        part = conn.recv(8192)
                        if not part:
                            break
                        resp_data += part
                    conn.close()
                    resp_str = resp_data.decode("utf-8")
                    resp_json = json.loads(resp_str)
                    if resp_json.get("status") == "ok":
                        data_hex = resp_json.get("data")
                        data_bytes = bytes.fromhex(data_hex)
                        calc_hash = hashlib.sha256(data_bytes).hexdigest()
                        expected_hash = metadata["blocks"][i]["hash"]
                        if calc_hash != expected_hash:
                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Checksum falhou para o bloco {i}")
                            return
                        with lock:
                            blocks_data[i] = data_bytes
                    else:
                        if self.app:
                            self.app.displaySignal.emit(
                                f"Erro no bloco {i}: " + resp_json.get("message", ""))
                except Exception as ex:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Exceção no bloco {i}: " + str(ex))

            for i in range(total_blocks):
                t = threading.Thread(target=download_block, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            if None in blocks_data:
                if self.app:
                    self.app.displaySignal.emit(
                        "Falha no download: alguns blocos não foram baixados")
                return

            file_data = b"".join(blocks_data)
            if len(file_data) != file_size:
                if self.app:
                    self.app.displaySignal.emit(
                        "Tamanho do arquivo incorreto após reassemblagem")
                return

            try:
                save_path = os.path.join(dest_path, file_name)
                with open(save_path, "wb") as f:
                    f.write(file_data)
                if self.app:
                    self.app.displaySignal.emit(
                        f"Arquivo '{file_name}' baixado com sucesso e salvo em {save_path}")
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        "Erro ao salvar arquivo: " + str(e))

        threading.Thread(target=_download, daemon=True).start()


class PeerApp(QMainWindow):
    # Sinal para atualizar mensagens na interface (garante atualização na thread principal)
    displaySignal = QtCore.pyqtSignal(str)

    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.peer.app = self  # Permite que o objeto peer envie mensagens para a interface
        self.initUI()

    def initUI(self):
        self.setWindowTitle("P2P File Sharing")
        self.setGeometry(100, 100, 700, 700)

        main_layout = QVBoxLayout()

        # Conexão do peer
        connection_layout = QHBoxLayout()
        self.peer_id_input = QLineEdit()
        self.peer_id_input.setPlaceholderText("Nome do Peer")
        connection_layout.addWidget(QLabel("Peer:"))
        connection_layout.addWidget(self.peer_id_input)

        self.peer_port_input = QLineEdit()
        self.peer_port_input.setPlaceholderText("Porta do Peer")
        connection_layout.addWidget(QLabel("Porta:"))
        connection_layout.addWidget(self.peer_port_input)

        self.connect_button = QPushButton("Conectar à Rede P2P")
        self.connect_button.clicked.connect(self.connect_to_network)
        connection_layout.addWidget(self.connect_button)
        main_layout.addLayout(connection_layout)

        # Upload de arquivo
        self.upload_button = QPushButton("Compartilhar Arquivo")
        self.upload_button.clicked.connect(self.upload_file)
        main_layout.addWidget(self.upload_button)

        # Listagem de peers ativos
        peers_layout = QVBoxLayout()
        self.fetch_peers_button = QPushButton("Listar Peers Ativos")
        self.fetch_peers_button.clicked.connect(self.fetch_peers)
        peers_layout.addWidget(self.fetch_peers_button)

        self.peer_list = QListWidget()
        peers_layout.addWidget(self.peer_list)
        main_layout.addLayout(peers_layout)

        # Listagem de arquivos disponíveis
        files_layout = QVBoxLayout()
        self.fetch_files_button = QPushButton("Listar Arquivos Disponíveis")
        self.fetch_files_button.clicked.connect(self.fetch_files)
        files_layout.addWidget(self.fetch_files_button)

        self.file_list = QListWidget()
        files_layout.addWidget(self.file_list)
        main_layout.addLayout(files_layout)

        # Botão para download do arquivo selecionado
        self.download_button = QPushButton("Baixar Arquivo Selecionado")
        self.download_button.clicked.connect(self.download_file)
        main_layout.addWidget(self.download_button)

        # Envio de mensagens para peers
        message_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Digite a mensagem")
        message_layout.addWidget(self.message_input)

        self.send_message_button = QPushButton(
            "Enviar Mensagem para Peer Selecionado")
        self.send_message_button.clicked.connect(self.send_message)
        message_layout.addWidget(self.send_message_button)
        main_layout.addLayout(message_layout)

        # Área de status e mensagens
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        main_layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.displaySignal.connect(self.update_status)

    def update_status(self, text):
        """Adiciona mensagens à área de status."""
        self.status.append(text)

    def connect_to_network(self):
        peer_id = self.peer_id_input.text().strip()
        peer_port = self.peer_port_input.text().strip()
        if peer_id and peer_port:
            self.peer.connect_to_network(peer_id, peer_port)
        else:
            self.update_status("Preencha o nome e a porta do Peer.")

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo")
        if file_path:
            self.peer.add_file(file_path)

    def fetch_peers(self):
        peers = self.peer.fetch_peers_from_tracker()
        self.peer_list.clear()
        for pid, info in peers.items():
            self.peer_list.addItem(f"{pid} -> {info['ip']}:{info['port']}")

    def fetch_files(self):
        files = self.peer.fetch_files_from_tracker()
        self.file_list.clear()
        # Verifica se o retorno é um dicionário ou uma lista
        if isinstance(files, dict):
            # Se as chaves forem nomes dos arquivos e os valores dicionários com informações do peer
            for file_name, info in files.items():
                # Se info já for um dicionário com os campos esperados:
                if isinstance(info, dict):
                    item_text = f"{file_name} -> {info.get('peer_id', 'N/A')}@{
                        info.get('ip', 'N/A')}:{info.get('port', 'N/A')}"
                else:
                    item_text = str(info)
                self.file_list.addItem(item_text)
        elif isinstance(files, list):
            for file_info in files:
                if isinstance(file_info, dict):
                    item_text = f"{file_info.get('file_name', 'unknown')} -> {file_info.get(
                        'peer_id', 'N/A')}@{file_info.get('ip', 'N/A')}:{file_info.get('port', 'N/A')}"
                else:
                    item_text = str(file_info)
                self.file_list.addItem(item_text)
        else:
            self.file_list.addItem(str(files))

    def download_file(self):
        """
        Faz o download do arquivo selecionado.
        O item deve ter o formato: "nome_arquivo -> peer_id@ip:porta"
        """
        item = self.file_list.currentItem()
        if item:
            try:
                text = item.text()
                file_name, rest = text.split(" -> ")
                # O formato esperado: "peer_id@ip:porta"
                peer_addr = rest.split("@")[1]
                peer_ip, peer_port = peer_addr.split(":")
            except Exception as e:
                self.update_status(
                    "Formato de item inválido para download.", e)
                return

            dest_path = QFileDialog.getExistingDirectory(
                self, "Selecionar Pasta para Salvar")
            if dest_path:
                self.peer.download_file(
                    file_name, peer_ip, peer_port, dest_path)
            else:
                self.update_status(
                    "Download cancelado: pasta não selecionada.")
        else:
            self.update_status("Selecione um arquivo para download.")

    def send_message(self):
        """Envia mensagem para o peer selecionado na lista de peers."""
        item = self.peer_list.currentItem()
        if item:
            try:
                text = item.text()  # Espera-se o formato "peer_id -> ip:porta"
                parts = text.split(" -> ")
                addr = parts[1]
                peer_ip, peer_port = addr.split(":")
            except Exception as e:
                self.update_status(
                    "Formato de item inválido para envio de mensagem.")
                return

            content = self.message_input.text().strip()
            if content:
                self.peer.send_message(peer_ip, peer_port, content)
            else:
                self.update_status("Digite uma mensagem para enviar.")
        else:
            self.update_status("Selecione um peer para enviar mensagem.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    peer = Peer()
    gui = PeerApp(peer)
    gui.show()
    sys.exit(app.exec_())

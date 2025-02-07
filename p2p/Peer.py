import sys
import socket
import threading
import json
import time
import os
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QLineEdit, QListWidget,
                             QLabel, QHBoxLayout, QCheckBox)

BLOCK_SIZE = 1024 * 1024
TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5001

# Função auxiliar para receber uma mensagem JSON completa utilizando um delimitador.


def recv_json(sock, delimiter=b"\n"):
    buffer = b""
    while True:
        part = sock.recv(8192)
        if not part:
            break
        buffer += part
        if delimiter in buffer:
            break
    if delimiter in buffer:
        data, _ = buffer.split(delimiter, 1)
    else:
        data = buffer
    return json.loads(data.decode("utf-8"))


class Peer:
    def __init__(self):
        self.peer_id = None
        self.host = "127.0.0.1"
        self.port = None
        self.files = {}
        self.resources = {}
        self.max_connections = 4  # Valor padrão para nível 1
        self.level = 1           # Nível inicial
        self.xp = 0              # Pontos de experiência iniciais
        self.level_threshold = 50  # XP necessária para subir de nível
        self.semaphore = threading.Semaphore(self.max_connections)
        self.lock = threading.Lock()
        self.app = None

    def set_max_connections(self, max_conn):
        """Atualiza o número máximo de conexões simultâneas."""
        self.max_connections = max_conn
        self.semaphore = threading.Semaphore(max_conn)

    def connect_to_network(self, peer_id, port):
        self.peer_id = peer_id
        self.port = int(port)
        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()
        if self.app:
            self.app.displaySignal.emit(
                f"Peer '{self.peer_id}' (Lv. {self.level}) conectado na porta {self.port}"
            )

    def register_with_tracker(self):
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            message = {
                "type": "register",
                "user_id": self.peer_id,
                "port": self.port,
                "resources": self.resources,
                "level": self.level
            }
            conn.sendall(json.dumps(message).encode("utf-8"))
            conn.close()
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(
                    f"Erro ao registrar no tracker: {e}")

    def keep_alive(self):
        def _send_keep_alive():
            while True:
                try:
                    conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
                    message = {
                        "type": "keep_alive",
                        "user_id": self.peer_id,
                        "resources": self.resources
                    }
                    conn.sendall(json.dumps(message).encode("utf-8"))
                    conn.close()
                except Exception as e:
                    if self.app:
                        self.app.displaySignal.emit(f"Erro no keep-alive: {e}")
                time.sleep(10)
        threading.Thread(target=_send_keep_alive, daemon=True).start()

    def add_file(self, file_path):
        """Lê o arquivo em blocos, registra-o e atualiza XP e nível."""
        try:
            file_size = os.path.getsize(file_path)
            blocks = []
            index = 0
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(BLOCK_SIZE)
                    if not chunk:
                        break
                    block_hash = hashlib.sha256(chunk).hexdigest()
                    blocks.append({"index": index, "hash": block_hash})
                    index += 1
            file_name = os.path.basename(file_path)
            self.files[file_name] = {"size": file_size, "blocks": blocks}
            self.resources[file_name] = list(range(len(blocks)))

            # Atualiza XP: cada bloco adicionado confere 1 ponto de XP.
            xp_ganho = len(blocks)
            self.xp += xp_ganho

            # Calcula o novo nível: cada 100 XP equivale a um nível extra.
            novo_nivel = 1 + self.xp // self.level_threshold
            if novo_nivel > self.level:
                self.level = novo_nivel
                self.max_connections = 4 + (self.level - 1)
                if self.app:
                    self.app.displaySignal.emit(
                        f"Nível atualizado: {self.level}. Máx. conexões agora: {self.max_connections}.")

            # Re-registra para atualizar as informações no tracker.
            self.register_with_tracker()

            if self.app:
                self.app.displaySignal.emit(
                    f"Arquivo '{file_name}' compartilhado com sucesso. XP ganho: {xp_ganho}. Total XP: {self.xp}.")
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(
                    f"Erro ao compartilhar arquivo: {e}")

    def fetch_peers_from_tracker(self):
        """Consulta o tracker para obter a lista de peers ativos."""
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

    def fetch_resources_from_tracker(self):
        """Consulta o tracker para obter a lista de arquivos disponíveis."""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            request = {"type": "get_resources"}
            conn.sendall(json.dumps(request).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao buscar recursos: {e}")
            return []

    def get_file_peers(self, file_name):
        """Consulta o tracker para obter a lista de peers que possuem o arquivo e seus blocos."""
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            request = {"type": "get_file_peers", "file_name": file_name}
            conn.sendall(json.dumps(request).encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            return json.loads(response)
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(
                    f"Erro ao buscar peers para '{file_name}': {e}")
            return []

    def start_peer_server(self):
        def _accept_connections(server_socket):
            while True:
                try:
                    conn, addr = server_socket.accept()
                    threading.Thread(target=self._handle_peer_connection, args=(
                        conn, addr), daemon=True).start()
                except Exception as e:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Erro ao aceitar conexão: {e}")
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((self.host, self.port))
            server_socket.listen(self.max_connections)
            threading.Thread(target=_accept_connections, args=(
                server_socket,), daemon=True).start()
        except Exception as e:
            if self.app:
                self.app.displaySignal.emit(f"Erro ao iniciar servidor: {e}")

    def _handle_peer_connection(self, conn, addr):
        """Permite múltiplas requisições na mesma conexão."""
        with conn:
            while True:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    try:
                        message = json.loads(data.decode("utf-8"))
                    except json.JSONDecodeError:
                        error_msg = {"status": "error",
                                     "message": "JSON inválido"}
                        conn.sendall(
                            (json.dumps(error_msg) + "\n").encode("utf-8"))
                        continue

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
                        conn.sendall(
                            (json.dumps(response) + "\n").encode("utf-8"))
                    elif msg_type == "get_block":
                        file_name = message.get("file_name")
                        block_index = message.get("block_index")
                        try:
                            if file_name in self.files:
                                with open(file_name, "rb") as f:
                                    f.seek(block_index * BLOCK_SIZE)
                                    chunk = f.read(BLOCK_SIZE)
                                response = {
                                    "status": "ok", "block_index": block_index, "data": chunk.hex()}
                            else:
                                response = {"status": "error",
                                            "message": "Arquivo não encontrado"}
                            conn.sendall(
                                (json.dumps(response) + "\n").encode("utf-8"))
                        except Exception as e:
                            response = {"status": "error", "message": str(e)}
                            conn.sendall(
                                (json.dumps(response) + "\n").encode("utf-8"))
                    else:
                        pass
                except Exception as e:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Erro ao lidar com conexão de {addr}: {e}")
                    break

    def _choose_peer_for_block(self, block_index, file_peers, excludes_peers):
        candidatos = [
            peer for peer in file_peers
            if block_index in peer.get("blocks", [])
            and peer["peer_id"] not in excludes_peers
            and peer["peer_id"] != self.peer_id
        ]
        return random.choice(candidatos) if candidatos else None

    def download_file(self, file_name, dest_path):
        def _download():
            if self.app:
                self.app.displaySignal.emit(
                    f"Iniciando download do arquivo '{file_name}'...")
            file_peers = self.get_file_peers(file_name)
            if not file_peers:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Nenhum peer possui o arquivo '{file_name}'")
                return

            metadata = None
            for peer in file_peers:
                try:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Tentando obter metadata de {peer['peer_id']} ({peer['ip']}:{peer['port']})...")
                    conn = socket.create_connection(
                        (peer["ip"], int(peer["port"])), timeout=10)
                    request = {"type": "get_file_metadata",
                               "file_name": file_name}
                    conn.sendall((json.dumps(request) + "\n").encode("utf-8"))
                    response = recv_json(conn)
                    conn.close()
                    if response.get("status") == "ok":
                        metadata = response.get("metadata")
                        if self.app:
                            self.app.displaySignal.emit(
                                f"Metadata obtida de {peer['peer_id']}.")
                        break
                except Exception as ex:
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Falha ao obter metadata de {peer['peer_id']}: {ex}")
                    continue
            if metadata is None:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Não foi possível obter metadata para '{file_name}'")
                return

            total_blocks = len(metadata["blocks"])
            file_size = metadata["size"]
            blocks_data = [None] * total_blocks

            start_time = time.time()

            def download_block(i):
                max_retries = 3
                attempt = 0
                excluded_peers = set()
                while attempt < max_retries:
                    peer_for_block = self._choose_peer_for_block(
                        i, file_peers, excluded_peers)
                    if not peer_for_block:
                        if excluded_peers:
                            excluded_peers.clear()
                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Nenhum outro peer disponível para o bloco {i}. Resetando tentativas...")
                            continue
                        else:
                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Nenhum peer disponível para o bloco {i}")
                            return
                    try:
                        conn = socket.create_connection(
                            (peer_for_block["ip"], int(peer_for_block["port"])), timeout=10)
                        req = {"type": "get_block",
                               "file_name": file_name, "block_index": i}
                        conn.sendall((json.dumps(req) + "\n").encode("utf-8"))
                        response = recv_json(conn)
                        conn.close()
                        if response.get("status") == "ok":
                            data_hex = response.get("data")
                            blocks_data[i] = bytes.fromhex(data_hex)
                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Bloco {i} baixado de {peer_for_block['peer_id']}.")
                                time.sleep(0.1)
                            return
                        else:
                            attempt += 1
                            excluded_peers.add(peer_for_block["peer_id"])
                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Tentativa {attempt}/{max_retries} falhou para o bloco {i}: {response.get('message')}")
                            time.sleep(2)
                    except Exception as ex:
                        attempt += 1
                        excluded_peers.add(peer_for_block["peer_id"])
                        if self.app:
                            self.app.displaySignal.emit(
                                f"Erro na tentativa {attempt}/{max_retries} para o bloco {i}: {ex}")
                        time.sleep(2)

            with ThreadPoolExecutor(max_workers=self.max_connections) as executor:
                futures = [executor.submit(download_block, i)
                           for i in range(total_blocks)]
                for future in futures:
                    future.result()

            end_time = time.time()
            total_time = end_time - start_time

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
                with self.lock:
                    self.files[file_name] = metadata
                    self.resources[file_name] = list(range(total_blocks))
                self.register_with_tracker()
                if self.app:
                    self.app.displaySignal.emit(
                        f"Download concluído em {total_time:.2f} segundos. Arquivo salvo em {save_path}")
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        "Erro ao salvar arquivo: " + str(e))

        threading.Thread(target=_download, daemon=True).start()


class PeerApp(QMainWindow):
    displaySignal = QtCore.pyqtSignal(str)

    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.peer.app = self
        self.initUI()

    def initUI(self):
        self.setWindowTitle("TR2 - P2P")
        self.setGeometry(100, 100, 750, 700)
        main_layout = QVBoxLayout()

        # Área de conexão
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

        # Configuração do número máximo de conexões
        connections_layout = QHBoxLayout()
        self.max_conn_input = QLineEdit()
        self.max_conn_input.setPlaceholderText("Máx. Conexões")
        self.max_conn_input.setText(str(self.peer.max_connections))
        connections_layout.addWidget(QLabel("Máx. Conexões:"))
        connections_layout.addWidget(self.max_conn_input)
        self.set_max_conn_button = QPushButton("Definir")
        self.set_max_conn_button.clicked.connect(self.set_max_connections)
        connections_layout.addWidget(self.set_max_conn_button)
        main_layout.addLayout(connections_layout)

        # Upload de arquivo
        self.upload_button = QPushButton("Compartilhar Arquivo")
        self.upload_button.clicked.connect(self.upload_file)
        main_layout.addWidget(self.upload_button)

        # Listar peers ativos
        peers_layout = QVBoxLayout()
        self.fetch_peers_button = QPushButton("Listar Peers Ativos")
        self.fetch_peers_button.clicked.connect(self.fetch_peers)
        peers_layout.addWidget(self.fetch_peers_button)
        self.peer_list = QListWidget()
        peers_layout.addWidget(self.peer_list)
        main_layout.addLayout(peers_layout)

        # Listar arquivos disponíveis com detalhes opcionais
        files_layout = QVBoxLayout()
        self.fetch_files_button = QPushButton("Listar Arquivos Disponíveis")
        self.fetch_files_button.clicked.connect(self.fetch_files)
        files_layout.addWidget(self.fetch_files_button)
        self.details_checkbox = QCheckBox(
            "Mostrar detalhes (quem possui quais blocos)")
        files_layout.addWidget(self.details_checkbox)
        self.file_list = QListWidget()
        files_layout.addWidget(self.file_list)
        main_layout.addLayout(files_layout)

        # Botão para download do arquivo selecionado
        self.download_button = QPushButton("Baixar Arquivo Selecionado")
        self.download_button.clicked.connect(self.download_file)
        main_layout.addWidget(self.download_button)

        # Envio de mensagem para peer selecionado
        message_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Digite a mensagem")
        message_layout.addWidget(self.message_input)
        self.send_message_button = QPushButton(
            "Enviar Mensagem para Peer Selecionado")
        self.send_message_button.clicked.connect(self.send_message)
        message_layout.addWidget(self.send_message_button)
        main_layout.addLayout(message_layout)

        # Área de status
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        main_layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.displaySignal.connect(self.update_status)

    def update_status(self, text, *args):
        if args:
            text += " " + " ".join(str(a) for a in args)
        self.status.append(text)

    def connect_to_network(self):
        peer_id = self.peer_id_input.text().strip()
        peer_port = self.peer_port_input.text().strip()
        if not peer_port.isdigit():
            self.update_status("A porta do Peer deve ser um número.")
            return
        if peer_id and peer_port:
            self.peer.connect_to_network(peer_id, peer_port)
        else:
            self.update_status("Preencha o nome e a porta do Peer.")

    def set_max_connections(self):
        try:
            max_conn = int(self.max_conn_input.text().strip())
            if max_conn < 1:
                raise ValueError("O número mínimo de conexões deve ser 1.")
            if max_conn > 4 + self.peer.level:
                raise ValueError(
                    "O número máximo de conexões deve ser 4 + nível do Peer.")
            self.peer.set_max_connections(max_conn)
            self.update_status(
                f"Número máximo de conexões ajustado para {max_conn}.")
        except ValueError as e:
            self.update_status(f"Valor inválido para conexões: {e}")

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo")
        if file_path:
            self.peer.add_file(file_path)

    def fetch_peers(self):
        peers = self.peer.fetch_peers_from_tracker()
        self.peer_list.clear()
        for pid, info in peers.items():
            if pid == self.peer.peer_id:
                continue
            # Exibe o nível do peer ao lado do nome
            self.peer_list.addItem(
                f"{pid} (Lv. {info.get('level', 1)}) -> {info['ip']}:{info['port']}")

    def fetch_files(self):
        files = self.peer.fetch_resources_from_tracker()
        self.file_list.clear()
        if isinstance(files, list):
            for f in files:
                if self.details_checkbox.isChecked():
                    file_peers = self.peer.get_file_peers(f)
                    details = []
                    for peer in file_peers:
                        details.append(
                            f"{peer['peer_id']}[{','.join(str(b) for b in peer['blocks'])}]")
                    item_text = f"{f} -> " + " | ".join(details)
                else:
                    item_text = f
                self.file_list.addItem(item_text)
        else:
            self.file_list.addItem(str(files))

    def download_file(self):
        item = self.file_list.currentItem()
        if item:
            text = item.text()
            file_name = text.split(" -> ")[0].strip()
            dest_path = QFileDialog.getExistingDirectory(
                self, "Selecionar Pasta para Salvar")
            if dest_path:
                self.peer.download_file(file_name, dest_path)
            else:
                self.update_status(
                    "Download cancelado: pasta não selecionada.")
        else:
            self.update_status("Selecione um arquivo para download.")

    def send_message(self):
        item = self.peer_list.currentItem()
        if item:
            try:
                text = item.text()  # Formato: "peer_id (Lv. x) -> ip:porta"
                parts = text.split(" -> ")
                addr = parts[1]
                peer_ip, peer_port = addr.split(":")
            except Exception as e:
                self.update_status(
                    "Formato de item inválido para envio de mensagem:", e)
                return
            content = self.message_input.text().strip()
            if content:
                try:
                    conn = socket.create_connection((peer_ip, int(peer_port)))
                    msg = {"type": "message", "content": content}
                    conn.sendall(json.dumps(msg).encode("utf-8"))
                    conn.close()
                    self.update_status("Mensagem enviada com sucesso!")
                except Exception as e:
                    self.update_status("Erro ao enviar mensagem:", e)
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

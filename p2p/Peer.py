import sys
import socket
import threading
import json
import time
import os
import hashlib
import random

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QLineEdit, QListWidget,
                             QLabel, QHBoxLayout, QCheckBox)

BLOCK_SIZE = 1024 * 1024  # 1 MB por bloco
TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 5001


class Peer:
    def __init__(self):
        self.peer_id = None
        self.host = "127.0.0.1"
        self.port = None
        # self.files: chave = nome do arquivo, valor = { "size": int, "blocks": [ { "index": int, "hash": str }, ... ] }
        self.files = {}
        # resources: dicionário com informações sobre os arquivos que este peer está compartilhando,
        # no formato: { file_name: [lista de índices dos blocos que possui], ... }
        self.resources = {}
        self.max_connections = 1  # Define o limite de conexões simultâneas
        self.active_connections = 0
        self.lock = threading.Lock()
        self.app = None

    def connect_to_network(self, peer_id, port):
        self.peer_id = peer_id
        self.port = int(port)
        # Registra com os recursos atuais (se houver)
        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()
        if self.app:
            self.app.displaySignal.emit(
                f"Peer '{self.peer_id}' conectado na porta {self.port}")

    def register_with_tracker(self):
        try:
            conn = socket.create_connection((TRACKER_IP, TRACKER_PORT))
            message = {
                "type": "register",
                "user_id": self.peer_id,
                "port": self.port,
                "resources": self.resources
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
        """Divide o arquivo em blocos, calcula os checksums e adiciona-o aos arquivos compartilhados."""
        with self.lock:
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
                # O peer possui o arquivo completo, portanto registra todos os índices
                self.resources[file_name] = list(range(len(blocks)))
                self.register_with_tracker()
                if self.app:
                    self.app.displaySignal.emit(
                        f"Arquivo '{file_name}' compartilhado com sucesso!")
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
        """Consulta o tracker para obter a lista de peers que possuem o arquivo e quais blocos cada um possui."""
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
                    threading.Thread(target=self._handle_peer_connection,
                                     args=(conn, addr), daemon=True).start()
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
        """Lida com requisições de outros peers (envio de metadata ou blocos)."""
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
                    # Outros tipos de mensagem podem ser tratados aqui.
                    pass
            except Exception as e:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Erro ao lidar com conexão de {addr}: {e}")

    def _choose_peer_for_block(self, block_index, file_peers, excludes_peers):
        """Escolhe aleatoriamente um peer dentre aqueles que possuem o bloco, excluindo os peers especificados."""
        candidatos = [
            peer for peer in file_peers if block_index in peer.get("blocks", []) and peer["peer_id"] not in excludes_peers
        ]
        if candidatos:
            return random.choice(candidatos)
        return None

    def download_file(self, file_name, dest_path):
        """
        Realiza o download distribuído de um arquivo:
          1. Consulta o tracker para obter os peers com o arquivo e os blocos disponíveis.
          2. Solicita a metadata (de um dos peers) para saber o total de blocos, tamanho e checksums.
          3. Para cada bloco, escolhe aleatoriamente um peer que o possua e inicia uma thread para baixá-lo.
          4. Após baixar todos os blocos, reagrupa e salva o arquivo.
          5. Atualiza seus recursos para compartilhar os blocos baixados (seeder parcial ou completo).
        """
        def _download():
            if self.app:
                self.app.displaySignal.emit(
                    f"Iniciando download do arquivo '{file_name}'...")
            # Obtém a lista de peers que possuem o arquivo
            file_peers = self.get_file_peers(file_name)
            if not file_peers:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Nenhum peer possui o arquivo '{file_name}'")
                return

            # Obtém a metadata do arquivo a partir de um dos peers
            metadata = None
            for peer in file_peers:
                try:
                    if self.app:
                        self.app.displaySignal.emit(f"Tentando obter metadata de {
                                                    peer['peer_id']} ({peer['ip']}:{peer['port']})...")
                    conn = socket.create_connection(
                        (peer["ip"], int(peer["port"])))
                    request = {"type": "get_file_metadata",
                               "file_name": file_name}
                    conn.sendall(json.dumps(request).encode("utf-8"))
                    resp = conn.recv(4096).decode("utf-8")
                    conn.close()
                    response = json.loads(resp)
                    if response.get("status") == "ok":
                        metadata = response.get("metadata")
                        if self.app:
                            self.app.displaySignal.emit(
                                f"Metadata obtida de {peer['peer_id']}.")
                        break
                except Exception as ex:
                    if self.app:
                        self.app.displaySignal.emit(f"Falha ao obter metadata de {
                                                    peer['peer_id']}: {ex}")
                    continue
            if metadata is None:
                if self.app:
                    self.app.displaySignal.emit(
                        f"Não foi possível obter metadata para '{file_name}'")
                return

            total_blocks = len(metadata["blocks"])
            file_size = metadata["size"]
            file_size_kb = file_size / 1024  # Convertendo bytes para KB
            blocks_data = [None] * total_blocks
            lock = threading.Lock()
            threads = []
            start_time = time.time()

            def download_block(i):
                """
                Baixa um bloco específico, tentando novamente se falhar e alternando peers se possível.
                """
                max_retries = 3  # Número máximo de tentativas
                attempt = 0
                excluded_peers = set()  # Peers que falharam anteriormente

                while attempt < max_retries:
                    # Escolhe um peer para baixar o bloco
                    peer_for_block = self._choose_peer_for_block(i, file_peers, excluded_peers)

                    # Se não houver mais peers disponíveis, limpamos a lista e tentamos novamente
                    if not peer_for_block:
                        if excluded_peers:  # Se já excluímos peers antes, devemos tentar novamente com eles
                            excluded_peers.clear()
                            self.app.displaySignal.emit(f"Nenhum outro peer disponível para o bloco {i}. Resetando tentativas...")
                            continue
                        else:
                            if self.app:
                                self.app.displaySignal.emit(f"Nenhum peer disponível para o bloco {i}")
                            return
                    
                    if self.app:
                        self.app.displaySignal.emit(
                            f"Conectando para baixar bloco {i} de {peer_for_block['peer_id']} ({peer_for_block['ip']}:{peer_for_block['port']})..."
                        )

                    try:
                        conn = socket.create_connection((peer_for_block["ip"], int(peer_for_block["port"])), timeout=10)
                        req = {"type": "get_block", "file_name": file_name, "block_index": i}

                        conn.sendall(json.dumps(req).encode("utf-8"))
                        resp_data = b""

                        while True:
                            part = conn.recv(8192)
                            if not part:
                                break
                            resp_data += part

                        conn.close()

                        resp_json = json.loads(resp_data.decode("utf-8"))
                        if resp_json.get("status") == "ok":
                            data_hex = resp_json.get("data")
                            data_bytes = bytes.fromhex(data_hex)

                            # Verifica a integridade do bloco via hash SHA-256
                            calc_hash = hashlib.sha256(data_bytes).hexdigest()
                            expected_hash = metadata["blocks"][i]["hash"]
                            if calc_hash != expected_hash:
                                if self.app:
                                    self.app.displaySignal.emit(f"Checksum falhou para o bloco {i}, tentando novamente...")
                                attempt += 1
                                continue  # Não excluímos o peer, apenas tentamos novamente

                            # Armazena o bloco com segurança
                            with lock:
                                blocks_data[i] = data_bytes

                            if self.app:
                                self.app.displaySignal.emit(
                                    f"Bloco {i} baixado com sucesso."
                                )
                            return  # Sai da função se o bloco foi baixado com sucesso

                    except Exception as ex:
                        attempt += 1

                        # Se houver outros peers disponíveis, excluímos esse da lista de tentativas
                        if len(file_peers) > 1:
                            excluded_peers.add(peer_for_block["peer_id"])

                        if self.app:
                            self.app.displaySignal.emit(
                                f"Tentativa {attempt}/{max_retries} falhou para o bloco {i}: {ex}"
                            )
                        time.sleep(2)  # Aguarda 2 segundos antes de tentar novamente

                # Se todas as tentativas falharem
                if self.app:
                    self.app.displaySignal.emit(f"Erro crítico: Falha ao baixar o bloco {i} após {max_retries} tentativas.")

            # Cria e inicia uma thread para cada bloco
            for i in range(total_blocks):
                t = threading.Thread(target=download_block, args=(i,))
                threads.append(t)
                t.start()

            # Aguarda o término de todas as threads
            for t in threads:
                t.join()

            end_time = time.time()
            total_time = end_time - start_time  # Tempo total de download

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

                # Calcula a velocidade média do download
                avg_speed = (file_size_kb / total_time) if total_time > 0 else 0

                if self.app:
                    self.app.displaySignal.emit(
                        f"Download concluído em {total_time:.2f} segundos."
                    )
                    self.app.displaySignal.emit(
                        f"Velocidade média do download: {avg_speed:.2f} KB/s"
                    )

                # Atualiza os recursos para indicar que este peer agora possui o arquivo completo
                with self.lock:
                    self.files[file_name] = metadata
                    self.resources[file_name] = list(range(total_blocks))
                self.register_with_tracker()
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
        self.setWindowTitle("P2P File Sharing")
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
        self.max_conn_input.setText(str(self.peer.max_connections))  # Valor inicial
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

        # Listar peers ativos (excluindo o próprio usuário)
        peers_layout = QVBoxLayout()
        self.fetch_peers_button = QPushButton("Listar Peers Ativos")
        self.fetch_peers_button.clicked.connect(self.fetch_peers)
        peers_layout.addWidget(self.fetch_peers_button)
        self.peer_list = QListWidget()
        peers_layout.addWidget(self.peer_list)
        main_layout.addLayout(peers_layout)

        # Listar arquivos disponíveis com opção de detalhes
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

        # Download do arquivo selecionado
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
            self.peer.max_connections = max_conn
            self.update_status(f"Número máximo de conexões ajustado para {max_conn}.")
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
            # Exclui o próprio usuário
            if pid == self.peer.peer_id:
                continue
            self.peer_list.addItem(f"{pid} -> {info['ip']}:{info['port']}")

    def fetch_files(self):
        files = self.peer.fetch_resources_from_tracker()
        self.file_list.clear()
        if isinstance(files, list):
            for f in files:
                if self.details_checkbox.isChecked():
                    # Se estiver marcado, busca detalhes de quais peers possuem o arquivo e seus blocos
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
            # Considera que a primeira parte até o "->" é o nome do arquivo
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
                text = item.text()  # Formato: "peer_id -> ip:porta"
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

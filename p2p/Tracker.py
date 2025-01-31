import socket
import threading
import json
import time


class P2PTracker:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        # Cada usuário ativo é armazenado como:
        # user_id -> {
        #     "ip": <ip>,
        #     "port": <porta>,
        #     "last_seen": <timestamp>,
        #     "resources": {
        #         <nome_arquivo>: [lista de índices dos blocos disponíveis],
        #         ...
        #     }
        # }
        self.active_users = {}
        self.lock = threading.Lock()

    def add_user(self, user_id, ip, port, resources=None):
        with self.lock:
            # 'resources':
            # { "README.md": [0,1,2,3], "video.mp4": [0,1,2,3,4,5,6,7] }
            resources = resources if resources is not None else {}
            self.active_users[user_id] = {
                "ip": ip,
                "port": port,
                "last_seen": time.time(),
                "resources": resources,
            }
        print(f"User {user_id} registered from {
              ip}:{port} with resources {resources}")

    def update_last_seen(self, user_id, resources=None):
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()
                # Se o peer enviar novos dados sobre os blocos que possui,
                # atualizamos o dicionário de resources.
                if resources is not None:
                    self.active_users[user_id]["resources"] = resources

    def remove_inactive_users(self):
        while True:
            time.sleep(10)
            with self.lock:
                now = time.time()
                inactive_users = [
                    user_id
                    for user_id, data in self.active_users.items()
                    if now - data["last_seen"] > 30
                ]
                for user_id in inactive_users:
                    print(f"Removing inactive user {user_id}")
                    del self.active_users[user_id]

    def get_active_users(self):
        with self.lock:
            return dict(self.active_users)

    def get_resources(self):
        """
        Retorna uma lista única dos nomes dos arquivos disponíveis (em todos os usuários ativos).
        """
        with self.lock:
            resources = set()
            for data in self.active_users.values():
                resources.update(data["resources"].keys())
            return list(resources)

    def get_file_peers(self, file_name):
        """
        Retorna uma lista de peers que possuem o arquivo 'file_name'.
        Cada item da lista é um dicionário contendo:
          - "peer_id": identificador do peer
          - "ip": endereço IP
          - "port": porta do peer
          - "blocks": a lista de blocos que aquele peer possui para esse arquivo.
        """
        peers = []
        with self.lock:
            for user_id, data in self.active_users.items():
                if file_name in data["resources"]:
                    peers.append({
                        "peer_id": user_id,
                        "ip": data["ip"],
                        "port": data["port"],
                        "blocks": data["resources"][file_name]
                    })
        return peers

    def handle_client(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    return

                request = json.loads(data)
                req_type = request.get("type")
                if req_type == "register":
                    self.add_user(
                        request["user_id"],
                        addr[0],
                        request["port"],
                        request.get("resources")
                    )
                    conn.sendall(b"OK")
                elif req_type == "keep_alive":
                    self.update_last_seen(
                        request["user_id"],
                        request.get("resources")
                    )
                    conn.sendall(b"OK")
                elif req_type == "get_peers":
                    active_users = self.get_active_users()
                    conn.sendall(json.dumps(active_users).encode("utf-8"))
                elif req_type == "get_resources":
                    resources = self.get_resources()
                    conn.sendall(json.dumps(resources).encode("utf-8"))
                elif req_type == "get_file_peers":
                    file_name = request.get("file_name")
                    file_peers = self.get_file_peers(file_name)
                    conn.sendall(json.dumps(file_peers).encode("utf-8"))
                else:
                    conn.sendall(b"Invalid request")
            except Exception as e:
                print(f"Error handling client {addr}: {e}")

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Tracker running on {self.host}:{self.port}")

        threading.Thread(target=self.remove_inactive_users,
                         daemon=True).start()

        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=self.handle_client,
                             args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    tracker = P2PTracker()
    tracker.start()

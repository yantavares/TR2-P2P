import socket
import threading
import time
import json


class P2PTracker:
    def __init__(self, host="0.0.0.0", port=5000):
        self.active_users = {}  # {user_id: {"ip": ip, "resources": list, "last_seen": timestamp}}
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(10)  # Permite até 10 conexões simultâneas
        self.server_socket.settimeout(60)  # Timeout de 60 segundos
        self.total_bytes_received = 0
        print(f"Tracker iniciado em {host}:{port}")

    def add_user(self, user_id, ip, resources):
        with self.lock:
            self.active_users[user_id] = {
                "ip": ip,
                "resources": resources,
                "last_seen": time.time(),
            }
            print(f"Usuário {user_id} conectado com IP {
                  ip} e recursos: {resources}")

    def remove_user(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]
                print(f"Usuário {user_id} removido da lista ativa.")

    def update_last_seen(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()
                print(f"Keep-alive recebido de {user_id}.")

    def check_inactive_users(self):
        while True:
            time.sleep(30)
            with self.lock:
                current_time = time.time()
                inactive_users = [
                    user_id
                    for user_id, data in self.active_users.items()
                    if current_time - data["last_seen"] > 30
                ]
                for user_id in inactive_users:
                    self.remove_user(user_id)

    def handle_client(self, conn, addr):
        try:
            while True:
                data = conn.recv(4096)  # Buffer maior para evitar truncamento
                if not data:
                    break

                self.total_bytes_received += len(data)
                message = json.loads(data.decode('utf-8'))
                user_id = message.get("user_id")
                action = message.get("action")

                if action == "register":
                    resources = message.get("resources", [])
                    self.add_user(user_id, addr[0], resources)
                    conn.sendall(b"Registered successfully")

                elif action == "keep_alive":
                    self.update_last_seen(user_id)
                    conn.sendall(b"Keep-alive acknowledged")

                elif action == "get_active_users":
                    with self.lock:
                        response = {
                            "active_users": self.active_users,
                            "total_bytes_received": self.total_bytes_received,
                        }
                    conn.sendall(json.dumps(response).encode('utf-8'))

        except BrokenPipeError:
            print(f"Conexão com {addr} interrompida (BrokenPipeError).")
        except Exception as e:
            print(f"Erro ao lidar com cliente {addr}: {e}")
        finally:
            conn.close()

    def start_server(self):
        print("Servidor pronto para aceitar conexões.")
        while True:
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(60)  # Timeout por conexão
                print(f"Conexão recebida de {addr}")
                threading.Thread(target=self.handle_client,
                                 args=(conn, addr), daemon=True).start()
            except socket.timeout:
                print("Nenhuma conexão recebida no intervalo do timeout.")


if __name__ == "__main__":
    tracker = P2PTracker()

    # Thread para monitorar usuários inativos
    threading.Thread(target=tracker.check_inactive_users, daemon=True).start()

    # Inicia o servidor
    tracker.start_server()

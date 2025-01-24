import socket
import threading
import json
import time


class P2PTracker:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.active_users = {}
        self.lock = threading.Lock()

    def add_user(self, user_id, ip, port):
        with self.lock:
            self.active_users[user_id] = {
                "ip": ip,
                "port": port,
                "last_seen": time.time(),
            }
        print(f"User {user_id} registered from {ip}:{port}")

    def update_last_seen(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()

    def remove_inactive_users(self):
        while True:
            time.sleep(10)
            with self.lock:
                now = time.time()
                inactive_users = [
                    user_id
                    for user_id, data in self.active_users.items()
                    if now - data["last_seen"] > 30  # Timeout: 30 seconds
                ]
                for user_id in inactive_users:
                    print(f"Removing inactive user {user_id}")
                    del self.active_users[user_id]

    def get_active_users(self):
        with self.lock:
            return self.active_users

    def handle_client(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    return

                request = json.loads(data)
                if request["type"] == "register":
                    self.add_user(request["user_id"], addr[0], request["port"])
                    conn.sendall(b"OK")
                elif request["type"] == "keep_alive":
                    self.update_last_seen(request["user_id"])
                    conn.sendall(b"OK")
                elif request["type"] == "get_peers":
                    active_users = self.get_active_users()
                    conn.sendall(json.dumps(active_users).encode("utf-8"))
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

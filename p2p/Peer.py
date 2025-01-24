import socket
import threading
import json
import sys
import time


class Peer:
    def __init__(self, peer_id, tracker_ip, tracker_port, host, port):
        self.peer_id = peer_id
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.host = host
        self.port = port
        self.connections = {}  # Active peer connections
        self.lock = threading.Lock()

    def register_with_tracker(self):
        """
        Register this peer with the tracker.
        """
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            message = json.dumps(
                {"type": "register", "user_id": self.peer_id, "port": self.port})
            conn.sendall(message.encode("utf-8"))
            conn.close()
            print(f"Registered with tracker as {self.peer_id}")
        except Exception as e:
            print(f"Error registering with tracker: {e}")

    def keep_alive(self):
        """
        Periodically send a keep-alive message to the tracker.
        """
        def _send_keep_alive():
            while True:
                try:
                    conn = socket.create_connection(
                        (self.tracker_ip, self.tracker_port))
                    message = json.dumps(
                        {"type": "keep_alive", "user_id": self.peer_id})
                    conn.sendall(message.encode("utf-8"))
                    conn.close()
                except Exception as e:
                    print(f"Failed to send keep-alive: {e}")
                time.sleep(5)  # Send keep-alive every 5 seconds

        threading.Thread(target=_send_keep_alive, daemon=True).start()

    def fetch_peers_from_tracker(self):
        """
        Fetch the list of active peers from the tracker.
        """
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            message = json.dumps({"type": "get_peers"})
            conn.sendall(message.encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            peers = json.loads(response)
            return peers
        except Exception as e:
            print(f"Error fetching peers from tracker: {e}")
            return {}

    def start_peer_server(self):
        """
        Start a server to listen for incoming peer connections.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Peer server started on {self.host}:{self.port}")

        threading.Thread(target=self._accept_connections,
                         args=(server_socket,), daemon=True).start()

    def _accept_connections(self, server_socket):
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=self._handle_peer_connection,
                             args=(conn, addr), daemon=True).start()

    def _handle_peer_connection(self, conn, addr):
        """
        Handle incoming messages from another peer.
        """
        with conn:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    return
                message = json.loads(data)
                print(f"Message from {message['peer_id']}: {
                      message['content']}")
            except Exception as e:
                print(f"Error handling peer connection: {e}")

    def connect_to_peer(self, peer_ip, peer_port):
        """
        Connect to another peer to send messages.
        """
        try:
            conn = socket.create_connection((peer_ip, peer_port))
            return conn
        except Exception as e:
            print(f"Failed to connect to peer at {peer_ip}:{peer_port}: {e}")
            return None

    def send_message(self, conn, content):
        """
        Send a message to a connected peer.
        """
        try:
            message = json.dumps({"peer_id": self.peer_id, "content": content})
            conn.sendall(message.encode("utf-8"))
            print("Message sent.")
        except Exception as e:
            print(f"Failed to send message: {e}")
        finally:
            conn.close()

    def run(self):
        """
        Main loop for user interaction.
        """
        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()

        while True:
            print("\nFetching active peers...")
            peers = self.fetch_peers_from_tracker()
            peers = {pid: data for pid, data in peers.items() if pid !=
                     self.peer_id}

            if not peers:
                print("No other active peers found.")
                time.sleep(5)
                continue

            print("Active peers:")
            for pid, info in peers.items():
                print(f"{pid} -> {info['ip']}:{info['port']}")

            target_peer_id = input(
                "\nChoose a peer to connect to (Peer ID): ").strip()
            if target_peer_id not in peers:
                print("Invalid peer ID. Please try again.")
                continue

            target_peer = peers[target_peer_id]
            conn = self.connect_to_peer(target_peer["ip"], target_peer["port"])
            if conn:
                message = input("Message: ").strip()
                self.send_message(conn, message)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python Peer.py <peer_id> <tracker_ip> <host> <port>")
        sys.exit(1)

    peer_id, tracker_ip, host, port = sys.argv[1], sys.argv[2], sys.argv[3], int(
        sys.argv[4])
    peer = Peer(peer_id, tracker_ip, 5000, host, port)
    peer.run()

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
        self.connections = {}
        self.resources = []
        self.lock = threading.Lock()

    def add_resource(self, resource):
        with self.lock:
            if resource not in self.resources:
                self.resources.append(resource)
                print(f"Resource {resource} added.")

    def register_with_tracker(self):
        """
        Register this peer with the tracker.
        """
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            message = json.dumps({
                "type": "register",
                "user_id": self.peer_id,
                "port": self.port,
                "resources": self.resources,
            })
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
                    message = json.dumps({
                        "type": "keep_alive",
                        "user_id": self.peer_id,
                        "resources": self.resources,
                    })
                    conn.sendall(message.encode("utf-8"))
                    conn.close()
                except Exception as e:
                    print(f"Failed to send keep-alive: {e}")
                time.sleep(5)

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

    def fetch_resources_from_tracker(self):
        """
        Fetch the list of resources available on the network from the tracker.
        """
        try:
            conn = socket.create_connection(
                (self.tracker_ip, self.tracker_port))
            message = json.dumps({"type": "get_resources"})
            conn.sendall(message.encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            resources = json.loads(response)
            print(f"Resources available on the network: {resources}")
            return resources
        except Exception as e:
            print(f"Error fetching resources from tracker: {e}")
            return []

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
        Handle incoming messages or resource queries from another peer.
        """
        with conn:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    return
                message = json.loads(data)
                if message["type"] == "message":
                    print(f"Message from {message['peer_id']}: {
                          message['content']}")
                elif message["type"] == "get_resources":
                    response = json.dumps({"resources": self.resources})
                    conn.sendall(response.encode("utf-8"))
                    print(f"Sent resource list to {addr}")
            except Exception as e:
                print(f"Error handling peer connection: {e}")

    def connect_to_peer(self, peer_ip, peer_port):
        """
        Connect to another peer to send messages or query resources.
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
            message = json.dumps(
                {"type": "message", "peer_id": self.peer_id, "content": content})
            conn.sendall(message.encode("utf-8"))
            print("Message sent.")
        except Exception as e:
            print(f"Failed to send message: {e}")
        finally:
            conn.close()

    def request_peer_resources(self, peer_ip, peer_port):
        """
        Request the list of resources from another peer.
        """
        try:
            conn = socket.create_connection((peer_ip, peer_port))
            message = json.dumps({"type": "get_resources"})
            conn.sendall(message.encode("utf-8"))
            response = conn.recv(4096).decode("utf-8")
            conn.close()
            resources = json.loads(response)["resources"]
            print(f"Resources available at peer {
                  peer_ip}:{peer_port}: {resources}")
            return resources
        except Exception as e:
            print(f"Error requesting resources from peer: {e}")
            return []

    def run(self):
        """
        Main loop for user interaction.
        """
        self.register_with_tracker()
        self.keep_alive()
        self.start_peer_server()

        while True:
            print("\n1. Add Resource")
            print("2. Fetch Resources from Tracker")
            print("3. Fetch Resources from a Peer")
            print("4. Fetch Active Peers")
            print("5. Send Message to a Peer")

            choice = input("Enter your choice: ").strip()
            if choice == "1":
                resource = input("Enter resource name: ").strip()
                self.add_resource(resource)
            elif choice == "2":
                self.fetch_resources_from_tracker()
            elif choice == "3":
                peer_ip = input("Enter peer IP: ").strip()
                peer_port = int(input("Enter peer port: ").strip())
                self.request_peer_resources(peer_ip, peer_port)
            elif choice == "4":
                peers = self.fetch_peers_from_tracker()
                for pid, info in peers.items():
                    print(f"{pid} -> {info['ip']}:{info['port']}")
            elif choice == "5":
                peer_ip = input("Enter peer IP: ").strip()
                peer_port = int(input("Enter peer port: ").strip())
                conn = self.connect_to_peer(peer_ip, peer_port)
                if conn:
                    message = input("Enter your message: ").strip()
                    self.send_message(conn, message)
            else:
                print("Invalid choice. Try again.")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python Peer.py <peer_id> <tracker_ip> <host> <port>")
        sys.exit(1)

    peer_id, tracker_ip, host, port = sys.argv[1], sys.argv[2], sys.argv[3], int(
        sys.argv[4])
    peer = Peer(peer_id, tracker_ip, 5000, host, port)
    peer.run()

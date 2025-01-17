import socket
import json
import threading


class HTTPServer:
    def __init__(self, host, port, tracker):
        self.host = host
        self.port = port
        self.tracker = tracker

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Server running on {self.host}:{self.port}")

        while True:
            client_socket, address = server_socket.accept()
            print(f"Connection received from {address[0]}:{address[1]}")
            threading.Thread(target=self.handle_client,
                             args=(client_socket, address)).start()

    def handle_client(self, client_socket, address):
        try:
            request_data = client_socket.recv(1024)
            request_size = len(request_data)
            print(f"Received request of size {
                  request_size} bytes from {address[0]}:{address[1]}")

            request_data = request_data.decode()
            if not request_data:
                return

            headers, body = request_data.split("\r\n\r\n", 1)
            lines = headers.split("\r\n")
            method, path, _ = lines[0].split()

            if method == "OPTIONS":
                self.handle_options(client_socket)
            elif method == "POST" and path == "/register":
                self.handle_register(client_socket, address, body)
            elif method == "POST" and path == "/keep_alive":
                self.handle_keep_alive(client_socket, body)
            elif method == "GET" and path == "/active_users":
                self.handle_active_users(client_socket)
            else:
                self.send_response(client_socket, 404, {
                                   "error": "Not Found"})
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def handle_register(self, client_socket, address, body):
        data = json.loads(body)
        user_id = data.get("user_id")
        resources = data.get("resources", [])
        ip = address[0]
        self.tracker.add_user(user_id, ip, resources)
        self.send_response(client_socket, 200, {
                           "message": "Registered successfully"})

    def handle_keep_alive(self, client_socket, body):
        data = json.loads(body)
        user_id = data.get("user_id")
        if user_id is None or user_id not in self.tracker.get_active_users():
            self.send_response(client_socket, 404, {
                               "error": "User not logged"})
            return
        self.tracker.update_last_seen(user_id)
        self.send_response(client_socket, 200, {
                           "message": "Keep-alive acknowledged"})

    def handle_active_users(self, client_socket):
        active_users = self.tracker.get_active_users()
        print(f"List of active users requested. Current users: {
              len(active_users)}")
        self.send_response(client_socket, 200, {"active_users": active_users})

    def handle_options(self, client_socket):
        response = "HTTP/1.1 204 No Content\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        response += "Access-Control-Allow-Headers: Content-Type\r\n"
        response += "Connection: close\r\n\r\n"
        client_socket.sendall(response.encode())

    def send_response(self, client_socket, status_code, body, isError=False):

        status_phrases = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
        }

        reason_phrase = status_phrases.get(status_code, "Unknown")
        response_body = json.dumps(body)

        response = f"HTTP/1.1 {status_code} {reason_phrase}\r\n"
        response += "Content-Type: application/json\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        response += "Access-Control-Allow-Headers: Content-Type\r\n"
        response += "Connection: close\r\n\r\n"
        response += response_body

        client_socket.sendall(response.encode())
        response_size = len(response.encode())
        print(f"Sent response of size {response_size} bytes with status {
              status_code} ({reason_phrase})")

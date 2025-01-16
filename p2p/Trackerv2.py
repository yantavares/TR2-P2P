from flask import Flask, request, jsonify
import threading
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


class P2PTracker:
    def __init__(self):
        self.active_users = {}  # {user_id: {"ip": ip, "resources": list, "last_seen": timestamp}}
        self.lock = threading.Lock()
        self.total_bytes_received = 0
        self.total_bytes_sent = 0

    def add_user(self, user_id, ip, resources):
        with self.lock:
            self.active_users[user_id] = {
                "ip": ip,
                "resources": resources,
                "last_seen": time.time(),
            }

    def remove_user(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]

    def update_last_seen(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()

    def get_active_users(self):
        print(self.active_users)
        with self.lock:
            return {
                "active_users": self.active_users,
                "total_bytes_received": self.total_bytes_received,
                "total_bytes_sent": self.total_bytes_sent,
            }

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


tracker = P2PTracker()


@app.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.json
        user_id = data.get("user_id")
        resources = data.get("resources", [])
        ip = request.remote_addr
        tracker.add_user(user_id, ip, resources)
        tracker.total_bytes_received += len(request.data)
        response = {"message": "Registered successfully"}
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error in /register: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/keep_alive", methods=["POST"])
def keep_alive():
    data = request.json
    user_id = data.get("user_id")
    tracker.update_last_seen(user_id)
    tracker.total_bytes_received += len(request.data)
    response = {"message": "Keep-alive acknowledged"}
    response_data = jsonify(response)
    tracker.total_bytes_sent += len(response_data.data)
    return response_data


@app.route("/active_users", methods=["GET"])
def get_active_users():
    try:
        # Optional: Add size of the incoming request
        tracker.total_bytes_received += len(request.data)
        response = tracker.get_active_users()  # Fetch active users
        response_data = jsonify(response)
        # Track response size
        tracker.total_bytes_sent += len(response_data.data)
        return response_data
    except Exception as e:
        app.logger.error(f"Error in /active_users: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Thread for monitoring inactive users
    threading.Thread(target=tracker.check_inactive_users, daemon=True).start()

    # Start the Flask server
    app.run(host="0.0.0.0", port=5000)

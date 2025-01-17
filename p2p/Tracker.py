import threading
import time
from HTTPServer import HTTPServer


class P2PTracker:
    def __init__(self):
        self.active_users = {}
        self.lock = threading.Lock()

    def add_user(self, user_id, ip, resources):
        with self.lock:
            self.active_users[user_id] = {
                "ip": ip,
                "resources": resources,
                "last_seen": time.time(),
            }
        print(f"User '{user_id}' connected from IP {
              ip}. Total users: {len(self.active_users)}")

    def remove_user(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]
                print(f"User '{user_id}' removed. Total users: {
                      len(self.active_users)}")

    def update_last_seen(self, user_id):
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()
                print(f"Updated last seen for user '{user_id}'.")

    def get_active_users(self):
        with self.lock:
            return self.active_users

    def check_inactive_users(self):
        while True:
            try:
                time.sleep(10)
                print("Checking for inactive users...")
                current_time = time.time()
                inactive_users = []

                with self.lock:
                    inactive_users = [
                        user_id
                        for user_id, data in self.active_users.items()
                        if current_time - data["last_seen"] > 30
                    ]
                for user_id in inactive_users:
                    print(f"Removing inactive user: {user_id}")
                    self.remove_user(user_id)
            except Exception as e:
                print(f"Error during check_inactive_users: {e}")


if __name__ == "__main__":
    tracker = P2PTracker()

    threading.Thread(target=tracker.check_inactive_users, daemon=True).start()

    server = HTTPServer("0.0.0.0", 5000, tracker)
    server.start()

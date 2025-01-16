import socket
import threading
import time
import json


def simulate_user(user_id, resources, action_interval=10):
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("127.0.0.1", 5000))
            client_socket.settimeout(60)  # Timeout do cliente

            register_message = {
                "user_id": user_id,
                "action": "register",
                "resources": resources
            }
            client_socket.sendall(json.dumps(register_message).encode('utf-8'))
            print(client_socket.recv(4096).decode('utf-8'))

            while True:
                time.sleep(action_interval)

                # Envia keep-alive
                keep_alive_message = {
                    "user_id": user_id,
                    "action": "keep_alive"
                }
                client_socket.sendall(json.dumps(
                    keep_alive_message).encode('utf-8'))
                print(client_socket.recv(4096).decode('utf-8'))

                # Solicita lista de usuários ativos
                get_users_message = {
                    "user_id": user_id,
                    "action": "get_active_users"
                }
                client_socket.sendall(json.dumps(
                    get_users_message).encode('utf-8'))
                response = client_socket.recv(4096).decode('utf-8')
                print(f"Usuário {user_id} recebeu lista de ativos: {response}")

        except (ConnectionError, BrokenPipeError):
            print(f"Reconectando usuário {user_id}...")
            time.sleep(5)
        except Exception as e:
            print(f"Erro no usuário {user_id}: {e}")
        finally:
            client_socket.close()


if __name__ == "__main__":
    user1 = threading.Thread(target=simulate_user, args=(
        "user1", ["file1", "file2"], 20))
    user2 = threading.Thread(target=simulate_user, args=(
        "user2", ["file3", "file4"], 25))

    user1.start()
    user2.start()

    user1.join()
    user2.join()

import threading
import time
import random


class P2PTracker:
    def __init__(self):
        self.active_users = {}  # {user_id: {"resources": list, "last_seen": timestamp}}
        self.lock = threading.Lock()

    def add_user(self, user_id, resources):
        """Adiciona um usuário à lista de usuários ativos."""
        with self.lock:
            self.active_users[user_id] = {
                "resources": resources,
                "last_seen": time.time(),
            }
            print(f"Usuário {user_id} adicionado com recursos: {resources}")

    def remove_user(self, user_id):
        """Remove um usuário da lista de ativos."""
        with self.lock:
            if user_id in self.active_users:
                del self.active_users[user_id]
                print(f"Usuário {user_id} removido da lista ativa.")

    def update_last_seen(self, user_id):
        """Atualiza o timestamp de último contato de um usuário."""
        with self.lock:
            if user_id in self.active_users:
                self.active_users[user_id]["last_seen"] = time.time()
                print(f"Keep-alive recebido de {user_id}.")

    def check_inactive_users(self):
        """Remove usuários inativos da lista de ativos."""
        while True:
            time.sleep(30)  # Executa a cada 30 segundos
            with self.lock:
                current_time = time.time()
                inactive_users = [
                    user_id
                    for user_id, data in self.active_users.items()
                    if current_time - data["last_seen"] > 30
                ]
                for user_id in inactive_users:
                    self.remove_user(user_id)

    def get_active_users(self):
        """Retorna a lista de usuários ativos."""
        with self.lock:
            return {
                user_id: data["resources"] for user_id, data in self.active_users.items()
            }

    def simulate_user_activity(self, user_id):
        """Simula atividade de um usuário enviando keep-alive periodicamente."""
        while user_id in self.active_users:
            time.sleep(random.randint(5, 25))  # Simula tempo entre mensagens
            self.update_last_seen(user_id)


# Inicializa o tracker
tracker = P2PTracker()

# Thread para monitorar usuários inativos
threading.Thread(target=tracker.check_inactive_users, daemon=True).start()

# Adiciona alguns usuários
tracker.add_user("user1", ["file1", "file2"])
tracker.add_user("user2", ["file3", "file4"])

# Função para solicitar lista de usuários ativos


def request_active_users(tracker):
    return tracker.get_active_users()


# Simula solicitações de usuários
threading.Thread(target=tracker.simulate_user_activity,
                 args=("user1",), daemon=True).start()
threading.Thread(target=tracker.simulate_user_activity,
                 args=("user2",), daemon=True).start()

# Caso simulado
print("Usuário 1 solicitando lista de usuários ativos:")
user1_resources = request_active_users(tracker)
print("Lista de usuários ativos para user1:", user1_resources)

# Espera 5 segundos
time.sleep(5)

# Usuário 1 se desconecta
tracker.remove_user("user1")

print("Usuário 2 solicitando lista de usuários ativos após 5 segundos:")
user2_resources = request_active_users(tracker)
print("Lista de usuários ativos para user2:", user2_resources)

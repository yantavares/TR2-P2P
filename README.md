# P2P File Sharing System (TR2)

```
  __         ________                  ________         
_/  |________\_____  \          ______ \_____  \______  
\   __\_  __ \/  ____/   ______ \____ \ /  ____/\____ \ 
 |  |  |  | \/       \  /_____/ |  |_> >       \|  |_> >
 |__|  |__|  \_______ \         |   __/\_______ \   __/ 
                     \/         |__|           \/__|    
```

This repository contains a Peer-to-Peer (P2P) file sharing application developed in Python. The system enables users to share and download files in a distributed network. It uses a central tracker to manage active peers and available resources, while file transfers occur directly between peers using TCP connections.

## Features

- **P2P File Sharing:** Share and download files in a distributed environment.
- **Central Tracker:** Manages the registration and status of active peers, as well as the list of available resources.
- **Persistent and Parallel TCP Connections:** Supports downloading file blocks in parallel using a persistent TCP connection per peer group, reducing connection overhead.
- **File Integrity:** Files are divided into fixed-size blocks (1 MB each) and each block is hashed using SHA-256 to ensure data integrity.
- **Robust Error Handling:** Implements timeouts, retries, and exclusion of unresponsive peers.
- **Graphical User Interface:** Built with PyQt5, providing an intuitive interface to connect to the network, share and download files, and communicate with peers.
- **Incentive Mechanism:** A gamification system where users earn experience points (XP) for sharing file blocks. For every block shared, the user gains 1 XP. Once the user accumulates 50 XP, they level up. A higher level increases the number of simultaneous connections allowed (a level 1 user gets up to 4 connections, and each additional level adds one extra connection).

## Getting Started

### Prerequisites

- Python 3.x
- PyQt5 library

You can install PyQt5 using pip:

```bash
pip install PyQt5
```

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yantavares/TR2-P2P.git
   cd p2p-file-sharing
   ```

2. **(Optional) Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

### Usage

1. **Run the Tracker:**

   Start the tracker:

   ```bash
   python Tracker.py
   ```

2. **Run a Peer Instance:**

   Start the peer application:

   ```bash
   python Peer.py
   ```

   The graphical interface will launch. Enter your peer ID and port, then connect to the network. Use the interface to share files, list peers, download files, and send messages.

3. **Earning XP and Leveling Up:**

   - Share files using the interface. Each file is divided into 1 MB blocks.
   - For each block shared, you gain 1 XP.
   - When you accumulate 50 XP, you level up.
   - Your level is displayed next to your peer ID, and the maximum number of simultaneous connections increases by 1 for each level above 1 (starting at 4 for level 1).

## Code Structure

- **peer.py:** Contains the main Peer class that handles network registration, file sharing, downloading (using persistent connections for multiple blocks), and the XP/level incentive mechanism.
- **tracker.py:** Contains the Tracker class that manages active peers, resource availability, and handles client requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


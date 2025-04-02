# Archology-WebXR: Interactive 3D Network Traffic Visualization

A 3D network traffic visualization tool that uses WebXR to visualize network traffic captured by tshark (Wireshark CLI).

## Features

- Real-time network traffic visualization in 3D
- WebXR support for immersive visualization
- Deep packet inspection
- Protocol detection and classification
- Stream analysis
- Test traffic generation mode
- Interactive 3D interface with animated connections
- Multiple traffic sources:
  - Real network capture (requires root/sudo)
  - Test traffic generation for demos
  - Realistic traffic simulation

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/Archology-WebXR.git
cd Archology-WebXR
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Visualization Server

Use the provided script to start the visualization server:

```bash
./run_visualization_server.sh
```

Or run directly with Python:

```bash
python serve_visualization.py
```

For test traffic (no root privileges required):

```bash
python serve_visualization.py --test-only
```

For real network traffic capture (requires root/sudo):

```bash
sudo python serve_visualization.py
```

Additional options:

```
python serve_visualization.py --help
```

### Viewing the Visualization

Open your web browser and navigate to:

```
http://localhost:3001/
```

## Testing

Run the test suite with:

```bash
python tests/run_tests.py
```

## Architecture

- **Backend**: Python Flask with Socket.IO for real-time communication
- **Packet Capture**: tshark (Wireshark CLI) for capturing and parsing network packets
- **Frontend**: React with Three.js for 3D visualization

## Project Structure

```
Archology-WebXR/
├── NetworkVisualization.html     # Main frontend HTML
├── serve_visualization.py        # Main server script
├── server/                       # Backend services
│   ├── backend-socket-handlers.py # Socket.IO event handlers
│   ├── deep-packet-inspection.py  # Packet analysis code
│   └── wiresharkServer.py        # tshark interface
├── src/                          # Frontend source
│   ├── components/               # React components
│   │   ├── NetworkVisualization.tsx
│   │   ├── PacketInspector.tsx
│   │   └── TestTrafficControls.tsx
│   ├── types/                    # TypeScript types
│   │   └── wireshark.ts
├── tests/                        # Unit tests
├── static/                       # Static assets
└── docs/                         # Documentation
```

## Documentation

See the [docs](./docs) directory for detailed documentation.

## License

[MIT License](LICENSE)
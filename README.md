# TShark-3D: Interactive 3D Network Traffic Visualization

TShark-3D is a powerful, interactive tool for visualizing network traffic in 3D with deep packet inspection capabilities. The project combines the packet capturing abilities of tshark (Wireshark's command-line interface) with a beautiful 3D visualization using Three.js and React.

![Network Visualization Demo](https://via.placeholder.com/800x400)

## Features

- **Interactive 3D Network Visualization**: See your network come alive with animated connections and nodes that scale based on traffic volume
- **Deep Packet Inspection**: Analyze packet contents, headers, and protocol-specific information
- **Real-time Processing**: Watch your network traffic update in real-time
- **Multiple Traffic Sources**:
  - Real network capture (requires root/sudo)
  - Test traffic generation for demos
  - Realistic traffic simulation
  - PCAP file analysis
- **Protocol Support**:
  - TCP/UDP visualization
  - HTTP/HTTPS analysis
  - DNS query inspection
  - ICMP traffic
- **Flexible Deployment**: Run as a standalone application or integrate into your existing monitoring tools

## Requirements

- Python 3.7+
- tshark (Wireshark CLI)
- Modern web browser with WebGL support
- Node.js (for development only)

## Installation

### Install Dependencies

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install -y tshark python3-venv python3-pip

# macOS
brew install wireshark python3

# Windows
# Download and install Wireshark from https://www.wireshark.org/download.html
# Ensure Python 3.7+ is installed
```

### Set Up the Project

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/tshark-3d.git
cd tshark-3d

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create static folder if it doesn't exist
mkdir -p static
```

## Usage

### Starting the Server

For test traffic (no root privileges required):

```bash
python serve_visualization.py --test-only
```

For real network traffic capture (requires root/sudo):

```bash
sudo python serve_visualization.py
```

### Command-line Options

```
usage: serve_visualization.py [-h] [--port PORT] [--interface INTERFACE] 
                              [--test-only] [--debug] [--pcap PCAP]

Network Traffic Visualization Server

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           Port to run the server on (default: 3001)
  --interface INTERFACE Network interface to capture from (default: any)
  --test-only           Run in test mode only (no real traffic capture)
  --debug               Enable debug mode
  --pcap PCAP           Read from PCAP file instead of live capture
```

### Using the Visualization

1. Open your web browser and navigate to `http://localhost:3001/`
2. Connect to the server by clicking the "Connect to Server" button
3. Choose a traffic source:
   - Click "Generate Test Traffic" for a demo
   - Use the "Advanced" options for realistic simulation or real capture
4. Interact with the visualization:
   - Rotate, pan, and zoom using mouse controls
   - Hover over nodes and connections to see basic information
   - Click on a connection to open the packet inspector

## Deep Packet Inspection

The packet inspector provides detailed information about the data flowing between hosts:

- **Basic Information**: Source/destination IPs, ports, protocol, packet size
- **TCP Flags**: SYN, ACK, FIN, RST, PSH, URG flags for TCP connections
- **HTTP Analysis**: Methods, URIs, headers, status codes
- **DNS Inspection**: Queries, responses, and DNS record information
- **Payload Data**: Raw packet content when available

## Development

### Project Structure

```
tshark-3d/
├── NetworkVisualization.html     # Main frontend HTML
├── serve_visualization.py        # Main server script
├── deep_packet_inspection.py     # Packet analysis code
├── socket_handlers.py            # Socket.IO event handlers
├── test_traffic_generator.py     # Test traffic generation
├── create_favicon.py             # Generate favicon
├── app.py                        # Simple Flask server
├── src/                          # Frontend source
│   ├── components/               # React components
│   │   ├── NetworkVisualization.tsx
│   │   ├── PacketInspector.tsx
│   │   └── TestTrafficControls.tsx
│   ├── types/                    # TypeScript types
│   │   └── wireshark.ts
│   └── main.tsx                  # Entry point
├── static/                       # Static assets
├── .gitignore                    # Git ignore file
└── requirements.txt              # Python dependencies
```

### Extending the Visualization

To add support for new protocols:

1. Update the protocol detection in `_get_protocol()` method in `deep_packet_inspection.py`
2. Add a color for the protocol in `protocolColors` in `NetworkVisualization.tsx`
3. Create an extraction method in `deep_packet_inspection.py`
4. Update the packet inspector UI to display the new information

## Troubleshooting

### Common Issues

- **"Permission denied" errors**: Real traffic capture requires root/sudo privileges
- **No connections showing**: Try the test traffic generator to verify functionality
- **Performance issues**: For high-volume networks, consider using a more powerful machine or filtering traffic

### Debugging

Enable debug mode for more verbose logging:

```bash
sudo python serve_visualization.py --debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Wireshark/tshark](https://www.wireshark.org/) for packet capture functionality
- [Three.js](https://threejs.org/) for 3D visualization
- [React Three Fiber](https://github.com/pmndrs/react-three-fiber) for React integration with Three.js
- [Socket.IO](https://socket.io/) for real-time communication

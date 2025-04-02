Usage
Starting the server
The server requires root privileges to capture network traffic. For testing, you can use the --test-only flag to run without root.
For test traffic (no root required):
bashCopypython serve_visualization.py --test-only
For real traffic capture (requires root/sudo):
bashCopysudo python serve_visualization.py
Command-line options
Copypython serve_visualization.py --help

usage: serve_visualization.py [-h] [--port PORT] [--interface INTERFACE] [--test-only] [--debug] [--pcap PCAP]

Network Traffic Visualization Server

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           Port to run the server on (default: 3001)
  --interface INTERFACE Network interface to capture from (default: any)
  --test-only           Run in test mode only (no real traffic capture)
  --debug               Enable debug mode
  --pcap PCAP           Read from PCAP file instead of live capture
Accessing the application
Open your web browser and navigate to:
Copyhttp://localhost:3001/
Using the Visualization

Connect to Server: The application will automatically try to connect to the server.
Generate Test Traffic: For demo purposes, click "Generate Test Traffic".
Interact with the 3D Visualization:

Rotate, pan, and zoom using mouse controls
Hover over nodes and connections to see basic information
Click on a connection to open the packet inspector



Advanced Features
Packet Inspector
The packet inspector allows you to examine detailed information about the packets in a selected connection:

Basic packet properties (source, destination, protocol, size)
Protocol-specific details (TCP flags, HTTP headers, DNS queries)
Payload data (when available)
Filter packets to find specific information

Traffic Types

Test Traffic: Simple random traffic generation for testing
Realistic Traffic: Simulated traffic with realistic network patterns
Real Traffic: Actual network traffic captured from your selected interface

Development
Project Structure
Copytshark-3d/
├── NetworkVisualization.html       # Frontend visualization
├── serve_visualization.py          # Main server script
├── create_favicon.py               # Script to create favicon
├── server/                         # Server-side components 
│   ├── deep-packet-inspection.py   # DPI functionality
│   ├── backend-socket-handlers.py  # Socket.IO event handlers
│   ├── wiresharkServer.py          # Python packet capture server
│   └── wiresharkServer.ts          # TypeScript packet capture server
├── src/                            # React/TypeScript components
│   ├── components/                 # UI components 
│   │   ├── NetworkVisualization.tsx # Main visualization component
│   │   ├── PacketInspector.tsx     # Packet inspection component
│   │   └── TestTrafficControls.tsx # Traffic control UI
│   ├── types/                      # TypeScript type definitions
│   └── main.tsx                    # Entry point
├── static/                         # Static assets
└── venv/                           # Python virtual environment

## Packet Inspection Features

The system now includes powerful deep packet inspection capabilities:

### Components

1. **server/deep-packet-inspection.py**
   - Detailed packet analysis and extraction
   - Protocol-specific data parsing (HTTP, DNS, TCP flags)
   - Payload extraction and formatting
   - Storage and retrieval of packet details by connection

2. **server/backend-socket-handlers.py**
   - Socket.IO event handlers for packet detail requests
   - Real-time data streaming to frontend components
   - Connection management between visualization and packet inspector

3. **src/components/PacketInspector.tsx**
   - Interactive UI for examining packet details
   - Protocol-specific visualization panels
   - Packet filtering and searching capabilities
   - Real-time updates as new packets arrive

### Supported Protocols

The packet inspector provides specialized views for:
- **TCP/UDP**: Port information, flags (SYN, ACK, FIN, etc.)
- **HTTP/HTTPS**: Methods, headers, status codes, content types
- **DNS**: Query details, response codes, answer records
- **ICMP**: Message types, codes
- **General IPv4/IPv6**: TTL values, fragmentation details

### Using the Packet Inspector

1. In the 3D visualization view, click on any connection (edge) between hosts
2. The packet inspector panel will open with all packets for that connection
3. Filter packets using the search bar at the top of the inspector
4. Click on individual packets to view detailed information
5. Examine protocol-specific data in the dedicated panels

### Extending the Application
Adding a New Protocol

Update the _get_protocol method in NetworkTrafficAggregator class
Add a color for the protocol in the protocolColors object in NetworkVisualization.tsx
Add extraction logic in the appropriate method (e.g., _extract_http_info as an example)
Create a new panel in PacketInspector.tsx to display the protocol-specific information

Adding New Visualization Features
The visualization is built using Three.js via React Three Fiber. To add new visualization elements:

Create new components in the src/components/ directory
Import and use them in the NetworkGraph component

## Traffic Simulation

The system provides three ways to visualize network traffic:

1. **Test Traffic**: Simple random packet generation for testing the visualization
2. **Realistic Traffic**: Simulated network with common protocols and realistic patterns
3. **Real Traffic**: Actual network capture using tshark (requires sudo/root)

### Realistic Traffic Simulation

The realistic traffic simulation creates:
- A network topology with common devices (PCs, phones, IoT devices)
- Typical network services (DNS, HTTP/HTTPS, local file sharing)
- Realistic communication patterns between devices
- Protocol-appropriate port numbers and packet sizes

This provides a more meaningful visualization experience when real traffic capture isn't available or desired.

## Troubleshooting
Common Issues

"Permission denied": For real traffic capture, you need to run the server with sudo privileges.
Connection refused: Make sure the server is running on the expected port.
No traffic showing: Try using test traffic generation to verify the visualization is working.
tshark not found: Ensure Wireshark/tshark is properly installed and in your PATH.

Debugging
Use the --debug flag to enable more verbose logging:
bashCopysudo python serve_visualization.py --debug
Check the browser console for frontend errors.
License
This project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgments

Wireshark/tshark for packet capture functionality
Three.js and React Three Fiber for 3D visualization
Socket.IO for real-time communication

Implementation Guide: Adding Deep Packet Inspection to Network Visualization
This guide explains the enhanced features and implementation details for adding deep packet inspection (DPI) to your 3D network visualization project. It covers key files, changes, and how to implement and extend the functionality.
Overview of Changes
To enhance the existing visualization with deep packet inspection capabilities, I've added several key components:

Packet Storage and Aggregation: Store detailed packet information in memory for each connection
Advanced tshark Configuration: Capture more detailed packet data including application layer protocols
Packet Inspector UI: A React component for viewing and analyzing packet details
Socket API Extensions: New events for requesting and receiving packet details

Key Components
1. Enhanced NetworkTrafficAggregator
The core of the DPI functionality is in the enhanced NetworkTrafficAggregator class. Key additions include:
pythonCopyclass NetworkTrafficAggregator:
    def __init__(self):
        # Existing code...
        self.packets: Dict[str, List[DetailedPacket]] = {}  # Store packets by stream key
        self.max_packets_per_stream = 100  # Limit packet storage

    def add_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        # Existing aggregation code...
        
        # Create detailed packet and store it
        detailed_packet = self._create_detailed_packet(
            packet, src_ip, dst_ip, bytes_transferred, protocol, timestamp
        )
        
        # Store packet by stream key with limit
        if stream_key not in self.packets:
            self.packets[stream_key] = []
        
        self.packets[stream_key].append(detailed_packet)
        
        # Enforce packet storage limit
        if len(self.packets[stream_key]) > self.max_packets_per_stream:
            self.packets[stream_key].pop(0)  # Remove oldest packet
2. DetailedPacket Class
A new data class to store comprehensive packet information:
pythonCopy@dataclass
class DetailedPacket:
    id: str
    timestamp: float
    sourceIP: str
    destinationIP: str
    protocol: str
    length: int
    ttl: Optional[int] = None
    sourcePort: Optional[int] = None
    destinationPort: Optional[int] = None
    tcpFlags: Optional[Dict[str, bool]] = None
    payload: Optional[str] = None
    httpInfo: Optional[Dict[str, Any]] = None
    dnsInfo: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None  # Store raw packet data for reference
3. Protocol-Specific Information Extraction
Methods to extract detailed protocol information:
pythonCopydef _extract_tcp_flags(self, packet: Dict[str, Any]) -> Optional[Dict[str, bool]]:
    # Extract TCP flags (SYN, ACK, FIN, etc.)

def _extract_http_info(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Extract HTTP headers, methods, etc.

def _extract_dns_info(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Extract DNS queries, answers, etc.

def _extract_payload(self, packet: Dict[str, Any]) -> Optional[str]:
    # Extract and format packet payload data
4. Socket.IO Event Handler
A new handler for requesting packet details:
pythonCopy@socketio.on('requestPacketDetails')
def handle_packet_details_request(data):
    """Handler for packet detail requests"""
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    protocol = data.get('protocol')
    
    if not all([source_id, target_id, protocol]):
        return
    
    # Use the global aggregator instance
    global aggregator
    packets = aggregator.get_packet_details(source_id, target_id, protocol)
    socketio.emit('packetDetails', {"packets": packets})
5. Frontend PacketInspector Component
React component for inspecting packets:
typescriptCopyconst PacketInspector: React.FC<PacketInspectorProps> = ({ 
  socket, 
  selectedConnection, 
  onClose 
}) => {
  const [packets, setPackets] = useState<DetailedPacket[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<DetailedPacket | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  
  useEffect(() => {
    if (!socket || !selectedConnection) return;
    
    setLoading(true);
    setPackets([]);
    
    // Parse the connection details
    const [sourceId, targetId, protocol] = selectedConnection.split('-');
    
    // Request detailed packets for this connection
    socket.emit('requestPacketDetails', {
      sourceId,
      targetId,
      protocol
    });
    
    // Listen for packet details
    const handlePacketDetails = (data: { packets: DetailedPacket[] }) => {
      setPackets(prevPackets => [...prevPackets, ...data.packets]);
      setLoading(false);
    };
    
    socket.on('packetDetails', handlePacketDetails);
    
    return () => {
      socket.off('packetDetails', handlePacketDetails);
    };
  }, [socket, selectedConnection]);
  
  // Render packet list and details
  // ...
}
Implementation Steps
To implement these changes in your project, follow these steps:
1. Create the Deep Packet Inspection Backend

Create a file named deep_packet_inspection.py with the NetworkTrafficAggregator and DetailedPacket classes.
Update your server code to use the enhanced aggregator.

2. Modify tshark Capture Parameters
Update your tshark command to capture more detailed data:
pythonCopytshark_cmd = [
    "tshark", "-i", network_interface, "-T", "json", 
    "-l", "-V", "-n", "-q",
    # Capture HTTP, DNS, and other application layer data
    "-d", "tcp.port==80,http", 
    "-d", "tcp.port==443,tls",
    "-d", "udp.port==53,dns"
]
3. Add Socket.IO Event Handlers
Implement the requestPacketDetails event handler in your server code.
4. Create Frontend Components

Create PacketInspector.tsx for the packet inspection UI.
Update NetworkVisualization.tsx to support selecting connections and showing the inspector.

5. Integrate DPI into the Main Application

Update your main server script to incorporate the new functionality.
Connect the frontend and backend components.

Extending the DPI Functionality
Adding Support for New Protocols
To add support for a new protocol:

Add protocol detection in _get_protocol method:

pythonCopydef _get_protocol(self, packet: Dict[str, Any]) -> str:
    layers = packet["_source"]["layers"]
    # Add your protocol detection logic here
    if "your_protocol" in layers:
        return "YOUR_PROTOCOL"
    # Existing code...

Create an extraction method for the protocol:

pythonCopydef _extract_your_protocol_info(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    layers = packet["_source"]["layers"]
    if "your_protocol" not in layers:
        return None
        
    your_protocol_layer = layers["your_protocol"]
    protocol_info = {}
    
    # Extract relevant fields
    # ...
        
    return protocol_info

Update _create_detailed_packet to include your new protocol information.
Add UI support in the PacketInspector component.

Performance Considerations
For large-scale packet capture, consider:

Selective Storage: Only store packets that match certain criteria
Aggregation: For high-volume connections, store aggregated statistics instead of individual packets
Disk Buffering: For long-running captures, implement disk-based storage with indexed lookup

Advanced Analysis Features
Some ideas for advanced analysis:

Traffic Patterns: Visualize packet timing and volumes over time
Connection Correlation: Identify related connections
Anomaly Detection: Highlight unusual traffic patterns
Protocol Decoding: Deep decode specific protocols of interest

Deployment Considerations
When deploying with DPI functionality:

Memory Usage: Monitor memory usage as packet storage can grow substantially
Privacy and Security: Be aware of privacy implications when inspecting packet payloads
Network Load: For high-throughput networks, consider sampling or filtering

Resources for Further Development

tshark Documentation
Wireshark Display Filters
React Three Fiber Documentation
Socket.IO Documentation

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

bgilbert1984: use your Python backend with the NetworkVisualization and TestTrafficControls components in a few ways:

## Option 1: Use the Combined Server Approach

Instead of running the wiresharkServer.py directly as you were doing before, use our new `serve_visualization.py` script which handles both the Socket.IO backend and serves the static files:

```bash
python /home/ashben/www/html/Archology-WebXR/serve_visualization.py
```

This script will:
1. Start the backend Socket.IO server on port 3002
2. Start a frontend web server on port 3001
3. Make both the simple test connection page and the full 3D visualization available

You'll be able to access:
- Basic connection test page at: http://localhost:3001/
- Full 3D network visualization at: http://localhost:3001/network

## Option 2: Use the Original React Application with our Python Backend

If you want to use the original React components in the Archology-WebXR project:

1. Start the Python backend:
```bash
python /home/ashben/www/html/Archology-WebXR/server/wiresharkServer.py
```

2. In a separate terminal, navigate to the React project directory and start the frontend:
```bash
cd /home/ashben/www/html/Archology-WebXR
npm run dev  # or whatever command you use to start the React development server
```

3. Open the React application in your browser (typically http://localhost:5173 or similar)

## Testing the Connection

If you're having connection issues, you can use our test-connection.html file to verify that the Socket.IO server is working correctly. Simply open it in a browser:

```
http://localhost:3001/
```

This will show a simple UI where you can:
1. Click "Connect to Server" to establish a Socket.IO connection
2. Generate test traffic or capture real network traffic
3. View the basic stats of received network data

## Remember:

- For capturing real network traffic (not test data), you'll need to run the backend with sudo privileges
- The backend listens on port 3002, and WebSocket connections are accepted from localhost:5173, localhost:5174, and localhost:5175
- The test traffic generator creates simulated network packets that match what the React visualization components expect


GitHub Copilot: I'll help you implement the serve_visualization.py script to provide the combined server approach that will handle both the Socket.IO backend and serve the static files. This will make it easier to run everything from one command.

Let's first examine the current state of the project to understand what we're working with.Looking at the existing app.py, I see it's a simple Flask application that serves the NetworkVisualization.html file and a favicon. Now let's check the existing network visualization HTML and the wiresharkServer.py to understand the components we need to integrate:I'll continue by examining the wiresharkServer.py and test-connection.html files to understand how they work before implementing the serve_visualization.py script.Based on the files I examined, I can now create the serve_visualization.py script that will combine both the Socket.IO backend server and static file serving. I examined the existing app.py (a Flask server that simply serves HTML files), wiresharkServer.py (a Flask-SocketIO server that captures and processes network traffic), and the NetworkVisualization.html file (which contains the 3D visualization).

Let's also check the test-connection.html file to understand how to make that available:Based on my review of the files, I now have a clear understanding of what we need to implement. I'll create the serve_visualization.py script that combines both the Socket.IO backend server (from wiresharkServer.py) and the static file serving (from app.py). This will allow you to run everything from a single command.

Let me create the serve_visualization.py file:
````
#!/usr/bin/env python3
import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import random
import os
import threading

from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configure SocketIO
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3001", 
                                              "http://localhost:5173", 
                                              "http://localhost:5174", 
                                              "http://localhost:5175"],
                   ping_timeout=60, ping_interval=25)

# Data models
@dataclass
class NetworkHost:
    id: str
    ip: str
    packets: int = 0
    bytesTransferred: int = 0

@dataclass
class NetworkStream:
    source: str
    target: str
    protocol: str
    packets: int = 0
    bytes: int = 0
    timestamp: float = 0.0

@dataclass
class WiresharkData:
    hosts: List[NetworkHost] = field(default_factory=list)
    streams: List[NetworkStream] = field(default_factory=list)

class NetworkTrafficAggregator:
    def __init__(self):
        self.hosts: Dict[str, NetworkHost] = {}
        self.streams: Dict[str, NetworkStream] = {}
        self.host_id_counter = 0

    def add_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        ip_layer = packet["_source"]["layers"]["ip"]
        src_ip = ip_layer["ip.src"]
        dst_ip = ip_layer["ip.dst"]
        protocol = self._get_protocol(packet)
        bytes_transferred = int(ip_layer["ip.len"])
        timestamp = float(packet["_source"]["layers"]["frame"]["frame.time_epoch"]) * 1000

        # Update hosts
        src_host = self._get_or_create_host(src_ip)
        dst_host = self._get_or_create_host(dst_ip)

        src_host.packets += 1
        dst_host.packets += 1
        src_host.bytesTransferred += bytes_transferred
        dst_host.bytesTransferred += bytes_transferred

        # Update stream
        stream_key = f"{src_host.id}-{dst_host.id}-{protocol}"
        if stream_key not in self.streams:
            self.streams[stream_key] = NetworkStream(
                source=src_host.id,
                target=dst_host.id,
                protocol=protocol,
                packets=0,
                bytes=0,
                timestamp=timestamp
            )
            
        stream = self.streams[stream_key]
        stream.packets += 1
        stream.bytes += bytes_transferred
        stream.timestamp = timestamp

        return self._get_visualization_data()

    def _get_or_create_host(self, ip: str) -> NetworkHost:
        for host in self.hosts.values():
            if host.ip == ip:
                return host
                
        self.host_id_counter += 1
        host = NetworkHost(
            id=str(self.host_id_counter),
            ip=ip
        )
        self.hosts[host.id] = host
        return host

    def _get_protocol(self, packet: Dict[str, Any]) -> str:
        layers = packet["_source"]["layers"]
        if "tcp" in layers:
            return "TCP"
        elif "udp" in layers:
            return "UDP"
        return "OTHER"

    def _get_visualization_data(self) -> Dict[str, Any]:
        return {
            "hosts": [asdict(host) for host in self.hosts.values()],
            "streams": [asdict(stream) for stream in self.streams.values()]
        }


def start_capture(network_interface='any'):
    aggregator = NetworkTrafficAggregator()
    
    try:
        # Check if running as root (required for packet capture)
        if os.geteuid() != 0:
            print("Warning: Not running as root. Packet capture may fail due to permission issues.")
            socketio.emit('error', {
                "message": "Not running with sudo privileges. Real traffic capture requires sudo."
            })
            
        # Use tshark to capture network traffic with specific parameters
        # -p: Don't put the interface in promiscuous mode (if firewall is blocking)
        # -n: Disable all name resolution (faster and avoids DNS issues)
        # Try with a more basic configuration first
        tshark_cmd = ["tshark", "-i", network_interface, "-T", "json", 
                     "-l", "-f", "ip", "-n", "-q"]
        print(f"Running command: {' '.join(tshark_cmd)}")
        
        tshark_process = subprocess.Popen(
            tshark_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Check for immediate startup errors
        time.sleep(0.5)
        if tshark_process.poll() is not None:
            error_output = tshark_process.stderr.read()
            print(f"tshark failed to start: {error_output}")
            socketio.emit('error', {
                "message": f"Failed to start packet capture: {error_output}"
            })
            return
            
        print(f"tshark started successfully on interface {network_interface}")
        
        # Notify client that capture has started successfully
        socketio.emit('captureStatus', {
            "status": "started", 
            "message": f"Packet capture started on {network_interface}"
        })
        
        buffer = ""
        packet_count = 0
        last_update_time = time.time()
        update_batch = []
        
        while True:
            # Process stderr to catch warnings but don't stop on them
            error = tshark_process.stderr.readline()
            if error:
                print(f"tshark stderr: {error.strip()}", file=sys.stderr)
                if "Permission denied" in error:
                    socketio.emit('error', {
                        "message": "Permission denied. Please run the server with sudo privileges."
                    })
                    break
            
            # Process stdout for packet data
            output = tshark_process.stdout.readline()
            if output == "" and tshark_process.poll() is not None:
                print("tshark process ended")
                break
                
            if output:
                # Check if the line is a complete JSON object 
                try:
                    # Clean the output and try to parse it
                    cleaned_output = output.strip()
                    if cleaned_output.startswith('[') and cleaned_output.endswith(']'):
                        # If it's an array, take the first item
                        packet_list = json.loads(cleaned_output)
                        if packet_list and len(packet_list) > 0:
                            packet = packet_list[0]
                            visualization_data = aggregator.add_packet(packet)
                            update_batch.append(visualization_data)
                            packet_count += 1
                    elif cleaned_output.startswith('{') and cleaned_output.endswith('}'):
                        # It's a single packet
                        packet = json.loads(cleaned_output)
                        visualization_data = aggregator.add_packet(packet)
                        update_batch.append(visualization_data)
                        packet_count += 1
                    else:
                        # Incomplete JSON, add to buffer
                        buffer += output
                except json.JSONDecodeError:
                    # Not valid JSON, add to buffer and try to process
                    buffer += output
                    
                    # Try to extract complete JSON objects from buffer
                    if buffer.strip().startswith('{') and '}' in buffer:
                        try:
                            # Find the position of the closing brace
                            end_pos = buffer.find('}') + 1
                            json_part = buffer[:end_pos]
                            buffer = buffer[end_pos:]
                            
                            packet = json.loads(json_part)
                            visualization_data = aggregator.add_packet(packet)
                            update_batch.append(visualization_data)
                            packet_count += 1
                        except json.JSONDecodeError:
                            # Still not valid JSON
                            if len(buffer) > 50000:  # Reset if buffer gets too large
                                print("Buffer overflow, resetting")
                                buffer = ""
            
            # Send batch updates every 0.5 seconds to reduce network traffic
            current_time = time.time()
            if update_batch and (current_time - last_update_time > 0.5 or len(update_batch) >= 10):
                # Send the most recent update
                recent_update = update_batch[-1]
                socketio.emit('networkUpdate', recent_update)
                
                # Log statistics
                print(f"Processed {packet_count} packets, {len(recent_update['hosts'])} hosts, {len(recent_update['streams'])} streams")
                
                # Reset batch tracking
                update_batch = []
                last_update_time = current_time
                    
    except Exception as e:
        print(f"Failed to start tshark: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        socketio.emit('error', {
            "message": f"Failed to start packet capture. {str(e)}"
        })
    finally:
        # Send final update if there are any pending
        if update_batch:
            socketio.emit('networkUpdate', update_batch[-1])
            
        if tshark_process and tshark_process.poll() is None:
            print("Terminating tshark process...")
            tshark_process.terminate()
            try:
                tshark_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("tshark process did not terminate, forcing...")
                tshark_process.kill()
            

class TestTrafficGenerator:
    def __init__(self):
        self.running = False
        self.aggregator = NetworkTrafficAggregator()
        self.ips = [
            '192.168.1.1', '192.168.1.2', '192.168.1.100', 
            '10.0.0.1', '10.0.0.2', '10.0.0.3',
            '172.16.0.1', '8.8.8.8', '1.1.1.1'
        ]
        self.protocols = ['TCP', 'UDP', 'HTTP', 'HTTPS', 'DNS']
        self.connection_attempts = 0
        self.max_retries = 5

    def generate_random_packet(self):
        src_ip_index = random.randint(0, len(self.ips) - 1)
        dst_ip_index = random.randint(0, len(self.ips) - 1)
        
        # Ensure source and destination are different
        while dst_ip_index == src_ip_index:
            dst_ip_index = random.randint(0, len(self.ips) - 1)
            
        protocol_index = random.randint(0, len(self.protocols) - 1)
        protocol = self.protocols[protocol_index]
        bytes_count = random.randint(50, 1550)  # Random packet size between 50 and 1550 bytes
        
        tcp_data = None
        udp_data = None
        
        if protocol in ['TCP', 'HTTP', 'HTTPS']:
            src_port = str(random.randint(1024, 61023))
            dst_port = str(random.randint(1024, 61023))
            
            # Set appropriate destination ports for HTTP/HTTPS
            if protocol == 'HTTP':
                dst_port = '80'
            elif protocol == 'HTTPS':
                dst_port = '443'
                
            tcp_data = {
                "tcp.srcport": src_port,
                "tcp.dstport": dst_port
            }
        elif protocol in ['UDP', 'DNS']:
            src_port = str(random.randint(1024, 61023))
            dst_port = str(random.randint(1024, 61023))
            
            # Set appropriate destination port for DNS
            if protocol == 'DNS':
                dst_port = '53'
                
            udp_data = {
                "udp.srcport": src_port,
                "udp.dstport": dst_port
            }
            
        return {
            "_source": {
                "layers": {
                    "frame": {
                        "frame.time_epoch": str(time.time())
                    },
                    "ip": {
                        "ip.src": self.ips[src_ip_index],
                        "ip.dst": self.ips[dst_ip_index],
                        "ip.proto": "6" if protocol in ['TCP', 'HTTP', 'HTTPS'] else
                                   "17" if protocol in ['UDP', 'DNS'] else "1",
                        "ip.len": str(bytes_count)
                    },
                    "tcp": tcp_data,
                    "udp": udp_data
                }
            }
        }

    def start(self):
        self.running = True
        self.connection_attempts = 0
        
        print("Starting test traffic generator with enhanced reliability")

# Initialize test traffic generator
test_traffic_generator = TestTrafficGenerator()

# Flask routes for web server
@app.route('/')
def home():
    return send_from_directory('.', 'test-connection.html')

@app.route('/network')
def network():
    return send_from_directory('.', 'NetworkVisualization.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('startCapture')
def handle_start_capture(network_interface):
    print(f'Starting capture on interface: {network_interface}')
    
    if network_interface == 'test':
        print('Starting test traffic generator')
        # Start test traffic generator in a background task
        socketio.start_background_task(start_test_traffic)
    elif network_interface == 'realistic':
        print('Starting realistic traffic simulation')
        # Start realistic traffic simulation in a background task
        socketio.start_background_task(start_realistic_simulation)
    else:
        # Start real traffic capture in a background task
        socketio.start_background_task(start_capture, network_interface)

@socketio.on('stopTestTraffic')
def handle_stop_test_traffic():
    print('Stopping test traffic generator')
    global test_traffic_generator
    test_traffic_generator.running = False

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    
# Background task to generate test traffic
def start_test_traffic():
    global test_traffic_generator
    test_traffic_generator.running = True
    test_traffic_generator.connection_attempts = 0
    
    while test_traffic_generator.running:
        try:
            packet = test_traffic_generator.generate_random_packet()
            visualization_data = test_traffic_generator.aggregator.add_packet(packet)
            socketio.emit('networkUpdate', visualization_data)
            socketio.sleep(0.5)  # Generate traffic every 500ms
        except Exception as e:
            print(f"Error generating test traffic: {e}")
            # Don't stop completely on error, just log it
            socketio.sleep(1)

# Start a separate Flask app for the frontend
def start_frontend_server():
    print("Frontend server starting on port 3001")
    socketio.run(app, host='0.0.0.0', port=3001, debug=False)

# Signal handlers
def cleanup(signum, frame):
    print('Cleaning up...')
    print('Server shut down successfully')
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == '__main__':
    print("Starting Combined Visualization Server")
    print("Frontend: http://localhost:3001/")
    print("Frontend (3D): http://localhost:3001/network")
    print("Backend Socket.IO: port 3001")
    print("\nNote: For capturing real network traffic, you may need to run with sudo privileges")
    
    socketio.run(app, host='0.0.0.0', port=3001, debug=False)
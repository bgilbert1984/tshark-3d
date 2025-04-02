#!/usr/bin/env python3
import json
import signal
import subprocess
import sys
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import random

try:
    from flask import Flask, jsonify, request, send_from_directory, render_template
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit, disconnect
except ImportError:
    print("Error: Required packages not found.")
    print("Please run: source venv/bin/activate && pip install flask flask-socketio flask-cors")
    sys.exit(1)

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
class DetailedPacket:
    id: str
    timestamp: float
    sourceIP: str
    destinationIP: str
    protocol: str
    length: int
    ttl: Optional[int] = None
    sourcePort: Optional[str] = None
    destinationPort: Optional[str] = None
    tcpFlags: Optional[Dict[str, bool]] = None
    httpInfo: Optional[Dict[str, Any]] = None
    dnsInfo: Optional[Dict[str, Any]] = None
    payload: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

@dataclass
class WiresharkData:
    hosts: List[NetworkHost] = field(default_factory=list)
    streams: List[NetworkStream] = field(default_factory=list)

class NetworkTrafficAggregator:
    def __init__(self):
        self.hosts: Dict[str, NetworkHost] = {}
        self.streams: Dict[str, NetworkStream] = {}
        self.host_id_counter = 0
        self.packets: Dict[str, List[DetailedPacket]] = {}  # Store packets by stream key
        self.max_packets_per_stream = 100  # Limit packet storage
        self.packet_id_counter = 0

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
        
        # Create and store detailed packet information
        detailed_packet = self._extract_packet_details(packet, src_ip, dst_ip, bytes_transferred, protocol, timestamp)
        
        # Store packet by stream key with limit
        if stream_key not in self.packets:
            self.packets[stream_key] = []
            
        self.packets[stream_key].append(detailed_packet)
        
        # Enforce packet storage limit
        if len(self.packets[stream_key]) > self.max_packets_per_stream:
            self.packets[stream_key].pop(0)  # Remove oldest packet

        return self._get_visualization_data()
    
    def _extract_packet_details(self, packet: Dict[str, Any], 
                               src_ip: str = None, dst_ip: str = None, 
                               bytes_transferred: int = None, 
                               protocol: str = None, 
                               timestamp: float = None) -> DetailedPacket:
        """Extract detailed information about the packet for deeper inspection"""
        self.packet_id_counter += 1
        layers = packet["_source"]["layers"]
        
        # Use provided values or extract from packet
        src_ip = src_ip or layers["ip"]["ip.src"]
        dst_ip = dst_ip or layers["ip"]["ip.dst"]
        bytes_transferred = bytes_transferred or int(layers["ip"]["ip.len"])
        protocol = protocol or self._get_protocol(packet)
        timestamp = timestamp or float(layers["frame"]["frame.time_epoch"]) * 1000
        
        # Extract TTL if available
        ttl = int(layers["ip"].get("ip.ttl", 0)) if "ip.ttl" in layers["ip"] else None
        
        # Extract port information
        src_port = None
        dst_port = None
        if "tcp" in layers:
            src_port = layers["tcp"].get("tcp.srcport")
            dst_port = layers["tcp"].get("tcp.dstport")
        elif "udp" in layers:
            src_port = layers["udp"].get("udp.srcport")
            dst_port = layers["udp"].get("udp.dstport")
            
        # Extract TCP flags
        tcp_flags = None
        if "tcp" in layers:
            tcp_layer = layers["tcp"]
            tcp_flags = {
                "syn": tcp_layer.get("tcp.flags.syn") == "1",
                "ack": tcp_layer.get("tcp.flags.ack") == "1", 
                "fin": tcp_layer.get("tcp.flags.fin") == "1",
                "rst": tcp_layer.get("tcp.flags.reset") == "1",
                "psh": tcp_layer.get("tcp.flags.push") == "1",
                "urg": tcp_layer.get("tcp.flags.urg") == "1"
            }
            
        # Extract HTTP information
        http_info = None
        if "http" in layers:
            http_layer = layers["http"]
            http_info = {}
            
            # HTTP Request
            if "http.request.method" in http_layer:
                http_info["method"] = http_layer["http.request.method"]
                http_info["uri"] = http_layer.get("http.request.uri", "")
                http_info["host"] = http_layer.get("http.host", "")
                http_info["userAgent"] = http_layer.get("http.user_agent", "")
                
            # HTTP Response
            elif "http.response" in http_layer or "http.response_code" in http_layer:
                http_info["statusCode"] = http_layer.get("http.response.code", "")
                http_info["statusPhrase"] = http_layer.get("http.response.phrase", "")
                http_info["contentType"] = http_layer.get("http.content_type", "")
                http_info["contentLength"] = http_layer.get("http.content_length", "")
                
            # Common HTTP headers
            for key, value in http_layer.items():
                if key.startswith("http.") and key not in ["http.request", "http.response"]:
                    cleaned_key = key.replace("http.", "")
                    http_info[cleaned_key] = value
                    
        # Extract DNS information
        dns_info = None
        if "dns" in layers:
            dns_layer = layers["dns"]
            dns_info = {
                "isResponse": dns_layer.get("dns.flags.response", "0") == "1",
                "queryName": dns_layer.get("dns.qry.name", ""),
                "queryType": dns_layer.get("dns.qry.type", ""),
                "responseCode": dns_layer.get("dns.flags.rcode", "")
            }
            
            # Extract answers if available
            if "dns.a" in dns_layer:
                if isinstance(dns_layer["dns.a"], list):
                    dns_info["answers"] = dns_layer["dns.a"]
                else:
                    dns_info["answers"] = [dns_layer["dns.a"]]
            
        # Extract payload if available
        payload = None
        if "data" in layers and "data.data" in layers["data"]:
            hex_data = layers["data"]["data.data"]
            try:
                # Try to decode the hex data
                payload = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
            except (ValueError, UnicodeDecodeError):
                payload = f"HEX:{hex_data}"
                
        return DetailedPacket(
            id=str(self.packet_id_counter),
            timestamp=timestamp,
            sourceIP=src_ip,
            destinationIP=dst_ip,
            protocol=protocol,
            length=bytes_transferred,
            ttl=ttl,
            sourcePort=src_port,
            destinationPort=dst_port,
            tcpFlags=tcp_flags,
            httpInfo=http_info,
            dnsInfo=dns_info,
            payload=payload,
            raw_data=None  # Don't store the full packet to save memory
        )

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
        
        # Check application layer protocols first
        if "http" in layers:
            return "HTTP"
        elif "tls" in layers:
            return "HTTPS"  # Assume TLS is HTTPS
        elif "dns" in layers:
            return "DNS"
        
        # Check transport layer
        if "tcp" in layers:
            tcp_layer = layers["tcp"]
            
            # Check for well-known ports
            if "tcp.dstport" in tcp_layer:
                dst_port = tcp_layer["tcp.dstport"]
                if dst_port == "80":
                    return "HTTP"
                elif dst_port == "443":
                    return "HTTPS"
                elif dst_port == "22":
                    return "SSH"
                elif dst_port == "21":
                    return "FTP"
                elif dst_port == "23":
                    return "TELNET"
                
            return "TCP"
        elif "udp" in layers:
            udp_layer = layers["udp"]
            
            # Check for well-known ports
            if "udp.dstport" in udp_layer:
                dst_port = udp_layer["udp.dstport"]
                if dst_port == "53":
                    return "DNS"
                elif dst_port == "123":
                    return "NTP"
                elif dst_port == "67" or dst_port == "68":
                    return "DHCP"
                    
            return "UDP"
        elif "icmp" in layers:
            return "ICMP"
            
        return "OTHER"

    def _get_visualization_data(self) -> Dict[str, Any]:
        return {
            "hosts": [asdict(host) for host in self.hosts.values()],
            "streams": [asdict(stream) for stream in self.streams.values()]
        }
        
    def get_packet_details(self, source_id: str, target_id: str, protocol: str) -> List[Dict[str, Any]]:
        """Return detailed packet information for a specific connection"""
        stream_key = f"{source_id}-{target_id}-{protocol}"
        
        # Check if we have packets for this stream
        if stream_key in self.packets:
            # Convert packets to dictionaries and return
            return [asdict(packet) for packet in self.packets[stream_key]]
            
        # Try the reverse direction
        reverse_key = f"{target_id}-{source_id}-{protocol}"
        if reverse_key in self.packets:
            return [asdict(packet) for packet in self.packets[reverse_key]]
            
        # No packets found
        return []

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

def start_realistic_simulation():
    """Generate more realistic network traffic simulation with common services and protocols"""
    aggregator = NetworkTrafficAggregator()
    
    # Create a more realistic network topology
    network_topology = {
        'gateway': '192.168.1.1',
        'local_devices': [
            '192.168.1.100',  # Your PC
            '192.168.1.101',  # Phone
            '192.168.1.102',  # Tablet
            '192.168.1.103',  # Smart TV
            '192.168.1.104',  # IoT Device
        ],
        'external_services': [
            {'ip': '8.8.8.8', 'service': 'DNS'},
            {'ip': '8.8.4.4', 'service': 'DNS'},
            {'ip': '93.184.216.34', 'service': 'HTTP/HTTPS'},  # example.com
            {'ip': '31.13.65.36', 'service': 'HTTPS'},  # Facebook
            {'ip': '142.250.185.78', 'service': 'HTTPS'},  # Google
            {'ip': '52.96.165.152', 'service': 'HTTPS'},  # Microsoft
            {'ip': '151.101.1.140', 'service': 'HTTPS'},  # Reddit
        ]
    }
    
    # Communication patterns
    patterns = [
        # DNS queries (local devices to DNS servers)
        {'src': 'local_devices', 'dst': '8.8.8.8', 'protocol': 'DNS', 'frequency': 10, 'size_range': (60, 120)},
        {'src': 'local_devices', 'dst': '8.8.4.4', 'protocol': 'DNS', 'frequency': 5, 'size_range': (60, 120)},
        
        # HTTP/HTTPS traffic (local devices to external services)
        {'src': 'local_devices', 'dst': 'external_services', 'protocol': 'HTTP', 'frequency': 3, 'size_range': (200, 1500)},
        {'src': 'local_devices', 'dst': 'external_services', 'protocol': 'HTTPS', 'frequency': 15, 'size_range': (200, 1500)},
        
        # Local network traffic
        {'src': 'local_devices', 'dst': 'local_devices', 'protocol': 'TCP', 'frequency': 2, 'size_range': (80, 400)},
        {'src': 'local_devices', 'dst': 'gateway', 'protocol': 'UDP', 'frequency': 5, 'size_range': (100, 300)},
    ]
    
    print("Starting realistic network traffic simulation")
    socketio.emit('captureStatus', {
        "status": "started", 
        "message": "Realistic network simulation started"
    })
    
    packet_count = 0
    is_running = True
    last_update_time = time.time()
    update_batch = []
    
    try:
        while is_running:
            # Select a random communication pattern
            pattern = random.choice(patterns)
            
            # Determine source IP
            if pattern['src'] == 'local_devices':
                src_ip = random.choice(network_topology['local_devices'])
            elif pattern['src'] == 'gateway':
                src_ip = network_topology['gateway']
            else:
                src_ip = pattern['src']
                
            # Determine destination IP
            if pattern['dst'] == 'local_devices':
                dst_ip = random.choice(network_topology['local_devices'])
                while dst_ip == src_ip:  # Ensure different destination
                    dst_ip = random.choice(network_topology['local_devices'])
            elif pattern['dst'] == 'external_services':
                service = random.choice(network_topology['external_services'])
                dst_ip = service['ip']
            elif pattern['dst'] == 'gateway':
                dst_ip = network_topology['gateway']
            else:
                dst_ip = pattern['dst']
            
            # Create the packet
            protocol = pattern['protocol']
            size = random.randint(*pattern['size_range'])
            
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
            
            # Create a packet in the format expected by add_packet
            packet = {
                "_source": {
                    "layers": {
                        "frame": {
                            "frame.time_epoch": str(time.time())
                        },
                        "ip": {
                            "ip.src": src_ip,
                            "ip.dst": dst_ip,
                            "ip.proto": "6" if protocol in ['TCP', 'HTTP', 'HTTPS'] else
                                       "17" if protocol in ['UDP', 'DNS'] else "1",
                            "ip.len": str(size)
                        }
                    }
                }
            }
            
            # Add protocol specific data
            if tcp_data:
                packet["_source"]["layers"]["tcp"] = tcp_data
            if udp_data:
                packet["_source"]["layers"]["udp"] = udp_data
                
            # Process the packet
            visualization_data = aggregator.add_packet(packet)
            update_batch.append(visualization_data)
            packet_count += 1
            
            # Emit updates periodically
            current_time = time.time()
            if update_batch and (current_time - last_update_time > 0.2 or len(update_batch) >= 5):
                # Send the most recent update
                recent_update = update_batch[-1]
                socketio.emit('networkUpdate', recent_update)
                
                # Log statistics occasionally
                if packet_count % 20 == 0:
                    print(f"Simulated {packet_count} packets, {len(recent_update['hosts'])} hosts, {len(recent_update['streams'])} streams")
                
                # Reset batch tracking
                update_batch = []
                last_update_time = current_time
                
            # Add a short delay based on the pattern frequency
            socketio.sleep(1.0 / pattern['frequency'])
            
    except Exception as e:
        print(f"Error in realistic simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Realistic simulation stopped")
        if update_batch:
            socketio.emit('networkUpdate', update_batch[-1])

# Update the Socket.IO event handler to support realistic simulation
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
    
    try:
        socketio.run(app, host='0.0.0.0', port=3001, debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTIP: Make sure you're running this script from within the virtual environment.")
        print("Use: source venv/bin/activate && python serve_visualization.py")

@socketio.on('requestPacketDetails')
def handle_packet_details_request(data):
    """Handler for packet detail requests from frontend"""
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    protocol = data.get('protocol')
    
    if not all([source_id, target_id, protocol]):
        print(f"Invalid packet details request: missing parameters. Got: {data}")
        return
    
    print(f"Packet details requested for connection: {source_id}-{target_id}-{protocol}")
    
    # Use the global test traffic generator's aggregator if it exists and is running
    if test_traffic_generator.running:
        packets = test_traffic_generator.aggregator.get_packet_details(source_id, target_id, protocol)
    else:
        # Create a new aggregator just for this request
        # This is a temporary solution - in a production app, you'd want to keep the aggregator in a global state
        aggregator = NetworkTrafficAggregator()
        packets = aggregator.get_packet_details(source_id, target_id, protocol)
    
    print(f"Found {len(packets)} packets for connection")
    socketio.emit('packetDetails', {"packets": packets})
#!/usr/bin/env python3
import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
import random

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", 
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
            "hosts": list(self.hosts.values()),
            "streams": list(self.streams.values())
        }


def start_capture(network_interface='any'):
    aggregator = NetworkTrafficAggregator()
    
    try:
        # Use tshark to capture network traffic
        tshark_process = subprocess.Popen(
            ["sudo", "tshark", "-i", network_interface, "-T", "json", "-l", "-f", "ip"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        buffer = ""
        while True:
            output = tshark_process.stdout.readline()
            if output == "" and tshark_process.poll() is not None:
                break
                
            if output:
                buffer += output
                try:
                    packet = json.loads(buffer)
                    visualization_data = aggregator.add_packet(packet)
                    socketio.emit('networkUpdate', visualization_data)
                    buffer = ""
                except json.JSONDecodeError:
                    # Incomplete JSON, continue buffering
                    if len(buffer) > 1000000:  # Reset if buffer gets too large
                        buffer = ""
                        
            error = tshark_process.stderr.readline()
            if error:
                print(f"tshark error: {error}", file=sys.stderr)
                if "Permission denied" in error:
                    socketio.emit('error', {
                        "message": "Permission denied. Please run the server with sudo privileges."
                    })
                    
    except Exception as e:
        print(f"Failed to start tshark: {e}", file=sys.stderr)
        socketio.emit('error', {
            "message": "Failed to start packet capture. Check permissions and tshark installation."
        })
    finally:
        if tshark_process and tshark_process.poll() is None:
            tshark_process.terminate()
            tshark_process.wait()
            

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
test_traffic_generator = TestTrafficGenerator()

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
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3002
    
    print(f"Server running on port {PORT}")
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)
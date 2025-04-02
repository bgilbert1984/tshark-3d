#!/usr/bin/env python3
import json
import signal
import subprocess
import sys
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Set
import random
import uuid
import re

try:
    from flask import Flask, jsonify, request, send_from_directory
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
    sourcePort: Optional[int] = None
    destinationPort: Optional[int] = None
    tcpFlags: Optional[Dict[str, bool]] = None
    payload: Optional[str] = None
    httpInfo: Optional[Dict[str, Any]] = None
    dnsInfo: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None  # Store raw packet data for reference

@dataclass
class WiresharkData:
    hosts: List[NetworkHost] = field(default_factory=list)
    streams: List[NetworkStream] = field(default_factory=list)

class NetworkTrafficAggregator:
    def __init__(self):
        self.hosts: Dict[str, NetworkHost] = {}
        self.streams: Dict[str, NetworkStream] = {}
        self.packets: Dict[str, List[DetailedPacket]] = {}  # Store packets by stream key
        self.host_id_counter = 0
        self.max_packets_per_stream = 100  # Limit packet storage to avoid memory issues

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
        if "http" in layers:
            return "HTTP"
        elif "tls" in layers:
            return "HTTPS"
        elif "dns" in layers:
            return "DNS"
        elif "icmp" in layers:
            return "ICMP"
        elif "tcp" in layers:
            return "TCP"
        elif "udp" in layers:
            return "UDP"
        return "OTHER"

    def _extract_tcp_flags(self, packet: Dict[str, Any]) -> Optional[Dict[str, bool]]:
        layers = packet["_source"]["layers"]
        if "tcp" not in layers:
            return None
            
        tcp_layer = layers["tcp"]
        flags = {}
        
        try:
            flags["syn"] = tcp_layer.get("tcp.flags.syn", "0") == "1"
            flags["ack"] = tcp_layer.get("tcp.flags.ack", "0") == "1"
            flags["fin"] = tcp_layer.get("tcp.flags.fin", "0") == "1"
            flags["rst"] = tcp_layer.get("tcp.flags.reset", "0") == "1"
            flags["psh"] = tcp_layer.get("tcp.flags.push", "0") == "1"
            flags["urg"] = tcp_layer.get("tcp.flags.urgent", "0") == "1"
            return flags
        except (KeyError, AttributeError):
            return None

    def _extract_http_info(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        layers = packet["_source"]["layers"]
        if "http" not in layers:
            return None
            
        http_layer = layers["http"]
        http_info = {}
        
        # HTTP Request
        if "http.request" in http_layer:
            http_info["method"] = http_layer.get("http.request.method", "")
            http_info["uri"] = http_layer.get("http.request.uri", "")
            http_info["version"] = http_layer.get("http.request.version", "")
            
            # Headers
            if "http.host" in http_layer:
                http_info["host"] = http_layer["http.host"]
            if "http.user_agent" in http_layer:
                http_info["userAgent"] = http_layer["http.user_agent"]
                
        # HTTP Response
        elif "http.response" in http_layer:
            http_info["statusCode"] = http_layer.get("http.response.code", "")
            http_info["statusPhrase"] = http_layer.get("http.response.phrase", "")
            
            # Headers
            if "http.content_type" in http_layer:
                http_info["contentType"] = http_layer["http.content_type"]
            if "http.content_length" in http_layer:
                http_info["contentLength"] = http_layer["http.content_length"]
                
        return http_info if http_info else None

    def _extract_dns_info(self, packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        layers = packet["_source"]["layers"]
        if "dns" not in layers:
            return None
            
        dns_layer = layers["dns"]
        dns_info = {}
        
        try:
            # Query information
            if "Queries" in dns_layer:
                queries = dns_layer["Queries"]
                dns_info["queryName"] = queries.get("dns.qry.name", "")
                dns_info["queryType"] = queries.get("dns.qry.type", "")
                
            # Response information
            if "dns.resp.code" in dns_layer:
                dns_info["responseCode"] = dns_layer["dns.resp.code"]
                
            # Extract answers if available
            answers = []
            if "Answers" in dns_layer and isinstance(dns_layer["Answers"], list):
                for answer in dns_layer["Answers"]:
                    answers.append({
                        "name": answer.get("dns.resp.name", ""),
                        "type": answer.get("dns.resp.type", ""),
                        "data": answer.get("dns.resp.data", "")
                    })
            elif "Answers" in dns_layer and isinstance(dns_layer["Answers"], dict):
                answers.append({
                    "name": dns_layer["Answers"].get("dns.resp.name", ""),
                    "type": dns_layer["Answers"].get("dns.resp.type", ""),
                    "data": dns_layer["Answers"].get("dns.resp.data", "")
                })
                
            if answers:
                dns_info["answers"] = answers
                
            return dns_info if dns_info else None
        except (KeyError, AttributeError) as e:
            print(f"Error extracting DNS info: {e}")
            return None

    def _extract_payload(self, packet: Dict[str, Any]) -> Optional[str]:
        """Extract and format packet payload for display"""
        try:
            layers = packet["_source"]["layers"]
            
            # Try to get data from various protocol layers
            data_layers = ["data", "data-text-lines", "http.file_data", "tcp.payload", "udp.payload"]
            
            for layer_name in data_layers:
                if layer_name in layers:
                    layer_data = layers[layer_name]
                    if isinstance(layer_data, str):
                        # Clean up any control characters for display
                        cleaned = re.sub(r'[^\x20-\x7E\r\n\t]', '.', layer_data)
                        return cleaned
            
            return None
        except (KeyError, AttributeError):
            return None

    def _create_detailed_packet(
        self, 
        packet: Dict[str, Any], 
        src_ip: str, 
        dst_ip: str, 
        length: int, 
        protocol: str, 
        timestamp: float
    ) -> DetailedPacket:
        """Create a detailed packet object with all available information"""
        layers = packet["_source"]["layers"]
        
        # Extract ports if available
        src_port = None
        dst_port = None
        if "tcp" in layers:
            src_port = int(layers["tcp"].get("tcp.srcport", 0))
            dst_port = int(layers["tcp"].get("tcp.dstport", 0))
        elif "udp" in layers:
            src_port = int(layers["udp"].get("udp.srcport", 0))
            dst_port = int(layers["udp"].get("udp.dstport", 0))
            
        # Extract TTL
        ttl = None
        if "ip" in layers and "ip.ttl" in layers["ip"]:
            ttl = int(layers["ip"]["ip.ttl"])
            
        # Create detailed packet
        detailed_packet = DetailedPacket(
            id=str(uuid.uuid4()),
            timestamp=timestamp,
            sourceIP=src_ip,
            destinationIP=dst_ip,
            protocol=protocol,
            length=length,
            ttl=ttl,
            sourcePort=src_port,
            destinationPort=dst_port,
            tcpFlags=self._extract_tcp_flags(packet),
            httpInfo=self._extract_http_info(packet),
            dnsInfo=self._extract_dns_info(packet),
            payload=self._extract_payload(packet)
        )
        
        return detailed_packet
    
    def get_packet_details(self, source_id: str, target_id: str, protocol: str) -> List[Dict[str, Any]]:
        """Retrieve detailed packet information for a specific stream"""
        stream_key = f"{source_id}-{target_id}-{protocol}"
        reverse_key = f"{target_id}-{source_id}-{protocol}"
        
        packets = []
        
        # Check both directions of communication
        for key in [stream_key, reverse_key]:
            if key in self.packets:
                packets.extend([asdict(packet) for packet in self.packets[key]])
        
        return packets

    def _get_visualization_data(self) -> Dict[str, Any]:
        return {
            "hosts": [asdict(host) for host in self.hosts.values()],
            "streams": [asdict(stream) for stream in self.streams.values()]
        }
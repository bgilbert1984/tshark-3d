#!/usr/bin/env python3

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import time

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the NetworkTrafficAggregator class from serve_visualization
from serve_visualization import NetworkTrafficAggregator

class TestNetworkTrafficAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = NetworkTrafficAggregator()

    def test_initialization(self):
        """Test that the aggregator initializes with empty data structures"""
        self.assertEqual(len(self.aggregator.hosts), 0)
        self.assertEqual(len(self.aggregator.streams), 0)

    def test_add_packet(self):
        """Test that packets can be added and tracked"""
        # Create a mock packet
        mock_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "100"
                    },
                    "tcp": {
                        "tcp.srcport": "12345",
                        "tcp.dstport": "80"
                    }
                }
            }
        }

        # Add the packet
        result = self.aggregator.add_packet(mock_packet)

        # Check that hosts were created
        self.assertEqual(len(self.aggregator.hosts), 2)
        
        # Find the hosts by IP
        host1 = None
        host2 = None
        for host in self.aggregator.hosts.values():
            if host.ip == "192.168.1.1":
                host1 = host
            elif host.ip == "192.168.1.2":
                host2 = host
                
        self.assertIsNotNone(host1)
        self.assertIsNotNone(host2)

        # Check that a stream was created
        self.assertEqual(len(self.aggregator.streams), 1)
        
        # Check that the network data is returned correctly
        self.assertIn("hosts", result)
        self.assertIn("streams", result)
        self.assertEqual(len(result["hosts"]), 2)
        self.assertEqual(len(result["streams"]), 1)

    def test_protocol_detection(self):
        """Test that protocols are correctly detected"""
        # TCP packet
        tcp_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "100"
                    },
                    "tcp": {
                        "tcp.srcport": "12345",
                        "tcp.dstport": "80"
                    }
                }
            }
        }
        self.aggregator.add_packet(tcp_packet)
        
        # Get the first stream
        stream_id = list(self.aggregator.streams.keys())[0]
        stream = self.aggregator.streams[stream_id]
        
        # Check that TCP was detected
        self.assertEqual(stream.protocol, "TCP")
        
        # Reset aggregator
        self.aggregator = NetworkTrafficAggregator()
        
        # UDP packet
        udp_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "100"
                    },
                    "udp": {
                        "udp.srcport": "12345",
                        "udp.dstport": "53"
                    }
                }
            }
        }
        self.aggregator.add_packet(udp_packet)
        
        # Get the first stream
        stream_id = list(self.aggregator.streams.keys())[0]
        stream = self.aggregator.streams[stream_id]
        
        # Check that UDP was detected
        self.assertEqual(stream.protocol, "UDP")
        
        # Reset aggregator
        self.aggregator = NetworkTrafficAggregator()
        
        # HTTP packet (TCP on port 80)
        http_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "500"
                    },
                    "tcp": {
                        "tcp.srcport": "12345",
                        "tcp.dstport": "80"
                    },
                    "http": {
                        "http.request.method": "GET",
                        "http.request.uri": "/index.html",
                        "http.host": "example.com"
                    }
                }
            }
        }
        self.aggregator.add_packet(http_packet)
        
        # Get the first stream
        stream_id = list(self.aggregator.streams.keys())[0]
        stream = self.aggregator.streams[stream_id]
        
        # Check that HTTP was detected
        self.assertEqual(stream.protocol, "HTTP")
        
        # Reset aggregator
        self.aggregator = NetworkTrafficAggregator()
        
        # HTTPS packet (TCP on port 443)
        https_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "300"
                    },
                    "tcp": {
                        "tcp.srcport": "12345",
                        "tcp.dstport": "443"
                    },
                    "tls": {
                        "tls.handshake": "16"
                    }
                }
            }
        }
        self.aggregator.add_packet(https_packet)
        
        # Get the first stream
        stream_id = list(self.aggregator.streams.keys())[0]
        stream = self.aggregator.streams[stream_id]
        
        # Check that HTTPS was detected
        self.assertEqual(stream.protocol, "HTTPS")
        
        # Reset aggregator
        self.aggregator = NetworkTrafficAggregator()
        
        # DNS packet (UDP on port 53)
        dns_packet = {
            "_source": {
                "layers": {
                    "frame": {"frame.time_epoch": str(time.time())},
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "8.8.8.8",
                        "ip.len": "75"
                    },
                    "udp": {
                        "udp.srcport": "12345",
                        "udp.dstport": "53"
                    },
                    "dns": {
                        "dns.qry.name": "example.com",
                        "dns.flags.response": "0"
                    }
                }
            }
        }
        self.aggregator.add_packet(dns_packet)
        
        # Get the first stream
        stream_id = list(self.aggregator.streams.keys())[0]
        stream = self.aggregator.streams[stream_id]
        
        # Check that DNS was detected
        self.assertEqual(stream.protocol, "DNS")

    def test_get_or_create_host(self):
        """Test that hosts are correctly created or retrieved"""
        # First call should create a new host
        host1 = self.aggregator._get_or_create_host("192.168.1.1")
        self.assertEqual(host1.ip, "192.168.1.1")
        self.assertEqual(host1.id, "1")
        
        # Second call with same IP should return the existing host
        host2 = self.aggregator._get_or_create_host("192.168.1.1")
        self.assertEqual(host2.ip, "192.168.1.1")
        self.assertEqual(host2.id, "1")
        self.assertIs(host1, host2)  # Should be the same object
        
        # New IP should create a new host
        host3 = self.aggregator._get_or_create_host("192.168.1.2")
        self.assertEqual(host3.ip, "192.168.1.2")
        self.assertEqual(host3.id, "2")
        self.assertIsNot(host1, host3)  # Should be different objects
        
    def test_deep_packet_inspection(self):
        """Test deep packet inspection capabilities"""
        # HTTP packet with detailed data
        http_packet = {
            "_source": {
                "layers": {
                    "frame": {
                        "frame.time_epoch": str(time.time()),
                        "frame.len": "1024"
                    },
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "192.168.1.2",
                        "ip.len": "1000",
                        "ip.ttl": "64"
                    },
                    "tcp": {
                        "tcp.srcport": "12345",
                        "tcp.dstport": "80",
                        "tcp.flags": "0x0018",  # PSH, ACK
                        "tcp.flags.syn": "0",
                        "tcp.flags.ack": "1",
                        "tcp.flags.push": "1"
                    },
                    "http": {
                        "http.request.method": "POST",
                        "http.request.uri": "/api/data",
                        "http.host": "example.com",
                        "http.user_agent": "Mozilla/5.0",
                        "http.content_type": "application/json",
                        "http.content_length": "250"
                    },
                    "data": {
                        "data.data": "7b2264617461223a202268656c6c6f20776f726c64227d"  # {"data": "hello world"}
                    }
                }
            }
        }
        
        # If the enhanced _extract_packet_details method exists, test it
        if hasattr(self.aggregator, '_extract_packet_details'):
            details = self.aggregator._extract_packet_details(http_packet)
            self.assertIsNotNone(details)
            self.assertEqual(details.get('protocol'), 'HTTP')
            self.assertEqual(details.get('sourceIP'), '192.168.1.1')
            self.assertEqual(details.get('destinationIP'), '192.168.1.2')
            self.assertEqual(details.get('sourcePort'), '12345')
            self.assertEqual(details.get('destinationPort'), '80')
            self.assertEqual(details.get('httpMethod'), 'POST')
            self.assertEqual(details.get('httpUri'), '/api/data')
            
        # DNS packet with query and response
        dns_packet = {
            "_source": {
                "layers": {
                    "frame": {
                        "frame.time_epoch": str(time.time()),
                        "frame.len": "120"
                    },
                    "ip": {
                        "ip.src": "192.168.1.1",
                        "ip.dst": "8.8.8.8",
                        "ip.len": "100",
                        "ip.ttl": "64"
                    },
                    "udp": {
                        "udp.srcport": "53124",
                        "udp.dstport": "53"
                    },
                    "dns": {
                        "dns.id": "0x1234",
                        "dns.flags.response": "0",
                        "dns.flags.opcode": "0",
                        "dns.qry.name": "example.com",
                        "dns.qry.type": "1",  # A record
                        "dns.count.queries": "1"
                    }
                }
            }
        }
        
        # If the enhanced _extract_packet_details method exists, test it
        if hasattr(self.aggregator, '_extract_packet_details'):
            details = self.aggregator._extract_packet_details(dns_packet)
            self.assertIsNotNone(details)
            self.assertEqual(details.get('protocol'), 'DNS')
            self.assertEqual(details.get('sourceIP'), '192.168.1.1')
            self.assertEqual(details.get('destinationIP'), '8.8.8.8')
            self.assertEqual(details.get('sourcePort'), '53124')
            self.assertEqual(details.get('destinationPort'), '53')
            self.assertEqual(details.get('dnsQueryName'), 'example.com')
            self.assertEqual(details.get('dnsQueryType'), '1')
            self.assertEqual(details.get('dnsIsResponse'), '0')

if __name__ == "__main__":
    unittest.main()

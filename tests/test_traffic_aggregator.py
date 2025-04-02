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

if __name__ == "__main__":
    unittest.main()

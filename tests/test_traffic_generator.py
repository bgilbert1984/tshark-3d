#!/usr/bin/env python3

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the TestTrafficGenerator class
from serve_visualization import TestTrafficGenerator

class TestTrafficGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = TestTrafficGenerator()

    def test_initialization(self):
        """Test that the generator initializes correctly"""
        self.assertIsNotNone(self.generator)
        self.assertEqual(self.generator.running, False)

    def test_generate_random_packet(self):
        """Test that random packets can be generated"""
        # Generate a packet
        packet = self.generator.generate_random_packet()
        
        # Check packet structure
        self.assertIn('_source', packet)
        self.assertIn('layers', packet['_source'])
        
        # Check required layers
        self.assertIn('frame', packet['_source']['layers'])
        self.assertIn('ip', packet['_source']['layers'])
        
        # Should have either TCP or UDP
        has_tcp_or_udp = ('tcp' in packet['_source']['layers'] or 
                         'udp' in packet['_source']['layers'])
        self.assertTrue(has_tcp_or_udp)
        
        # IP layer should have src, dst, and len
        ip_layer = packet['_source']['layers']['ip']
        self.assertIn('ip.src', ip_layer)
        self.assertIn('ip.dst', ip_layer)
        self.assertIn('ip.len', ip_layer)

    @patch('serve_visualization.socketio')
    def test_start(self, mock_socketio):
        """Test the start method"""
        # Call start
        self.generator.start()
        
        # Check that running is set to True
        self.assertTrue(self.generator.running)
        self.assertEqual(self.generator.connection_attempts, 0)

if __name__ == "__main__":
    unittest.main()

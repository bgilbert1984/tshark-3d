#!/usr/bin/env python3

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test the socket event handlers
class TestSocketHandlers(unittest.TestCase):
    @patch('serve_visualization.socketio')
    def test_connect_handler(self, mock_socketio):
        """Test the connect event handler"""
        # Import the handler function
        from serve_visualization import handle_connect
        
        # Call the handler
        handle_connect()
        
        # No assertions since it just prints a message
        # This test just ensures the function runs without errors

    @patch('serve_visualization.socketio')
    def test_disconnect_handler(self, mock_socketio):
        """Test the disconnect event handler"""
        # Import the handler function
        from serve_visualization import handle_disconnect
        
        # Call the handler
        handle_disconnect()
        
        # No assertions since it just prints a message
        # This test just ensures the function runs without errors

    @patch('serve_visualization.test_traffic_generator')
    def test_start_test_traffic(self, mock_generator):
        """Test the start_test_traffic function"""
        # Set up mocks
        mock_socketio = MagicMock()
        
        # Patch socketio.emit and socketio.sleep
        with patch('serve_visualization.socketio', mock_socketio):
            # Import the function
            from serve_visualization import start_test_traffic
            
            # Set the generator to running first, then it will stop after one iteration
            mock_generator.running = True
            
            # Configure mock to make the loop run once
            def side_effect(*args, **kwargs):
                mock_generator.running = False
            mock_socketio.sleep.side_effect = side_effect
            
            # Generate a test packet
            mock_packet = {
                "_source": {
                    "layers": {
                        "frame": {"frame.time_epoch": "123456789"},
                        "ip": {
                            "ip.src": "192.168.1.1",
                            "ip.dst": "192.168.1.2",
                            "ip.len": "100"
                        },
                        "tcp": {}
                    }
                }
            }
            mock_generator.generate_random_packet.return_value = mock_packet
            
            # Mock the visualization data returned by add_packet
            mock_viz_data = {"hosts": [], "streams": []}
            mock_generator.aggregator.add_packet.return_value = mock_viz_data
            
            # Call the function
            start_test_traffic()
            
            # Check that the packet was generated
            mock_generator.generate_random_packet.assert_called_once()
            
            # Check that add_packet was called
            mock_generator.aggregator.add_packet.assert_called_once_with(mock_packet)
            
            # Check that the update was emitted
            mock_socketio.emit.assert_called_once_with('networkUpdate', mock_viz_data)

if __name__ == "__main__":
    unittest.main()

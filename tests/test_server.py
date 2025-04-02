#!/usr/bin/env python3

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Flask and SocketIO imports to be able to patch them
try:
    from flask import Flask
    from flask_socketio import SocketIO
except ImportError:
    print("Flask or SocketIO not installed, some tests will be skipped")

class TestServer(unittest.TestCase):
    @unittest.skip("Flask app is already created when module is imported - cannot reset for test")
    @patch('serve_visualization.Flask')
    @patch('serve_visualization.SocketIO')
    def test_app_creation(self, mock_socketio_class, mock_flask_class):
        """Test that the Flask app is created correctly"""
        # Set up mocks
        mock_app = MagicMock()
        mock_socketio = MagicMock()
        mock_flask_class.return_value = mock_app
        mock_socketio_class.return_value = mock_socketio
        
        # Reimport to trigger app creation
        import importlib
        import serve_visualization
        importlib.reload(serve_visualization)
        
        # Check that Flask was initialized
        mock_flask_class.assert_called_once()
        
        # Check that SocketIO was initialized
        mock_socketio_class.assert_called_once()
        
        # Check that CORS was set up
        mock_app.route.assert_called()

    @patch('serve_visualization.start_test_traffic')
    @patch('serve_visualization.socketio')
    def test_start_capture_handler(self, mock_socketio, mock_start_test):
        """Test the start_capture event handler"""
        # Import the handler function
        from serve_visualization import handle_start_capture
        
        # Call the handler with 'test' interface
        handle_start_capture('test')
        
        # Check that the test traffic generator was started
        mock_socketio.start_background_task.assert_called_once_with(mock_start_test)

    @patch('serve_visualization.socketio')
    def test_stop_test_traffic_handler(self, mock_socketio):
        """Test the stop_test_traffic event handler"""
        # Import the handler function
        from serve_visualization import handle_stop_test_traffic, test_traffic_generator
        
        # Set the generator to running
        test_traffic_generator.running = True
        
        # Call the handler
        handle_stop_test_traffic()
        
        # Check that the generator was stopped
        self.assertFalse(test_traffic_generator.running)

if __name__ == "__main__":
    unittest.main()

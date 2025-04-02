#!/usr/bin/env python3

# Import necessary modules
import argparse
import os
import sys
import logging
import signal
import json
import traceback
from dataclasses import asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("NetworkViz")

try:
    from flask import Flask, send_from_directory
    from flask_cors import CORS
    from flask_socketio import SocketIO
except ImportError:
    logger.error("Required packages not found. Please install with:")
    logger.error("pip install flask flask-socketio flask-cors")
    sys.exit(1)

# Import our custom modules
try:
    from deep_packet_inspection import NetworkTrafficAggregator, DetailedPacket
    from test_traffic_generator import TestTrafficGenerator, start_realistic_simulation
except ImportError:
    # Fall back to importing from this file
    from serve_visualization import NetworkTrafficAggregator, TestTrafficGenerator, start_realistic_simulation

# Parse command line arguments
parser = argparse.ArgumentParser(description='Network Traffic Visualization Server')
parser.add_argument('--port', type=int, default=3001, help='Port to run the server on')
parser.add_argument('--interface', type=str, default='any', help='Network interface to capture from')
parser.add_argument('--test-only', action='store_true', help='Run in test mode only (no real traffic capture)')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--pcap', type=str, help='Read from PCAP file instead of live capture')
args = parser.parse_args()

# Check if running as root when not in test mode
if not args.test_only and os.geteuid() != 0:
    logger.warning("Not running as root. Real traffic capture requires sudo privileges.")
    logger.warning("Use --test-only for test traffic or run with sudo.")

# Create Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Configure SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Create global aggregator instance for use in socket handlers
aggregator = NetworkTrafficAggregator()
test_traffic_generator = TestTrafficGenerator()

# Flask routes for web server
@app.route('/')
def home():
    return send_from_directory('.', 'NetworkVisualization.html')

@app.route('/network')
def network():
    return send_from_directory('.', 'NetworkVisualization.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

# Health check endpoint
@app.route('/health')
def health():
    return {"status": "ok"}

# Socket.IO handlers
import socket_handlers

def start_server():
    """Start the Flask-SocketIO server"""
    try:
        logger.info(f"Starting Network Visualization Server on port {args.port}")
        logger.info(f"Web interface: http://localhost:{args.port}/")
        
        if args.test_only:
            logger.info("Running in test mode only (no real traffic capture)")
        elif args.pcap:
            logger.info(f"Reading from PCAP file: {args.pcap}")
        else:
            logger.info(f"Capturing traffic from interface: {args.interface}")
            logger.info("Root privileges are required for real traffic capture")
        
        # Make aggregator available to socket handlers
        socket_handlers.aggregator = aggregator
        socket_handlers.test_traffic_generator = test_traffic_generator
        
        socketio.run(app, host='0.0.0.0', port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        traceback.print_exc()
        sys.exit(1)

# Signal handlers for clean shutdown
def cleanup(signum, frame):
    logger.info('Cleaning up...')
    # Additional cleanup if needed
    logger.info('Server shut down successfully')
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == '__main__':
    start_server()
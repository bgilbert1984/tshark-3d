def start_capture(network_interface='any'):
    aggregator = NetworkTrafficAggregator()
    packet_buffer = {}  # Store partial packets until complete
    
    try:
        # Check if running as root (required for packet capture)
        if os.geteuid() != 0:
            print("Warning: Not running as root. Packet capture may fail due to permission issues.")
            socketio.emit('error', {
                "message": "Not running with sudo privileges. Real traffic capture requires sudo."
            })
            
        # Use tshark to capture network traffic with more verbose output
        # -V produces verbose output with all fields
        # -T json outputs as JSON
        # -e fields select specific fields for extraction
        tshark_cmd = [
            "tshark", "-i", network_interface, "-T", "json", 
            "-l", "-V", "-n", "-q",
            # Capture HTTP, DNS, and other application layer data
            "-d", "tcp.port==80,http", 
            "-d", "tcp.port==443,tls",
            "-d", "udp.port==53,dns"
        ]
        
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

@socketio.on('requestPacketDetails')
def handle_packet_details_request(data):
    """Handler for packet detail requests"""
    source_id = data.get('sourceId')
    target_id = data.get('targetId')
    protocol = data.get('protocol')
    
    if not all([source_id, target_id, protocol]):
        return
    
    # Use the global aggregator instance to get packet details
    global aggregator
    if not hasattr(handle_packet_details_request, 'aggregator'):
        print("Error: No active aggregator instance")
        return
    
    packets = aggregator.get_packet_details(source_id, target_id, protocol)
    socketio.emit('packetDetails', {"packets": packets})

@socketio.on('stopTestTraffic')
def handle_stop_test_traffic():
    print('Stopping test traffic generator')
    global test_traffic_generator
    test_traffic_generator.running = False

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
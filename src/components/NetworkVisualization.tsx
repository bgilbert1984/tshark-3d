import React, { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Stars } from '@react-three/drei';
import * as THREE from 'three';
import { io, Socket } from 'socket.io-client';
import { WiresharkData, NetworkHost, NetworkStream } from '../types/wireshark';
import TestTrafficControls from './TestTrafficControls';
import PacketInspector, { DetailedPacket } from './PacketInspector';

interface NetworkVisualizationProps {
  serverUrl?: string;
  interface?: string;
  initialData?: WiresharkData;
  width?: string;
  height?: string;
}

// Color schemes for different protocols
const protocolColors: Record<string, string> = {
  TCP: '#ff0000',
  UDP: '#00ff00',
  ICMP: '#0000ff',
  HTTP: '#ff00ff',
  HTTPS: '#00ffff',
  DNS: '#ffff00',
  OTHER: '#ffffff'
};

// Particle system for active connections
const ConnectionParticles: React.FC<{
  start: [number, number, number];
  end: [number, number, number];
  color: string;
  count?: number;
  speed?: number;
}> = ({ start, end, color, count = 10, speed = 1 }) => {
  const points = useRef<THREE.Points>(null);
  const particleCount = count;
  
  // Create particles along the path
  const particlesGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount);
    
    for (let i = 0; i < particleCount; i++) {
      // Random progress along the path (0 to 1)
      const progress = Math.random();
      
      // Position along the line
      positions[i * 3] = start[0] + (end[0] - start[0]) * progress;
      positions[i * 3 + 1] = start[1] + (end[1] - start[1]) * progress;
      positions[i * 3 + 2] = start[2] + (end[2] - start[2]) * progress;
      
      // Store velocity as progress per frame
      velocities[i] = (Math.random() * 0.01 + 0.005) * speed;
    }
    
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('velocity', new THREE.BufferAttribute(velocities, 1));
    
    return geometry;
  }, [start, end, particleCount, speed]);
  
  const particleMaterial = useMemo(() => {
    return new THREE.PointsMaterial({
      color: new THREE.Color(color),
      size: 0.2,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
  }, [color]);
  
  useFrame(() => {
    if (!points.current) return;
    
    const positions = points.current.geometry.attributes.position.array as Float32Array;
    const velocities = points.current.geometry.attributes.velocity.array as Float32Array;
    
    for (let i = 0; i < particleCount; i++) {
      // Update progress
      let progress = velocities[i];
      
      // Update positions
      positions[i * 3] += (end[0] - start[0]) * progress;
      positions[i * 3 + 1] += (end[1] - start[1]) * progress;
      positions[i * 3 + 2] += (end[2] - start[2]) * progress;
      
      // Reset particle if it reached the end
      const dx = positions[i * 3] - end[0];
      const dy = positions[i * 3 + 1] - end[1];
      const dz = positions[i * 3 + 2] - end[2];
      const distanceToEnd = Math.sqrt(dx * dx + dy * dy + dz * dz);
      
      if (distanceToEnd < 0.5) {
        // Reset to start
        positions[i * 3] = start[0];
        positions[i * 3 + 1] = start[1];
        positions[i * 3 + 2] = start[2];
      }
    }
    
    points.current.geometry.attributes.position.needsUpdate = true;
  });
  
  return (
    <points ref={points} geometry={particlesGeometry} material={particleMaterial} />
  );
};

const NodeMesh: React.FC<{ 
  position: [number, number, number]; 
  color?: string;
  size?: number;
  label?: string;
  data?: NetworkHost;
  onClick?: () => void;
}> = ({ position, color = '#ff0000', size = 0.5, label, data, onClick }) => {
  const [hovered, setHovered] = useState(false);
  const [pulseScale, setPulseScale] = useState(1);
  
  // Create a pulsing effect for nodes with high traffic
  useFrame((state, delta) => {
    if (data && data.packets > 100) {
      setPulseScale(1 + 0.1 * Math.sin(state.clock.elapsedTime * 3));
    }
  });

  return (
    <group position={position}>
      <mesh 
        scale={[pulseScale, pulseScale, pulseScale]}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
          if (onClick) onClick();
        }}
      >
        <sphereGeometry args={[size, 32, 32]} />
        <meshStandardMaterial 
          color={hovered ? '#ffffff' : color} 
          emissive={color}
          emissiveIntensity={0.3}
        />
      </mesh>
      
      {/* Glow effect */}
      <mesh scale={[size * 1.2, size * 1.2, size * 1.2]}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial 
          color={color} 
          transparent={true} 
          opacity={0.15} 
        />
      </mesh>
      
      {(hovered && data) && (
        <Html distanceFactor={10}>
          <div style={{
            backgroundColor: 'rgba(0,0,0,0.8)',
            padding: '8px',
            borderRadius: '4px',
            color: 'white',
            fontSize: '14px',
          zIndex: 1000
        }}>
          Connecting to server...
        </div>
      )}
      
      {/* Test Traffic Controls */}
      <TestTrafficControls 
        onStartTest={handleStartTestTraffic}
        onStopTest={handleStopTestTraffic}
        isRunning={isTestTrafficRunning}
      />
      
      {/* Network Stats Display */}
      <div style={{
        position: 'absolute',
        top: 16,
        right: 16,
        background: 'rgba(0, 0, 0, 0.8)',
        color: 'white',
        padding: '8px 16px',
        borderRadius: '4px',
        fontSize: '14px',
        zIndex: 1000
      }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>Network Stats</h3>
        <div>Hosts: {data.hosts.length}</div>
        <div>Connections: {data.streams.length}</div>
        <div>Total Packets: {data.hosts.reduce((sum, host) => sum + host.packets, 0)}</div>
        <div>Total Traffic: {formatBytes(data.hosts.reduce((sum, host) => sum + host.bytesTransferred, 0))}</div>
        {isTestTrafficRunning && (
          <div style={{ 
            marginTop: '8px',
            padding: '4px 8px',
            backgroundColor: '#ffcc00',
            color: '#333',
            borderRadius: '4px',
            fontWeight: 'bold'
          }}>
            Using test traffic
          </div>
        )}
      </div>
      
      {/* Protocol Legend */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        background: 'rgba(0, 0, 0, 0.8)',
        color: 'white',
        padding: '8px 16px',
        borderRadius: '4px',
        fontSize: '14px',
        zIndex: 1000
      }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>Protocols</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {Object.entries(protocolColors).map(([protocol, color]) => (
            <div key={protocol} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ 
                width: '16px', 
                height: '16px', 
                backgroundColor: color,
                borderRadius: '4px'
              }} />
              <span>{protocol}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Packet Inspector */}
      {showPacketInspector && selectedConnection && (
        <PacketInspector 
          socket={socketRef.current}
          selectedConnection={selectedConnection}
          onClose={handleClosePacketInspector}
        />
      )}
    </div>
  );
};

// Helper function to format bytes to KB, MB, etc.
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
} '12px',
            whiteSpace: 'nowrap'
          }}>
            <div>IP: {data.ip}</div>
            <div>Packets: {data.packets}</div>
            <div>Bytes: {data.bytesTransferred}</div>
          </div>
        </Html>
      )}
    </group>
  );
}

const EdgeLine: React.FC<{ 
  start: [number, number, number]; 
  end: [number, number, number]; 
  color?: string;
  width?: number;
  data?: NetworkStream;
  onClick?: () => void;
  active?: boolean;
}> = ({ 
  start, 
  end, 
  color = '#ffffff', 
  width = 1, 
  data, 
  onClick,
  active = false 
}) => {
  const [hovered, setHovered] = useState(false);
  const lineRef = useRef<THREE.Line>(null);
  const points = [new THREE.Vector3(...start), new THREE.Vector3(...end)];
  const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);

  const material = useMemo(() => 
    new THREE.LineBasicMaterial({ 
      color: color,
      linewidth: width,
      transparent: true,
      opacity: active || hovered ? 1 : 0.6,
    }), [color, width, active, hovered]);

  return (
    <group>
      <line 
        ref={lineRef}
        geometry={lineGeometry}
        material={material}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
          if (onClick) onClick();
        }}
      />
      
      {/* Particles for active connections */}
      {active && data && data.packets > 0 && (
        <ConnectionParticles 
          start={start} 
          end={end} 
          color={color} 
          count={Math.min(20, Math.max(5, Math.log(data.packets)))} 
          speed={Math.min(3, Math.max(0.5, Math.log(data.packets) / 3))}
        />
      )}
      
      {(hovered && data) && (
        <Html position={[
          (start[0] + end[0]) / 2,
          (start[1] + end[1]) / 2,
          (start[2] + end[2]) / 2
        ]}>
          <div style={{
            backgroundColor: 'rgba(0,0,0,0.8)',
            padding: '8px',
            borderRadius: '4px',
            color: 'white',
            fontSize: '12px',
            whiteSpace: 'nowrap'
          }}>
            <div>Protocol: {data.protocol}</div>
            <div>Packets: {data.packets}</div>
            <div>Bytes: {data.bytes}</div>
            <div style={{ 
              fontSize: '10px', 
              color: '#aaa', 
              marginTop: '4px' 
            }}>
              Click to inspect packets
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

const calculateNodePositions = (hosts: NetworkHost[]): Map<string, [number, number, number]> => {
  const positions = new Map<string, [number, number, number]>();
  const radius = 10;
  const angleStep = (2 * Math.PI) / hosts.length;

  hosts.forEach((host, index) => {
    const angle = angleStep * index;
    const x = radius * Math.cos(angle);
    const z = radius * Math.sin(angle);
    positions.set(host.id, [x, 0, z]);
  });

  return positions;
};

const NetworkGraph: React.FC<{ 
  data: WiresharkData;
  onSelectConnection: (sourceId: string, targetId: string, protocol: string) => void;
  selectedConnection?: string;
}> = ({ data, onSelectConnection, selectedConnection }) => {
  const nodePositions = useMemo(() => calculateNodePositions(data.hosts), [data.hosts]);
  const prevPositions = useRef(new Map<string, [number, number, number]>());
  const [transitionProgress, setTransitionProgress] = useState(1);

  useFrame((state, delta) => {
    // Smooth transition for node movements
    if (transitionProgress < 1) {
      setTransitionProgress(Math.min(1, transitionProgress + delta * 2));
    }
  });

  useEffect(() => {
    setTransitionProgress(0);
    const newPositions = calculateNodePositions(data.hosts);
    prevPositions.current = nodePositions;
  }, [data.hosts]);

  const interpolatePosition = (id: string, targetPos: [number, number, number]): [number, number, number] => {
    const prevPos = prevPositions.current.get(id);
    if (!prevPos || transitionProgress === 1) return targetPos;
    
    return [
      THREE.MathUtils.lerp(prevPos[0], targetPos[0], transitionProgress),
      THREE.MathUtils.lerp(prevPos[1], targetPos[1], transitionProgress),
      THREE.MathUtils.lerp(prevPos[2], targetPos[2], transitionProgress),
    ];
  };

  return (
    <>
      {/* Add subtle ambient stars for visual interest */}
      <Stars radius={50} depth={50} count={1500} factor={4} fade speed={0.5} />
      
      {/* Create network nodes */}
      {data.hosts.map((host) => {
        const targetPosition = nodePositions.get(host.id);
        if (!targetPosition) return null;
        
        const interpolatedPosition = interpolatePosition(host.id, targetPosition);
        
        // Scale nodes based on traffic volume with a logarithmic scale for better visibility
        const nodeSize = 0.5 + (Math.log(host.packets || 1) / Math.log(10)) * 0.2;
        
        return (
          <NodeMesh
            key={host.id}
            position={interpolatedPosition}
            color={protocolColors.OTHER}
            size={nodeSize}
            data={host}
          />
        );
      })}
      
      {/* Create connection edges */}
      {data.streams.map((stream) => {
        const sourcePosition = nodePositions.get(stream.source);
        const targetPosition = nodePositions.get(stream.target);
        if (!sourcePosition || !targetPosition) return null;

        const sourcePos = interpolatePosition(stream.source, sourcePosition);
        const targetPos = interpolatePosition(stream.target, targetPosition);
        
        const protocol = stream.protocol.toUpperCase();
        const color = protocolColors[protocol] || protocolColors.OTHER;
        
        // Scale line width based on traffic volume
        const width = 0.5 + (Math.log(stream.packets || 1) / Math.log(10)) * 0.2;
        
        // Check if this connection is selected
        const connectionKey = `${stream.source}-${stream.target}-${stream.protocol}`;
        const isSelected = (selectedConnection === connectionKey);
        
        return (
          <EdgeLine
            key={connectionKey}
            start={sourcePos}
            end={targetPos}
            color={color}
            width={width}
            data={stream}
            active={isSelected}
            onClick={() => onSelectConnection(stream.source, stream.target, stream.protocol)}
          />
        );
      })}
    </>
  );
}

export const NetworkVisualization: React.FC<NetworkVisualizationProps> = ({ 
  serverUrl = 'http://localhost:3001', // Updated to match combined server port
  interface: networkInterface = 'any',
  initialData,
  width = '100%', 
  height = '600px' 
}) => {
  const [data, setData] = useState<WiresharkData>(initialData || { hosts: [], streams: [] });
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTestTrafficRunning, setIsTestTrafficRunning] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<string | undefined>(undefined);
  const [showPacketInspector, setShowPacketInspector] = useState(false);
  
  const socketRef = useRef<Socket | undefined>(undefined);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connectToServer = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      setError(`Failed to connect to server after ${maxReconnectAttempts} attempts. Make sure the server is running with 'sudo python serve_visualization.py'`);
      return;
    }

    try {
      if (socketRef.current?.connected) {
        socketRef.current.disconnect();
      }

      console.log(`Attempting to connect to ${serverUrl}... (Attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);

      socketRef.current = io(serverUrl, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 20000, // Increased timeout
        forceNew: true // Force a new connection each time
      });

      socketRef.current.on('connect', () => {
        console.log('Connected to Wireshark server');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        socketRef.current?.emit('startCapture', networkInterface);
      });

      socketRef.current.on('connect_error', (err) => {
        console.error('Connection error:', err);
        setError(`Connection error: ${err.message}. Make sure the server is running with 'sudo python serve_visualization.py'`);
        reconnectAttempts.current++;
        setIsConnected(false);
        
        // Schedule retry with exponential backoff
        const retryDelay = Math.min(1000 * Math.pow(1.5, reconnectAttempts.current), 10000);
        console.log(`Will retry in ${retryDelay}ms`);
        setTimeout(() => connectToServer(), retryDelay);
      });

      socketRef.current.on('error', (err) => {
        console.error('Socket error:', err);
        setError(`Server error: ${err.message || 'Unknown error'}`);
      });

      socketRef.current.on('networkUpdate', (newData: WiresharkData) => {
        setData(newData);
      });

      socketRef.current.on('disconnect', (reason) => {
        console.log('Disconnected from server:', reason);
        setIsConnected(false);
        
        // For all disconnection reasons except explicit client disconnects, try to reconnect
        if (reason !== 'io client disconnect') {
          const reconnectDelay = 1500;
          console.log(`Attempting to reconnect in ${reconnectDelay}ms...`);
          setTimeout(() => connectToServer(), reconnectDelay);
        }
      });

    } catch (err) {
      console.error('Failed to initialize socket:', err);
      setError(`Failed to initialize connection: ${err instanceof Error ? err.message : 'Unknown error'}`);
      reconnectAttempts.current++;
      
      const retryDelay = Math.min(1000 * Math.pow(1.5, reconnectAttempts.current), 10000);
      setTimeout(() => connectToServer(), retryDelay);
    }
  }, [serverUrl, networkInterface]);

  useEffect(() => {
    connectToServer();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [connectToServer]);

  const handleStartTestTraffic = () => {
    if (socketRef.current?.connected) {
      // Disconnect from real traffic if connected
      socketRef.current.emit('stopTestTraffic');
      
      // Start test traffic
      socketRef.current.emit('startCapture', 'test');
      setIsTestTrafficRunning(true);
    }
  };

  const handleStopTestTraffic = () => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('stopTestTraffic');
      setIsTestTrafficRunning(false);
      
      // Reset visualization data
      setData({ hosts: [], streams: [] });
      
      // Reconnect to real traffic if needed
      socketRef.current.emit('startCapture', networkInterface);
    }
  };

  const handleSelectConnection = (sourceId: string, targetId: string, protocol: string) => {
    const connectionKey = `${sourceId}-${targetId}-${protocol}`;
    setSelectedConnection(connectionKey);
    setShowPacketInspector(true);
  };

  const handleClosePacketInspector = () => {
    setShowPacketInspector(false);
    setSelectedConnection(undefined);
  };

  return (
    <div style={{ width, height, position: 'relative' }}>
      <Canvas camera={{ position: [0, 20, 20], fov: 75 }}>
        <color attach="background" args={['#050a1c']} />
        <fog attach="fog" args={['#070b25', 25, 40]} />
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />
        <NetworkGraph 
          data={data} 
          onSelectConnection={handleSelectConnection}
          selectedConnection={selectedConnection}
        />
        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          rotateSpeed={0.5}
          minDistance={5}
          maxDistance={30}
        />
      </Canvas>
      
      {/* Connection status indicators */}
      {error && (
        <div style={{
          position: 'absolute',
          top: 16,
          left: 16,
          background: 'rgba(255, 0, 0, 0.8)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '4px',
          fontSize: '14px',
          zIndex: 1000
        }}>
          {error}
        </div>
      )}
      {!isConnected && !error && (
        <div style={{
          position: 'absolute',
          top: 16,
          left: 16,
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '4px',
          fontSize:
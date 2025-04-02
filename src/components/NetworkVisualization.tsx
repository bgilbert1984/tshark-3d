import React, { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';
import { io, Socket } from 'socket.io-client';
import { WiresharkData, NetworkHost, NetworkStream } from '../types/wireshark';
import TestTrafficControls from './TestTrafficControls';

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
  default: '#ffffff'
};

const NodeMesh: React.FC<{ 
  position: [number, number, number]; 
  color?: string;
  size?: number;
  label?: string;
  data?: NetworkHost;
}> = ({ position, color = '#ff0000', size = 0.5, label, data }) => {
  const [hovered, setHovered] = useState(false);

  return (
    <mesh 
      position={position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <sphereGeometry args={[size, 32, 32]} />
      <meshStandardMaterial color={hovered ? '#ffffff' : color} />
      {(hovered && data) && (
        <Html distanceFactor={10}>
          <div style={{
            backgroundColor: 'rgba(0,0,0,0.8)',
            padding: '8px',
            borderRadius: '4px',
            color: 'white',
            fontSize: '12px',
            whiteSpace: 'nowrap'
          }}>
            <div>IP: {data.ip}</div>
            <div>Packets: {data.packets}</div>
            <div>Bytes: {data.bytesTransferred}</div>
          </div>
        </Html>
      )}
    </mesh>
  );
}

const EdgeLine: React.FC<{ 
  start: [number, number, number]; 
  end: [number, number, number]; 
  color?: string;
  width?: number;
  data?: NetworkStream;
}> = ({ start, end, color = '#ffffff', width = 1, data }) => {
  const [hovered, setHovered] = useState(false);
  const points = [new THREE.Vector3(...start), new THREE.Vector3(...end)];
  const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);

  const material = useMemo(() => 
    new THREE.LineBasicMaterial({ 
      color: color,
      linewidth: width,
    }), [color, width]);

  return (
    <>
      <lineSegments 
        geometry={lineGeometry}
        material={material}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      />
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
          </div>
        </Html>
      )}
    </>
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

const NetworkGraph: React.FC<{ data: WiresharkData }> = ({ data }) => {
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
      {data.hosts.map((host) => {
        const targetPosition = nodePositions.get(host.id);
        if (!targetPosition) return null;
        
        const interpolatedPosition = interpolatePosition(host.id, targetPosition);
        
        return (
          <NodeMesh
            key={host.id}
            position={interpolatedPosition}
            color={protocolColors.default}
            size={0.5 + (Math.log(host.packets) / Math.log(10)) * 0.2}
            data={host}
          />
        );
      })}
      {data.streams.map((stream, index) => {
        const sourceTargetPos = nodePositions.get(stream.source);
        const targetTargetPos = nodePositions.get(stream.target);
        if (!sourceTargetPos || !targetTargetPos) return null;

        const sourcePos = interpolatePosition(stream.source, sourceTargetPos);
        const targetPos = interpolatePosition(stream.target, targetTargetPos);
        
        const protocol = stream.protocol.toUpperCase();
        const color = protocolColors[protocol] || protocolColors.default;
        const width = Math.log(stream.packets) / Math.log(10);
        
        return (
          <EdgeLine
            key={`${stream.source}-${stream.target}-${index}`}
            start={sourcePos}
            end={targetPos}
            color={color}
            width={width}
            data={stream}
          />
        );
      })}
    </>
  );
}

export const NetworkVisualization: React.FC<NetworkVisualizationProps> = ({ 
  serverUrl = 'http://localhost:3002',
  interface: networkInterface = 'any',
  initialData,
  width = '100%', 
  height = '600px' 
}) => {
  const [data, setData] = useState<WiresharkData>(initialData || { hosts: [], streams: [] });
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTestTrafficRunning, setIsTestTrafficRunning] = useState(false);
  const socketRef = useRef<Socket | undefined>(undefined);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connectToServer = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      setError(`Failed to connect to server after ${maxReconnectAttempts} attempts. Make sure the server is running with 'npm run start:server'`);
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
        setError(`Connection error: ${err.message}. Make sure the server is running with 'npm run start:server'`);
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

  return (
    <div style={{ width, height, position: 'relative' }}>
      <Canvas camera={{ position: [0, 20, 20], fov: 75 }}>
        <color attach="background" args={['#000000']} />
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <NetworkGraph data={data} />
        <OrbitControls />
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
        <div>Hosts: {data.hosts.length}</div>
        <div>Connections: {data.streams.length}</div>
        {isTestTrafficRunning && (
          <div style={{ color: '#ffcc00' }}>
            Using test traffic
          </div>
        )}
      </div>
    </div>
  );
}
import React, { useState, useEffect } from 'react';
import { Socket } from 'socket.io-client';

// Interface for detailed packet information
export interface DetailedPacket {
  id: string;
  timestamp: number;
  sourceIP: string;
  destinationIP: string;
  protocol: string;
  length: number;
  ttl?: number;
  sourcePort?: number;
  destinationPort?: number;
  tcpFlags?: {
    syn: boolean;
    ack: boolean;
    fin: boolean;
    rst: boolean;
    psh: boolean;
    urg: boolean;
  };
  payload?: string;
  httpInfo?: {
    method?: string;
    uri?: string;
    version?: string;
    host?: string;
    userAgent?: string;
    contentType?: string;
  };
  dnsInfo?: {
    queryName?: string;
    queryType?: string;
    responseCode?: string;
    answers?: Array<{name: string, type: string, data: string}>;
  };
}

interface PacketInspectorProps {
  socket: Socket | undefined;
  selectedConnection?: string;  // Format: "sourceID-targetID-protocol"
  onClose: () => void;
}

const PacketInspector: React.FC<PacketInspectorProps> = ({ 
  socket, 
  selectedConnection, 
  onClose 
}) => {
  const [packets, setPackets] = useState<DetailedPacket[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<DetailedPacket | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  
  useEffect(() => {
    if (!socket || !selectedConnection) return;
    
    setLoading(true);
    setPackets([]);
    
    // Parse the connection details
    const [sourceId, targetId, protocol] = selectedConnection.split('-');
    
    // Request detailed packets for this connection
    socket.emit('requestPacketDetails', {
      sourceId,
      targetId,
      protocol
    });
    
    // Listen for packet details
    const handlePacketDetails = (data: { packets: DetailedPacket[] }) => {
      setPackets(prevPackets => [...prevPackets, ...data.packets]);
      setLoading(false);
    };
    
    socket.on('packetDetails', handlePacketDetails);
    
    return () => {
      socket.off('packetDetails', handlePacketDetails);
    };
  }, [socket, selectedConnection]);
  
  const filteredPackets = packets.filter(packet => {
    if (!filter) return true;
    
    const lowerFilter = filter.toLowerCase();
    return (
      packet.sourceIP.includes(lowerFilter) ||
      packet.destinationIP.includes(lowerFilter) ||
      packet.protocol.toLowerCase().includes(lowerFilter) ||
      (packet.payload && packet.payload.toLowerCase().includes(lowerFilter))
    );
  });
  
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };
  
  return (
    <div style={{
      position: 'absolute',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      width: '80%',
      height: '80%',
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      borderRadius: '8px',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px',
      zIndex: 2000,
      color: 'white',
      boxShadow: '0 4px 30px rgba(0, 0, 0, 0.5)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ margin: 0 }}>Packet Inspector</h2>
        <button 
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            fontSize: '24px',
            cursor: 'pointer'
          }}
        >
          ×
        </button>
      </div>
      
      <div style={{ marginBottom: '16px' }}>
        <input
          type="text"
          placeholder="Filter packets..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            backgroundColor: '#333',
            border: 'none',
            borderRadius: '4px',
            color: 'white'
          }}
        />
      </div>
      
      <div style={{ display: 'flex', height: 'calc(100% - 100px)' }}>
        {/* Packet list */}
        <div style={{ 
          width: '30%', 
          overflowY: 'auto',
          borderRight: '1px solid #444',
          paddingRight: '16px'
        }}>
          {loading ? (
            <div>Loading packets...</div>
          ) : filteredPackets.length === 0 ? (
            <div>No packets found</div>
          ) : (
            filteredPackets.map(packet => (
              <div 
                key={packet.id}
                onClick={() => setSelectedPacket(packet)}
                style={{
                  padding: '8px',
                  marginBottom: '8px',
                  backgroundColor: selectedPacket?.id === packet.id ? '#444' : '#222',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                <div style={{ fontSize: '12px', color: '#aaa' }}>
                  {formatTimestamp(packet.timestamp)}
                </div>
                <div>
                  {packet.sourceIP}:{packet.sourcePort || '?'} → 
                  {packet.destinationIP}:{packet.destinationPort || '?'}
                </div>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  fontSize: '12px'
                }}>
                  <span style={{ 
                    backgroundColor: getProtocolColor(packet.protocol),
                    padding: '2px 6px',
                    borderRadius: '4px',
                    color: '#000'
                  }}>
                    {packet.protocol}
                  </span>
                  <span>{packet.length} bytes</span>
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Packet details */}
        <div style={{ flex: 1, paddingLeft: '16px', overflowY: 'auto' }}>
          {selectedPacket ? (
            <div>
              <h3>Packet Details</h3>
              
              <div style={{ marginBottom: '16px' }}>
                <h4>Basic Information</h4>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <tbody>
                    <tr>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Time</td>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                        {new Date(selectedPacket.timestamp).toLocaleString()}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Source</td>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                        {selectedPacket.sourceIP}:{selectedPacket.sourcePort || 'N/A'}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Destination</td>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                        {selectedPacket.destinationIP}:{selectedPacket.destinationPort || 'N/A'}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Protocol</td>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                        {selectedPacket.protocol}
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Length</td>
                      <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                        {selectedPacket.length} bytes
                      </td>
                    </tr>
                    {selectedPacket.ttl !== undefined && (
                      <tr>
                        <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>TTL</td>
                        <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                          {selectedPacket.ttl}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {selectedPacket.tcpFlags && (
                <div style={{ marginBottom: '16px' }}>
                  <h4>TCP Flags</h4>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {Object.entries(selectedPacket.tcpFlags).map(([flag, value]) => (
                      <div 
                        key={flag}
                        style={{
                          padding: '4px 8px',
                          backgroundColor: value ? '#4CAF50' : '#555',
                          borderRadius: '4px',
                          opacity: value ? 1 : 0.5
                        }}
                      >
                        {flag.toUpperCase()}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedPacket.httpInfo && (
                <div style={{ marginBottom: '16px' }}>
                  <h4>HTTP Information</h4>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <tbody>
                      {selectedPacket.httpInfo.method && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Method</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.httpInfo.method}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.httpInfo.uri && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>URI</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.httpInfo.uri}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.httpInfo.host && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Host</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.httpInfo.host}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.httpInfo.userAgent && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>User-Agent</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.httpInfo.userAgent}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.httpInfo.contentType && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Content-Type</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.httpInfo.contentType}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
              
              {selectedPacket.dnsInfo && (
                <div style={{ marginBottom: '16px' }}>
                  <h4>DNS Information</h4>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <tbody>
                      {selectedPacket.dnsInfo.queryName && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Query</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.dnsInfo.queryName}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.dnsInfo.queryType && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Type</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.dnsInfo.queryType}
                          </td>
                        </tr>
                      )}
                      {selectedPacket.dnsInfo.responseCode && (
                        <tr>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>Response</td>
                          <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>
                            {selectedPacket.dnsInfo.responseCode}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                  
                  {selectedPacket.dnsInfo.answers && selectedPacket.dnsInfo.answers.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <h5>Answers</h5>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', padding: '4px', borderBottom: '1px solid #444' }}>Name</th>
                            <th style={{ textAlign: 'left', padding: '4px', borderBottom: '1px solid #444' }}>Type</th>
                            <th style={{ textAlign: 'left', padding: '4px', borderBottom: '1px solid #444' }}>Data</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedPacket.dnsInfo.answers.map((answer, index) => (
                            <tr key={index}>
                              <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>{answer.name}</td>
                              <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>{answer.type}</td>
                              <td style={{ padding: '4px', borderBottom: '1px solid #444' }}>{answer.data}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
              
              {selectedPacket.payload && (
                <div>
                  <h4>Payload</h4>
                  <div style={{
                    padding: '8px',
                    backgroundColor: '#222',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '200px',
                    overflowY: 'auto'
                  }}>
                    {selectedPacket.payload}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              height: '100%',
              color: '#777' 
            }}>
              Select a packet to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function to get color for protocol
function getProtocolColor(protocol: string): string {
  const protocolColors: Record<string, string> = {
    'TCP': '#ff0000',
    'UDP': '#00ff00',
    'ICMP': '#0000ff',
    'HTTP': '#ff00ff',
    'HTTPS': '#00ffff',
    'DNS': '#ffff00',
  };
  
  return protocolColors[protocol.toUpperCase()] || '#ffffff';
}

export default PacketInspector;
import React, { useState } from 'react';

interface TestTrafficControlsProps {
  onStartTest: () => void;
  onStopTest: () => void;
  onStartRealistic?: () => void;
  onStartRealCapture?: () => void;
  isRunning: boolean;
}

const TestTrafficControls: React.FC<TestTrafficControlsProps> = ({
  onStartTest,
  onStopTest,
  onStartRealistic,
  onStartRealCapture,
  isRunning
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div style={{
      position: 'absolute',
      bottom: 16,
      left: 16,
      background: 'rgba(0, 0, 0, 0.8)',
      color: 'white',
      padding: '16px',
      borderRadius: '4px',
      zIndex: 1000
    }}>
      <h3 style={{ marginTop: 0, marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
        <span>Controls</span>
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{
            background: 'none',
            border: 'none',
            color: '#aaa',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
        </button>
      </h3>
      
      <div style={{ marginBottom: 8 }}>
        {isRunning ? (
          <button 
            onClick={onStopTest}
            style={{
              background: '#ff4444',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Stop Test Traffic
          </button>
        ) : (
          <button 
            onClick={onStartTest}
            style={{
              background: '#44cc44',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Generate Test Traffic
          </button>
        )}
      </div>
      
      {showAdvanced && (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '8px',
          marginTop: '12px',
          padding: '12px',
          background: 'rgba(50, 50, 50, 0.5)',
          borderRadius: '4px'
        }}>
          <div>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#ccc' }}>Advanced Options</h4>
          </div>
          
          {onStartRealistic && (
            <button 
              onClick={onStartRealistic}
              style={{
                background: '#4488cc',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Realistic Traffic Simulation
            </button>
          )}
          
          {onStartRealCapture && (
            <button 
              onClick={onStartRealCapture}
              style={{
                background: '#cc8844',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Capture Real Network Traffic
            </button>
          )}
          
          <div style={{ 
            fontSize: '12px', 
            color: '#aaa',
            margin: '4px 0 0 0'
          }}>
            Note: Capturing real traffic requires running the server with sudo privileges.
          </div>
        </div>
      )}
    </div>
  );
};

export default TestTrafficControls;
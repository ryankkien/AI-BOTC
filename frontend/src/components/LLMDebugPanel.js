import React from 'react';

function LLMDebugPanel({ title, debugData, onClose }) {
  return (
    <div style={{ padding: '10px', border: '1px solid #ccc', borderRadius: '5px', backgroundColor: '#f0f0f0', maxHeight: '300px', overflowY: 'auto', marginTop: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4>{title}</h4>
        <button onClick={onClose} style={{ cursor: 'pointer' }}>x</button>
      </div>
      <div>
        <h5>prompts:</h5>
        {debugData.prompts && debugData.prompts.length > 0 ? (
          debugData.prompts.map((p, idx) => (
            <div key={idx} style={{ marginBottom: '8px' }}>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{p}</pre>
            </div>
          ))
        ) : (
          <p>none</p>
        )}
      </div>
      <div>
        <h5>responses:</h5>
        {debugData.responses && debugData.responses.length > 0 ? (
          debugData.responses.map((r, idx) => (
            <div key={idx} style={{ marginBottom: '8px' }}>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{r}</pre>
            </div>
          ))
        ) : (
          <p>none</p>
        )}
      </div>
    </div>
  );
}

export default LLMDebugPanel; 
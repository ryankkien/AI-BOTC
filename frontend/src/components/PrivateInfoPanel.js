import React from 'react';

const panelStyle = {
    padding: '10px',
    border: '1px solid #ccc',
    borderRadius: '5px',
    backgroundColor: '#f9f9f9',
    marginBottom: '10px'
};

const listItemStyle = {
    margin: '5px 0'
}

function PrivateInfoPanel({ info }) {
  if (!info || Object.keys(info).length === 0) {
    return (
        <div style={panelStyle} className="private-info-panel">
            <h4>Your Private Information</h4>
            <p>No private information available yet.</p>
        </div>
    );
  }

  return (
    <div style={panelStyle} className="private-info-panel">
      <h4>Your Private Information</h4>
      <p style={listItemStyle}><strong>Your Role:</strong> {info.role || 'Unknown'}</p>
      <p style={listItemStyle}><strong>Alignment:</strong> {info.alignment || 'Unknown'}</p>
      {info.description && <p style={listItemStyle}><strong>Role Description:</strong> {info.description}</p>}
      
      {info.clues && info.clues.length > 0 && (
        <div>
          <strong>Clues:</strong>
          <ul>
            {info.clues.map((clue, index) => (
              <li key={index} style={listItemStyle}>{clue.night ? `(Night ${clue.night}) ` : ''}{clue.text}</li>
            ))}
          </ul>
        </div>
      )}

      {info.known_demon && <p style={listItemStyle}><strong>Known Demon:</strong> {info.known_demon}</p>}
      {info.known_minions && info.known_minions.length > 0 && 
        <p style={listItemStyle}><strong>Known Minions:</strong> {info.known_minions.join(', ')}</p>
      }
      {info.demon_bluffs && info.demon_bluffs.length > 0 && 
        <p style={listItemStyle}><strong>Demon Bluffs (for Demon):</strong> {info.demon_bluffs.join(', ')}</p>
      }

      {/* Add more specific private info displays as needed */}
    </div>
  );
}

export default PrivateInfoPanel; 
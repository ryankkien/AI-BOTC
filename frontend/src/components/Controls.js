import React, { useState } from 'react';

const controlsStyle = {
  padding: '10px',
  border: '1px solid #ccc',
  borderRadius: '5px',
  backgroundColor: '#f9f9f9'
};

const buttonStyle = {
  margin: '5px',
  padding: '8px 15px',
  cursor: 'pointer'
};

const selectStyle = {
    margin: '5px',
    padding: '8px'
};

function Controls({ gameState, onNominate, onVote, onNightAction, players = [], humanPlayerId }) {
  const [selectedTarget, setSelectedTarget] = useState('');
  const isHumanPlayerAlive = players.find(p => p.id === humanPlayerId)?.isAlive;

  const handleNomination = () => {
    if (selectedTarget && onNominate) {
      onNominate(selectedTarget);
      setSelectedTarget(''); //reset selection
    }
  };

  const handleNightActionChoice = () => {
    if (selectedTarget && onNightAction) {
      onNightAction({ target: selectedTarget }); //example structure
      setSelectedTarget('');
    }
  };

  //filter out the human player from target selection lists if they can't target self
  //this depends on specific ability rules, for now, allow self-target for simplicity in UI
  const alivePlayersForSelection = players.filter(p => p.isAlive);
  //const alivePlayersForSelectionNoSelf = players.filter(p => p.isAlive && p.id !== humanPlayerId);

  if (!isHumanPlayerAlive) {
    return <div style={controlsStyle} className="controls"><p>You are dead. No actions available.</p></div>;
  }
  
  return (
    <div style={controlsStyle} className="controls">
      <h4>Controls</h4>
      {gameState.currentPhase === 'DAY_CHAT' && (
        <div>
          <p>It is Day. Time to discuss and nominate.</p>
          <select value={selectedTarget} onChange={(e) => setSelectedTarget(e.target.value)} style={selectStyle}>
            <option value="">Select player to nominate</option>
            {alivePlayersForSelection.map(p => (
                 //cannot nominate self
                p.id !== humanPlayerId && <option key={p.id} value={p.id}>{p.name || p.id}</option>
            ))}
          </select>
          <button onClick={handleNomination} disabled={!selectedTarget} style={buttonStyle}>Nominate</button>
        </div>
      )}
      {gameState.currentPhase === 'VOTING' && gameState.nominee && (
        <div>
          <p>Player {gameState.nominee.name || gameState.nominee.id} is up for execution.</p>
          <button onClick={() => onVote(true)} style={{...buttonStyle, backgroundColor: '#5cb85c'}}>Vote YES</button>
          <button onClick={() => onVote(false)} style={{...buttonStyle, backgroundColor: '#d9534f'}}>Vote NO</button>
        </div>
      )}
      {(gameState.currentPhase === 'NIGHT' || gameState.currentPhase === 'FIRST_NIGHT') && (
        //this is a simplified night action control, needs to be role-specific
        <div> 
          <p>It is Night. Choose your action.</p>
          {/* Example: generic target selection. Real implementation needs role-specific UIs */}
          <select value={selectedTarget} onChange={(e) => setSelectedTarget(e.target.value)} style={selectStyle}>
            <option value="">Select target for night action</option>
            {alivePlayersForSelection.map(p => (
                 //some abilities cannot target self, e.g. Monk. Others can, e.g. Imp.
                 //this logic should be based on player's role which is in privateInfo
                <option key={p.id} value={p.id}>{p.name || p.id}</option>
            ))}
          </select>
          <button onClick={handleNightActionChoice} disabled={!selectedTarget} style={buttonStyle}>Confirm Night Action</button>
        </div>
      )}
      {/* Add more controls based on game state and player role */}
    </div>
  );
}

export default Controls; 
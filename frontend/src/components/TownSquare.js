import React from 'react';

//basic styling, can be improved greatly
const playerStyle = (isAlive) => ({
  border: '1px solid #ddd',
  padding: '10px',
  margin: '5px',
  backgroundColor: isAlive ? '#e6ffe6' : '#ffe6e6',
  cursor: 'pointer'
});

const townSquareStyle = {
  display: 'flex',
  flexWrap: 'wrap',
  justifyContent: 'center',
  alignItems: 'center',
  padding: '10px',
  border: '1px solid #ccc',
  borderRadius: '5px',
  minHeight: '150px' //ensure it has some height even when empty
};

function TownSquare({ players = [], onPlayerClick }) {
  if (!players || players.length === 0) {
    return <div style={townSquareStyle} className="town-square"><p>Waiting for players to join...</p></div>;
  }

  return (
    <div style={townSquareStyle} className="town-square">
      <h2>Town Square</h2>
      {players.map(player => (
        <div 
          key={player.id} 
          style={playerStyle(player.isAlive)} 
          onClick={() => player.isAlive && onPlayerClick(player.id)}
        >
          <p>{player.name || player.id}</p>
          <p>Status: {player.isAlive ? 'Alive' : 'Dead'}</p>
          {/* Add more player info display as needed */}
        </div>
      ))}
    </div>
  );
}

export default TownSquare; 
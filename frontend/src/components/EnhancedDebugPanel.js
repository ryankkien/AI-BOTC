import React, { useState, useEffect } from 'react';

const EnhancedDebugPanel = ({ 
  playerLLMDebug, 
  storytellerLLMDebug, 
  players, 
  gameState,
  onClose 
}) => {
  const [selectedBot, setSelectedBot] = useState('storyteller');
  const [selectedCategory, setSelectedCategory] = useState('thoughts');
  const [searchFilter, setSearchFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showTimestamps, setShowTimestamps] = useState(true);

  const panelStyle = {
    position: 'fixed',
    top: '10px',
    right: '10px',
    width: '80%',
    height: '90%',
    backgroundColor: '#ffffff',
    border: '2px solid #333',
    borderRadius: '8px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column',
    fontFamily: 'monospace'
  };

  const headerStyle = {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '15px',
    borderRadius: '6px 6px 0 0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const contentStyle = {
    display: 'flex',
    flex: 1,
    overflow: 'hidden'
  };

  const sidebarStyle = {
    width: '250px',
    backgroundColor: '#ecf0f1',
    borderRight: '1px solid #bdc3c7',
    display: 'flex',
    flexDirection: 'column'
  };

  const mainContentStyle = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  };

  const botListStyle = {
    padding: '10px',
    borderBottom: '1px solid #bdc3c7'
  };

  const botItemStyle = (isSelected) => ({
    padding: '8px 12px',
    margin: '2px 0',
    backgroundColor: isSelected ? '#3498db' : '#ffffff',
    color: isSelected ? 'white' : '#2c3e50',
    border: '1px solid #bdc3c7',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    transition: 'all 0.2s'
  });

  const categoryTabStyle = (isSelected) => ({
    padding: '10px 15px',
    backgroundColor: isSelected ? '#3498db' : '#95a5a6',
    color: 'white',
    border: 'none',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 'bold'
  });

  const debugContentStyle = {
    flex: 1,
    padding: '15px',
    overflow: 'auto',
    backgroundColor: '#f8f9fa'
  };

  const thoughtItemStyle = {
    backgroundColor: '#ffffff',
    border: '1px solid #dee2e6',
    borderRadius: '6px',
    margin: '8px 0',
    padding: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  };

  const promptStyle = {
    backgroundColor: '#e3f2fd',
    border: '1px solid #2196f3',
    borderRadius: '4px',
    padding: '10px',
    margin: '5px 0',
    fontSize: '11px',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflow: 'auto'
  };

  const responseStyle = {
    backgroundColor: '#f3e5f5',
    border: '1px solid #9c27b0',
    borderRadius: '4px',
    padding: '10px',
    margin: '5px 0',
    fontSize: '11px',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflow: 'auto'
  };

  const timestampStyle = {
    fontSize: '10px',
    color: '#6c757d',
    marginBottom: '5px'
  };

  const filterStyle = {
    width: '100%',
    padding: '8px',
    margin: '10px 0',
    border: '1px solid #ced4da',
    borderRadius: '4px',
    fontSize: '12px'
  };

  const controlsStyle = {
    padding: '10px',
    backgroundColor: '#f8f9fa',
    borderTop: '1px solid #dee2e6',
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    fontSize: '12px'
  };

  // Get available bots - include all players from the players list, not just those with debug data
  const availableBots = [
    'storyteller', 
    ...players.map(p => p.id),
    ...Object.keys(playerLLMDebug).filter(id => !players.find(p => p.id === id))
  ];

  // Get current bot's data
  const getCurrentBotData = () => {
    if (selectedBot === 'storyteller') {
      return storytellerLLMDebug;
    }
    return playerLLMDebug[selectedBot] || { prompts: [], responses: [] };
  };

  // Get bot display name
  const getBotDisplayName = (botId) => {
    if (botId === 'storyteller') return 'Storyteller';
    const player = players.find(p => p.id === botId);
    return player ? `${player.name} (${player.role || 'Unknown'})` : botId;
  };

  // Filter and combine prompts/responses with timestamps
  const getFilteredThoughts = () => {
    const botData = getCurrentBotData();
    const thoughts = [];

    // Combine prompts and responses with type indicators
    botData.prompts?.forEach((promptEntry, index) => {
      thoughts.push({
        type: 'prompt',
        content: typeof promptEntry === 'string' ? promptEntry : promptEntry.content,
        index,
        timestamp: typeof promptEntry === 'object' ? promptEntry.timestamp : new Date().toISOString(),
        metadata: typeof promptEntry === 'object' ? promptEntry : {}
      });
    });

    botData.responses?.forEach((responseEntry, index) => {
      thoughts.push({
        type: 'response',
        content: typeof responseEntry === 'string' ? responseEntry : responseEntry.content,
        index,
        timestamp: typeof responseEntry === 'object' ? responseEntry.timestamp : new Date().toISOString(),
        metadata: typeof responseEntry === 'object' ? responseEntry : {}
      });
    });

    // Sort by timestamp
    thoughts.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Apply search filter
    if (searchFilter) {
      return thoughts.filter(thought => 
        thought.content.toLowerCase().includes(searchFilter.toLowerCase())
      );
    }

    return thoughts;
  };

  // Get bot memory/information
  const getBotMemory = () => {
    if (selectedBot === 'storyteller') {
      return {
        gameState: gameState,
        type: 'storyteller'
      };
    }
    
    const player = players.find(p => p.id === selectedBot);
    return {
      role: player?.role,
      alignment: player?.alignment,
      status: player?.status,
      memory: player?.memory,
      type: 'player'
    };
  };

  const renderThoughts = () => {
    const thoughts = getFilteredThoughts();
    
    if (thoughts.length === 0) {
      const isStorytellerSelected = selectedBot === 'storyteller';
      const player = players.find(p => p.id === selectedBot);
      
      return (
        <div style={{ textAlign: 'center', color: '#6c757d', padding: '20px' }}>
          <div style={{ marginBottom: '10px' }}>
            No thoughts recorded yet for {isStorytellerSelected ? 'the Storyteller' : (player?.name || selectedBot)}.
          </div>
          {!isStorytellerSelected && player && (
            <div style={{ fontSize: '11px', backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '4px', margin: '10px 0' }}>
              <strong>Agent Info:</strong><br/>
              Role: {player.role || 'Unknown'}<br/>
              Status: {player.isAlive ? 'Alive' : 'Dead'}<br/>
              Alignment: {player.alignment || 'Unknown'}
            </div>
          )}
          <div style={{ fontSize: '10px', color: '#999' }}>
            Debug data will appear here when this agent makes decisions or takes actions.
          </div>
        </div>
      );
    }

    return thoughts.map((thought, index) => (
      <div key={index} style={thoughtItemStyle}>
        {showTimestamps && (
          <div style={timestampStyle}>
            <strong>{thought.type.toUpperCase()} #{thought.index + 1}</strong> - {new Date(thought.timestamp).toLocaleTimeString()}
            {thought.metadata.provider && (
              <span style={{ marginLeft: '10px', fontSize: '9px', backgroundColor: '#e9ecef', padding: '2px 6px', borderRadius: '3px' }}>
                {thought.metadata.provider}
              </span>
            )}
            {thought.metadata.generation_time_seconds && (
              <span style={{ marginLeft: '5px', fontSize: '9px', backgroundColor: '#d4edda', padding: '2px 6px', borderRadius: '3px' }}>
                {thought.metadata.generation_time_seconds}s
              </span>
            )}
          </div>
        )}
        <div style={thought.type === 'prompt' ? promptStyle : responseStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
            <strong>{thought.type === 'prompt' ? '🧠 PROMPT:' : '💭 RESPONSE:'}</strong>
            <div style={{ fontSize: '9px', color: '#6c757d' }}>
              {thought.type === 'prompt' && thought.metadata.prompt_length && `${thought.metadata.prompt_length} chars`}
              {thought.type === 'response' && thought.metadata.response_length && `${thought.metadata.response_length} chars`}
              {thought.metadata.prompt_hash && ` | Hash: ${thought.metadata.prompt_hash}`}
            </div>
          </div>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: '11px' }}>
            {thought.content}
          </div>
        </div>
      </div>
    ));
  };

  const renderMemory = () => {
    const memory = getBotMemory();
    
    return (
      <div style={debugContentStyle}>
        <h4>Bot Information & Memory</h4>
        <div style={thoughtItemStyle}>
          <pre style={{ fontSize: '11px', whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(memory, null, 2)}
          </pre>
        </div>
      </div>
    );
  };

  const renderStats = () => {
    const botData = getCurrentBotData();
    
    return (
      <div style={debugContentStyle}>
        <h4>Bot Statistics</h4>
        <div style={thoughtItemStyle}>
          <p><strong>Total Prompts:</strong> {botData.prompts?.length || 0}</p>
          <p><strong>Total Responses:</strong> {botData.responses?.length || 0}</p>
          <p><strong>Last Activity:</strong> {botData.prompts?.length > 0 ? 'Recently active' : 'No activity'}</p>
          {selectedBot !== 'storyteller' && (
            <>
              <p><strong>Role:</strong> {getBotDisplayName(selectedBot).split('(')[1]?.replace(')', '') || 'Unknown'}</p>
              <p><strong>Status:</strong> {players.find(p => p.id === selectedBot)?.isAlive ? 'Alive' : 'Dead'}</p>
            </>
          )}
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch (selectedCategory) {
      case 'thoughts':
        return (
          <div style={debugContentStyle}>
            <h4>Bot Thoughts & Reasoning</h4>
            {renderThoughts()}
          </div>
        );
      case 'memory':
        return renderMemory();
      case 'stats':
        return renderStats();
      default:
        return renderThoughts();
    }
  };

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <h3>🔍 Enhanced Bot Debug Panel</h3>
        <button 
          onClick={onClose}
          style={{
            backgroundColor: '#e74c3c',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            padding: '8px 12px',
            cursor: 'pointer'
          }}
        >
          ✕ Close
        </button>
      </div>

      <div style={contentStyle}>
        {/* Sidebar with bot selection */}
        <div style={sidebarStyle}>
          <div style={botListStyle}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Select Bot:</h4>
            {availableBots.map(botId => (
              <div
                key={botId}
                style={botItemStyle(selectedBot === botId)}
                onClick={() => setSelectedBot(botId)}
              >
                {getBotDisplayName(botId)}
                <div style={{ fontSize: '10px', opacity: 0.8 }}>
                  {botId === 'storyteller' ? 'Game Master' : `Player ${botId}`}
                  {/* Show activity indicator */}
                  <div style={{ marginTop: '2px', fontSize: '9px' }}>
                    {(() => {
                      const botData = botId === 'storyteller' ? storytellerLLMDebug : (playerLLMDebug[botId] || { prompts: [], responses: [] });
                      const totalActivity = (botData.prompts?.length || 0) + (botData.responses?.length || 0);
                      return totalActivity > 0 ? `📊 ${totalActivity} actions` : '⚪ No activity';
                    })()}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: '10px' }}>
            <h5 style={{ margin: '0 0 10px 0', fontSize: '12px' }}>Quick Stats:</h5>
            <div style={{ fontSize: '10px', color: '#6c757d' }}>
              <div>Total Bots: {availableBots.length}</div>
              <div>Active: {availableBots.filter(id => {
                const botData = id === 'storyteller' ? storytellerLLMDebug : (playerLLMDebug[id] || { prompts: [], responses: [] });
                return (botData.prompts?.length || 0) + (botData.responses?.length || 0) > 0;
              }).length}</div>
              <div>Players: {players.length}</div>
              <div>Alive: {players.filter(p => p.isAlive).length}</div>
            </div>
          </div>
        </div>

        {/* Main content area */}
        <div style={mainContentStyle}>
          {/* Category tabs */}
          <div style={{ display: 'flex', backgroundColor: '#95a5a6' }}>
            {['thoughts', 'memory', 'stats'].map(category => (
              <button
                key={category}
                style={categoryTabStyle(selectedCategory === category)}
                onClick={() => setSelectedCategory(category)}
              >
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </button>
            ))}
          </div>

          {/* Search and filters */}
          {selectedCategory === 'thoughts' && (
            <div style={{ padding: '10px', backgroundColor: '#f8f9fa', borderBottom: '1px solid #dee2e6' }}>
              <input
                type="text"
                placeholder="Search thoughts..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                style={filterStyle}
              />
            </div>
          )}

          {/* Content area */}
          {renderContent()}

          {/* Controls */}
          <div style={controlsStyle}>
            <label>
              <input
                type="checkbox"
                checked={showTimestamps}
                onChange={(e) => setShowTimestamps(e.target.checked)}
              />
              Show timestamps
            </label>
            <label>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
            <div style={{ marginLeft: 'auto', fontSize: '10px', color: '#6c757d' }}>
              Debugging: {getBotDisplayName(selectedBot)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedDebugPanel; 
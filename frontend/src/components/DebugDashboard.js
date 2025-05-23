import React, { useState, useEffect } from 'react';

const DebugDashboard = ({ 
  playerLLMDebug, 
  storytellerLLMDebug, 
  players, 
  gameState,
  onClose 
}) => {
  const [selectedView, setSelectedView] = useState('overview');
  const [selectedBot, setSelectedBot] = useState('storyteller');
  const [botInfo, setBotInfo] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5000);

  // Fetch detailed bot information
  const fetchBotInfo = async () => {
    try {
      const response = await fetch('http://localhost:8000/debug/bot_info');
      const data = await response.json();
      setBotInfo(data);
    } catch (error) {
      console.error('Failed to fetch bot info:', error);
    }
  };

  useEffect(() => {
    fetchBotInfo();
    
    if (autoRefresh) {
      const interval = setInterval(fetchBotInfo, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  const dashboardStyle = {
    position: 'fixed',
    top: '5px',
    left: '5px',
    right: '5px',
    bottom: '5px',
    backgroundColor: '#ffffff',
    border: '2px solid #333',
    borderRadius: '8px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column',
    fontFamily: 'monospace',
    fontSize: '12px'
  };

  const headerStyle = {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '10px 15px',
    borderRadius: '6px 6px 0 0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const navStyle = {
    backgroundColor: '#34495e',
    color: 'white',
    padding: '10px',
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    borderBottom: '1px solid #2c3e50'
  };

  const navButtonStyle = (isActive) => ({
    padding: '8px 12px',
    backgroundColor: isActive ? '#3498db' : 'transparent',
    color: 'white',
    border: '1px solid #3498db',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '11px'
  });

  const contentStyle = {
    flex: 1,
    display: 'flex',
    overflow: 'hidden'
  };

  const sidebarStyle = {
    width: '200px',
    backgroundColor: '#ecf0f1',
    borderRight: '1px solid #bdc3c7',
    overflow: 'auto'
  };

  const mainContentStyle = {
    flex: 1,
    padding: '15px',
    overflow: 'auto',
    backgroundColor: '#f8f9fa'
  };

  const cardStyle = {
    backgroundColor: '#ffffff',
    border: '1px solid #dee2e6',
    borderRadius: '6px',
    margin: '10px 0',
    padding: '15px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  };

  const statStyle = {
    display: 'inline-block',
    backgroundColor: '#e3f2fd',
    padding: '4px 8px',
    margin: '2px',
    borderRadius: '4px',
    fontSize: '10px'
  };

  const renderOverview = () => {
    if (!botInfo) return <div>Loading bot information...</div>;

    const totalBots = 1 + Object.keys(botInfo.players || {}).length;
    const activeBots = Object.keys(playerLLMDebug).length + (storytellerLLMDebug.prompts?.length > 0 ? 1 : 0);

    return (
      <div>
        <h3>🎮 Game Debug Overview</h3>
        
        <div style={cardStyle}>
          <h4>System Status</h4>
          <div style={statStyle}>Total Bots: {totalBots}</div>
          <div style={statStyle}>Active Bots: {activeBots}</div>
          <div style={statStyle}>Game Phase: {gameState.currentPhase || 'Unknown'}</div>
          <div style={statStyle}>Day: {gameState.dayNumber || 0}</div>
          <div style={statStyle}>Players Alive: {botInfo.storyteller?.memory?.game_state?.players_alive || 0}</div>
        </div>

        <div style={cardStyle}>
          <h4>🤖 Bot Activity Summary</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
            
            {/* Storyteller Card */}
            <div style={{ ...cardStyle, margin: '5px' }}>
              <h5>🎭 Storyteller</h5>
              <div style={statStyle}>Prompts: {storytellerLLMDebug.prompts?.length || 0}</div>
              <div style={statStyle}>Responses: {storytellerLLMDebug.responses?.length || 0}</div>
              <div style={statStyle}>Game Events: {botInfo.storyteller?.stats?.game_events_processed || 0}</div>
            </div>

            {/* Player Bots */}
            {Object.entries(botInfo.players || {}).map(([playerId, playerData]) => (
              <div key={playerId} style={{ ...cardStyle, margin: '5px' }}>
                <h5>👤 {playerData.name}</h5>
                <div style={statStyle}>Role: {playerData.role}</div>
                <div style={statStyle}>Status: {playerData.status?.alive ? 'Alive' : 'Dead'}</div>
                <div style={statStyle}>Prompts: {playerLLMDebug[playerId]?.prompts?.length || 0}</div>
                <div style={statStyle}>Responses: {playerLLMDebug[playerId]?.responses?.length || 0}</div>
                <div style={statStyle}>Actions: {playerData.stats?.actions_taken || 0}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={cardStyle}>
          <h4>📊 Recent Activity</h4>
          <div style={{ maxHeight: '200px', overflow: 'auto' }}>
            {botInfo.storyteller?.memory?.recent_actions?.map((action, index) => (
              <div key={index} style={{ padding: '5px', borderBottom: '1px solid #eee', fontSize: '10px' }}>
                <strong>{new Date(action.timestamp).toLocaleTimeString()}</strong>: {action.event || action.message || JSON.stringify(action)}
              </div>
            )) || <div>No recent activity</div>}
          </div>
        </div>
      </div>
    );
  };

  const renderBotDetails = () => {
    const isStoryteller = selectedBot === 'storyteller';
    const botData = isStoryteller ? storytellerLLMDebug : (playerLLMDebug[selectedBot] || { prompts: [], responses: [] });
    const botDetails = isStoryteller ? botInfo?.storyteller : botInfo?.players?.[selectedBot];

    return (
      <div>
        <h3>🔍 {isStoryteller ? 'Storyteller' : botDetails?.name || selectedBot} Details</h3>
        
        <div style={cardStyle}>
          <h4>Basic Information</h4>
          {!isStoryteller && (
            <>
              <div style={statStyle}>Role: {botDetails?.role}</div>
              <div style={statStyle}>Alignment: {botDetails?.alignment}</div>
              <div style={statStyle}>Status: {botDetails?.status?.alive ? 'Alive' : 'Dead'}</div>
            </>
          )}
          <div style={statStyle}>Type: {isStoryteller ? 'Game Master' : 'Player Bot'}</div>
        </div>

        <div style={cardStyle}>
          <h4>Memory & Knowledge</h4>
          <pre style={{ fontSize: '10px', whiteSpace: 'pre-wrap', maxHeight: '300px', overflow: 'auto' }}>
            {JSON.stringify(botDetails?.memory || {}, null, 2)}
          </pre>
        </div>

        <div style={cardStyle}>
          <h4>Statistics</h4>
          <div style={statStyle}>Total Prompts: {botData.prompts?.length || 0}</div>
          <div style={statStyle}>Total Responses: {botData.responses?.length || 0}</div>
          {botDetails?.stats && Object.entries(botDetails.stats).map(([key, value]) => (
            <div key={key} style={statStyle}>{key}: {value}</div>
          ))}
        </div>

        <div style={cardStyle}>
          <h4>Recent Thoughts</h4>
          <div style={{ maxHeight: '400px', overflow: 'auto' }}>
            {[...botData.prompts || [], ...botData.responses || []]
              .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0))
              .slice(0, 5)
              .map((thought, index) => (
                <div key={index} style={{ padding: '8px', borderBottom: '1px solid #eee', fontSize: '10px' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                    {thought.timestamp ? new Date(thought.timestamp).toLocaleTimeString() : 'Unknown time'}
                    {thought.provider && <span style={{ marginLeft: '10px', color: '#666' }}>({thought.provider})</span>}
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>
                    {typeof thought === 'string' ? thought : thought.content}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    );
  };

  const renderSystemLogs = () => {
    return (
      <div>
        <h3>📋 System Logs</h3>
        
        <div style={cardStyle}>
          <h4>Game State</h4>
          <pre style={{ fontSize: '10px', whiteSpace: 'pre-wrap', maxHeight: '200px', overflow: 'auto' }}>
            {JSON.stringify(gameState, null, 2)}
          </pre>
        </div>

        <div style={cardStyle}>
          <h4>Players</h4>
          <pre style={{ fontSize: '10px', whiteSpace: 'pre-wrap', maxHeight: '200px', overflow: 'auto' }}>
            {JSON.stringify(players, null, 2)}
          </pre>
        </div>

        <div style={cardStyle}>
          <h4>Debug Data Summary</h4>
          <div style={statStyle}>Storyteller Prompts: {storytellerLLMDebug.prompts?.length || 0}</div>
          <div style={statStyle}>Storyteller Responses: {storytellerLLMDebug.responses?.length || 0}</div>
          <div style={statStyle}>Player Bots Tracked: {Object.keys(playerLLMDebug).length}</div>
          <div style={statStyle}>Total Debug Entries: {
            (storytellerLLMDebug.prompts?.length || 0) + 
            (storytellerLLMDebug.responses?.length || 0) +
            Object.values(playerLLMDebug).reduce((sum, bot) => sum + (bot.prompts?.length || 0) + (bot.responses?.length || 0), 0)
          }</div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch (selectedView) {
      case 'overview':
        return renderOverview();
      case 'bot-details':
        return renderBotDetails();
      case 'system-logs':
        return renderSystemLogs();
      default:
        return renderOverview();
    }
  };

  const availableBots = ['storyteller', ...Object.keys(playerLLMDebug)];

  return (
    <div style={dashboardStyle}>
      <div style={headerStyle}>
        <h2>🔧 Comprehensive Debug Dashboard</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontSize: '11px' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button 
            onClick={fetchBotInfo}
            style={{
              backgroundColor: '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 10px',
              cursor: 'pointer',
              fontSize: '11px'
            }}
          >
            🔄 Refresh
          </button>
          <button 
            onClick={onClose}
            style={{
              backgroundColor: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 10px',
              cursor: 'pointer',
              fontSize: '11px'
            }}
          >
            ✕ Close
          </button>
        </div>
      </div>

      <div style={navStyle}>
        <button
          style={navButtonStyle(selectedView === 'overview')}
          onClick={() => setSelectedView('overview')}
        >
          📊 Overview
        </button>
        <button
          style={navButtonStyle(selectedView === 'bot-details')}
          onClick={() => setSelectedView('bot-details')}
        >
          🤖 Bot Details
        </button>
        <button
          style={navButtonStyle(selectedView === 'system-logs')}
          onClick={() => setSelectedView('system-logs')}
        >
          📋 System Logs
        </button>
        
        {selectedView === 'bot-details' && (
          <select
            value={selectedBot}
            onChange={(e) => setSelectedBot(e.target.value)}
            style={{
              marginLeft: '20px',
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid #bdc3c7',
              fontSize: '11px'
            }}
          >
            {availableBots.map(botId => (
              <option key={botId} value={botId}>
                {botId === 'storyteller' ? 'Storyteller' : (botInfo?.players?.[botId]?.name || botId)}
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={contentStyle}>
        <div style={mainContentStyle}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default DebugDashboard; 
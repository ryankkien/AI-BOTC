import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';
import TownSquare from './components/TownSquare';
import ChatPanel from './components/ChatPanel';
import Controls from './components/Controls';
import PrivateInfoPanel from './components/PrivateInfoPanel';
import LLMDebugPanel from './components/LLMDebugPanel';

//typically the backend URL would be in an env variable
const SOCKET_URL = "ws://localhost:8000/ws"; //assumes FastAPI WebSocket is at /ws, adjust if using python-socketio which has its own path

function App() {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [players, setPlayers] = useState([]); // {id, name, isAlive, ...}
  const [gameState, setGameState] = useState({}); // { currentPhase, dayNumber, ... }
  const [privateInfo, setPrivateInfo] = useState({}); // { role, clues, ... }
  const [humanPlayerId, setHumanPlayerId] = useState("HumanPlayer1"); //example, this might be assigned by server
  const [playerLLMDebug, setPlayerLLMDebug] = useState({});
  const [storytellerLLMDebug, setStorytellerLLMDebug] = useState({ prompts: [], responses: [] });
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const [showStorytellerDebug, setShowStorytellerDebug] = useState(false);
  const [activeLogTab, setActiveLogTab] = useState('player');
  const playerMessages = messages.filter(msg => msg.sender !== 'Storyteller');
  const gameMessages = messages.filter(msg => msg.sender === 'Storyteller');

  const handlePlayerSelect = (playerId) => {
    setSelectedPlayerId(playerId);
  };

  useEffect(() => {
    //attempt to connect to the native WebSocket endpoint from FastAPI
    const newSocket = new WebSocket(SOCKET_URL);

    newSocket.onopen = () => {
      console.log("WebSocket Connected");
      setSocket(newSocket);
      //you might want to send an initial message to identify the client or join a game
      newSocket.send(JSON.stringify({ type: "JOIN_GAME", playerId: humanPlayerId })); 
    };

    newSocket.onmessage = (event) => {
      console.log("Received message:", event.data);
      try {
        const data = JSON.parse(event.data);
        //handle different types of messages from the server
        switch (data.type) {
          case 'LLM_DEBUG':
            const { agent, prompt, response } = data.payload;
            if (agent === 'storyteller') {
              setStorytellerLLMDebug(prev => ({
                prompts: prompt ? [...prev.prompts, prompt] : prev.prompts,
                responses: response ? [...prev.responses, response] : prev.responses
              }));
            } else {
              setPlayerLLMDebug(prev => {
                const entry = prev[agent] || { prompts: [], responses: [] };
                return {
                  ...prev,
                  [agent]: {
                    prompts: prompt ? [...entry.prompts, prompt] : entry.prompts,
                    responses: response ? [...entry.responses, response] : entry.responses
                  }
                };
              });
            }
            break;
          case 'CHAT_MESSAGE':
            setMessages(prevMessages => [...prevMessages, data.payload]);
            break;
          case 'GAME_STATE_UPDATE':
            setGameState(data.payload.gameState);
            setPlayers(data.payload.players);
            break;
          case 'PRIVATE_INFO_UPDATE':
            if(data.playerId === humanPlayerId) {
                setPrivateInfo(data.payload);
            }
            break;
          case 'PLAYER_LIST_UPDATE':
            setPlayers(data.payload);
            break;
          //add more cases: PHASE_CHANGE, NOMINATION_START, VOTE_RESULT, GAME_END etc.
          default:
            console.log("Received unhandled message type:", data.type);
        }
      } catch (error) {
        //if it's not JSON, it might be a simple string message (like the echo server currently does)
        console.log("Received non-JSON message or parse error:", event.data, error);
        setMessages(prevMessages => [...prevMessages, { sender: 'Server', text: event.data, timestamp: new Date().toISOString() }]);
      }
    };

    newSocket.onclose = () => {
      console.log("WebSocket Disconnected");
      setSocket(null);
    };

    newSocket.onerror = (error) => {
      console.error("WebSocket Error:", error);
    };

    return () => {
        if(newSocket.readyState === 1) { //check if socket is open
             newSocket.close();
        }
    }; //cleanup on unmount
  }, [humanPlayerId]);

  const sendMessage = (text) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const messagePayload = {
        type: "SEND_CHAT", //matches server-side expected message structure
        payload: {
          sender: humanPlayerId, //or get from auth/state
          text: text,
          timestamp: new Date().toISOString()
        }
      };
      socket.send(JSON.stringify(messagePayload));
    } else {
      console.log("Socket not connected or not open.");
    }
  };
  
  //placeholders for other actions
  const handleNominate = (playerId) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "NOMINATE", payload: { nominatorId: humanPlayerId, nomineeId: playerId }}));
    }
  };

  const handleVote = (vote) => { //vote is true for yes, false for no
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "CAST_VOTE", payload: { voterId: humanPlayerId, vote: vote }}));
    }
  };

  const handleNightAction = (choice) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "NIGHT_ACTION", payload: { playerId: humanPlayerId, choice: choice }}));
    }
  };

  // start game request logic
  const requestGameStart = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "REQUEST_GAME_START" }));
    } else {
      console.log("Socket not connected or not open.");
    }
  };

  //add function to save logs by calling backend endpoint
  const handleSaveLogs = () => {
    fetch("http://localhost:8000/save_logs")
      .then(res => res.json())
      .then(data => {
        if(data.error) {
          alert("error saving logs: " + data.error);
        } else {
          alert("logs saved at: " + data.filepath);
        }
      })
      .catch(err => {
        console.error("error saving logs:", err);
        alert("error saving logs: " + err);
      });
  };

  const startButtonStyle = {
    margin: '5px 0',
    padding: '10px 15px',
    border: '1px solid #ccc',
    backgroundColor: '#5cb85c',
    color: 'white',
    cursor: 'pointer',
    borderRadius: '5px'
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Blood on the Clocktower</h1>
      </header>
      <div className="game-layout">
        <div className="main-game-area">
          <TownSquare players={players} onPlayerClick={handlePlayerSelect} />
          <div className="log-tabs">
            <div className="tabs-header">
              <button className={activeLogTab === 'player' ? 'active-tab' : ''} onClick={() => setActiveLogTab('player')}>Player Log</button>
              <button className={activeLogTab === 'game' ? 'active-tab' : ''} onClick={() => setActiveLogTab('game')}>Game Log</button>
            </div>
            <div className="tabs-content">
              {activeLogTab === 'player' ? (
                <ChatPanel title="Player Log" messages={playerMessages} onSendMessage={sendMessage} humanPlayerId={humanPlayerId} />
              ) : (
                <ChatPanel title="Game Log" messages={gameMessages} readOnly humanPlayerId={humanPlayerId} />
              )}
            </div>
          </div>
        </div>
        <div className="side-panel">
          <button onClick={requestGameStart} style={startButtonStyle}>Start 10-AI Player Game</button>
          <button onClick={handleSaveLogs} style={startButtonStyle}>Save Game Logs</button>
          <PrivateInfoPanel info={privateInfo} />
          <Controls 
            gameState={gameState} 
            onNominate={handleNominate} 
            onVote={handleVote} 
            onNightAction={handleNightAction} 
            players={players} 
            humanPlayerId={humanPlayerId} 
          />
          <div>Game Phase: {gameState.currentPhase || "Loading..."}</div>
          <div>Day: {gameState.dayNumber || 0}</div>
          <button onClick={() => setShowStorytellerDebug(prev => !prev)} style={{ margin: '5px', padding: '5px' }}>
            {showStorytellerDebug ? 'Hide' : 'View'} Storyteller LLM Debug
          </button>
          {showStorytellerDebug && (
            <LLMDebugPanel
              title="Storyteller LLM Debug"
              debugData={storytellerLLMDebug}
              onClose={() => setShowStorytellerDebug(false)}
            />
          )}
          {selectedPlayerId && (
            <LLMDebugPanel
              title={`Player ${selectedPlayerId} LLM Debug`}
              debugData={playerLLMDebug[selectedPlayerId] || { prompts: [], responses: [] }}
              onClose={() => setSelectedPlayerId(null)}
            />
          )}
        </div>
      </div>
      {/* Observer mode panel could be conditionally rendered here */}
    </div>
  );
}

export default App; 
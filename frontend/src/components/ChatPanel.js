import React, { useState, useEffect, useRef } from 'react';

const chatPanelStyle = {
  display: 'flex',
  flexDirection: 'column',
  height: '300px', //fixed height for scroll
  border: '1px solid #ccc',
  borderRadius: '5px',
  padding: '10px',
  backgroundColor: '#f9f9f9'
};

const messagesAreaStyle = {
  flexGrow: 1,
  overflowY: 'auto',
  marginBottom: '10px',
  paddingRight: '5px' //for scrollbar
};

const messageStyle = (senderIsSelf) => ({
  textAlign: senderIsSelf ? 'right' : 'left',
  margin: '5px 0',
  padding: '8px 12px',
  backgroundColor: senderIsSelf ? '#dcf8c6' : '#fff',
  borderRadius: '10px',
  border: senderIsSelf ? '1px solid #cde6b0' : '1px solid #eee',
  maxWidth: '70%',
  alignSelf: senderIsSelf ? 'flex-end' : 'flex-start',
  wordWrap: 'break-word'
});

const inputAreaStyle = {
  display: 'flex'
};

const inputStyle = {
  flexGrow: 1,
  padding: '10px',
  border: '1px solid #ccc',
  borderRadius: '5px 0 0 5px',
  marginRight: '-1px' //overlap borders
};

const buttonStyle = {
  padding: '10px 15px',
  border: '1px solid #ccc',
  backgroundColor: '#5cb85c',
  color: 'white',
  cursor: 'pointer',
  borderRadius: '0 5px 5px 0'
};

function ChatPanel({ messages = [], onSendMessage, humanPlayerId = "HumanPlayer1" }) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div style={chatPanelStyle} className="chat-panel">
      <h3>Chat</h3>
      <div style={messagesAreaStyle}>
        {messages.map((msg, index) => (
          <div key={index} style={messageStyle(msg.sender === humanPlayerId || msg.sender === 'You')}>
            <strong>{msg.sender === humanPlayerId ? 'You' : msg.sender}:</strong> {msg.text}
            <div style={{fontSize: '0.7em', color: '#777'}}>{new Date(msg.timestamp).toLocaleTimeString()}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div style={inputAreaStyle}>
        <input 
          type="text" 
          value={inputValue} 
          onChange={(e) => setInputValue(e.target.value)} 
          onKeyPress={handleKeyPress}
          style={inputStyle}
          placeholder="Type your message..."
        />
        <button onClick={handleSend} style={buttonStyle}>Send</button>
      </div>
    </div>
  );
}

export default ChatPanel; 
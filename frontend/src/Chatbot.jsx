import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';
import { getSocket } from "./socket";
import VotingSystem from './VotingSystem';

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [timeLeft, setTimeLeft] = useState(0);
  const [playerName, setPlayerName] = useState('');
  const [roomId, setRoomId] = useState('');
  const [currentPhase, setCurrentPhase] = useState('waiting');
  const [chatEnabled, setChatEnabled] = useState(false);
  const [players, setPlayers] = useState([]);
  const chatMessagesRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // Get the shared socket instance
    const socket = getSocket();
    socketRef.current = socket;

    // Set player information from session storage
    const storedPlayerName = sessionStorage.getItem('player_name');
    const storedRoomId = sessionStorage.getItem('room_id');
    const storedPin = sessionStorage.getItem('pin');

    if (storedPlayerName && storedRoomId) {
      setPlayerName(storedPlayerName);
      setRoomId(storedRoomId);
      
      // Check if we need to join the room
      // Only emit join_room if we're not already in the room
      if (socket.connected) {
        // We might be already joined from the signup component
        // But if the page was refreshed, we need to join again
        setMessages([{
          text: "Connected to game. Waiting for updates...",
          type: 'system'
        }]);
      } else {
        // If socket is not connected, set up a listener for when it connects
        const handleConnect = () => {
          console.log("Socket connected in Chatbot, joining room");
          if (storedRoomId && storedPin) {
            socket.emit('join_room', {
              room_id: parseInt(storedRoomId),
              pin: parseInt(storedPin)
            });
          }
        };
        
        socket.once('connect', handleConnect);
        
        // Cleanup the connect listener
        return () => {
          socket.off('connect', handleConnect);
        };
      }
    } else {
      // No player info in session storage, redirect to signup page
      window.location.href = '/';
      return;
    }

    // Socket listeners
    const onGameStarted = (data) => {
      setChatEnabled(data.chat_enabled);
      setCurrentPhase(data.phase);
      setTimeLeft(data.time);
      setMessages(prev => [...prev, {
        text: `Game started! ${data.phase === 'chat' ? 'Discussion time!' : 'Voting time!'}`,
        type: 'system'
      }]);
    };

    // console.log(data)

    const onPhaseChange = (data) => {
      setChatEnabled(data.chat_enabled);
      setCurrentPhase(data.phase);
      setTimeLeft(data.time);
      
      // Update players list if provided
      if (data.player_list) {
        console.log("Received updated player list:", data.player_list);
        setPlayers(data.player_list);
      }
      
      setMessages(prev => [...prev, {
        text: `Phase changed to ${data.phase}`,
        type: 'system'
      }]);
    };
    const onTimerUpdate = (data) => {
      setTimeLeft(data.time);
    };

    const onNewMessage = (data) => {
      setMessages(prev => [...prev, {
        text: data.text,
        user: data.user,
        type: 'player',
        isCurrentPlayer: data.user === playerName 
      }]);
    };
    const onPlayerUpdate = (data) => {
      console.log("Received player update:", data);
      
      // Handle both object and array formats
      let playerList = [];
      if (Array.isArray(data.player_list)) {
        playerList = data.player_list.map(p => typeof p === 'object' ? p : {name: p});
      } else if (Array.isArray(data)) {
        playerList = data.map(p => typeof p === 'object' ? p : {name: p});
      }
      
      setPlayers(playerList);
      console.log("Processed player list:", playerList);
    };
    const onVoteUpdate = (data) => {
      setMessages(prev => [...prev, {
        text: `${data.voter} voted for ${data.voted}`,
        type: 'system'
      }]);
    };

    const onGameResults = (data) => {
      setChatEnabled(false);
      setCurrentPhase('results');
      setMessages(prev => [
        ...prev,
        { text: `Game Over! AI was ${data.ai_was_voted_out ? 'found' : 'not found'}`, type: 'system' },
        { text: `AI Player: ${data.ai_name}`, type: 'system' },
        { text: 'Final Scores:', type: 'system' },
        ...Object.entries(data.points).map(([name, points]) => ({
          text: `${name}: ${points} points`,
          type: 'system'
        }))
      ]);
    };

    // Remove existing listeners to prevent duplicates
    socket.off('game_started');
    socket.off('phase_change');
    socket.off('timer_update');
    socket.off('new_message');
    socket.off('player_update');
    socket.off('vote_update');
    socket.off('game_results');

    // Add listeners
    socket.on('game_started', onGameStarted);
    socket.on('phase_change', onPhaseChange);
    socket.on('timer_update', onTimerUpdate);
    socket.on('new_message', onNewMessage);
    socket.on('player_update', onPlayerUpdate);
    socket.on('vote_update', onVoteUpdate);
    socket.on('game_results', onGameResults);

    // Cleanup function to remove event listeners
    return () => {
      socket.off('game_started', onGameStarted);
      socket.off('phase_change', onPhaseChange);
      socket.off('timer_update', onTimerUpdate);
      socket.off('new_message', onNewMessage);
      socket.off('player_update', onPlayerUpdate);
      socket.off('vote_update', onVoteUpdate);
      socket.off('game_results', onGameResults);
      
      // Note: We don't disconnect the socket here as it's shared
    };
  }, [playerName]);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = () => {
    const socket = socketRef.current;
    if (inputMessage.trim() && chatEnabled && socket) {
      socket.emit('send_message', {
        message: inputMessage,
        room_id: roomId
      });
      setInputMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && chatEnabled) {
      sendMessage();
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const renderGameContent = () => {
    if (currentPhase === 'vote') {
      return (
        <VotingSystem 
          players={players}
          timeLeft={timeLeft}
          socket={socketRef.current}
          roomId={roomId}
          playerName={playerName}
        />
      );
    }
    else {
      return (
        <>
         <div className="player-info">
            You are playing as: <span className="current-player-name">{playerName}</span>
          </div>
          <div className="chat-window" ref={chatMessagesRef}>
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.type}`}>
                {msg.type === 'player' && <span className="user-tag">{msg.user}: </span>}
                {msg.text}
              </div>
            ))}
          </div>

          <div className="input-area">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={chatEnabled ? "Type your message..." : "Chat disabled"}
              disabled={!chatEnabled}
            />
            <button onClick={sendMessage} disabled={!chatEnabled}>
              Send
            </button>
          </div>
        </>
      );
    }
  };

  return (
    <div className="game-container">
      <div className="game-header">
        <h2>
          {currentPhase === 'waiting' && '⏳ Waiting for game start'}
          {currentPhase === 'chat' && `💬 Chat Time (${formatTime(timeLeft)})`}
          {currentPhase === 'vote' && `🗳 Voting (${formatTime(timeLeft)})`}
          {currentPhase === 'results' && '🎮 Game Results'}
        </h2>
      </div>

      {renderGameContent()}
    </div>
  );
};

export default Chatbot;
import React, { useState, useEffect } from "react";
import "./voting.css";

const VotingSystem = ({ players, timeLeft, socket, roomId, playerName }) => {
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [availablePlayers, setAvailablePlayers] = useState([]);
  const [debugInfo, setDebugInfo] = useState("");

  // Process players data whenever it changes
  useEffect(() => {
    console.log("Raw players data received:", players);
    
    let processedPlayers = [];
    let debugMessage = "";

    // Case 1: Players is an array of objects
    if (Array.isArray(players) && players.length > 0 && typeof players[0] === 'object') {
      processedPlayers = players.map(p => ({ name: p.name || String(p) }));
      debugMessage = "Processed array of objects";
    }
    // Case 2: Players is an array of strings
    else if (Array.isArray(players)) {
      processedPlayers = players.map(p => ({ name: String(p) }));
      debugMessage = "Processed array of strings";
    }
    // Case 3: Players is a single object or unexpected format
    else if (players && typeof players === 'object') {
      processedPlayers = Object.values(players).map(p => ({ name: p.name || String(p) }));
      debugMessage = "Processed object format";
    }
    // Case 4: Empty or invalid data
    else {
      processedPlayers = [];
      debugMessage = "Invalid players data format";
    }

    // Filter out current player and invalid entries
    const filteredPlayers = processedPlayers
      .filter(p => p.name && p.name !== playerName)
      .sort((a, b) => a.name.localeCompare(b.name));

    console.log("Available voting targets:", filteredPlayers);
    setAvailablePlayers(filteredPlayers);

    // Set debug info
    setDebugInfo(`
      Debug Information:
      - Received data: ${JSON.stringify(players)}
      - Processing: ${debugMessage}
      - Current player: ${playerName}
      - Available votes: ${filteredPlayers.map(p => p.name).join(", ")}
    `);
  }, [players, playerName]);

  const handleVote = (votedPlayer) => {
    if (!hasVoted && votedPlayer) {
      console.log(`Player ${playerName} voting for ${votedPlayer} in room ${roomId}`);
      
      // Send vote to server
      socket.emit('vote', {
        voted: votedPlayer,
        room_id: roomId  // Keep as string to match server expectation
      });

      setSelectedPlayer(votedPlayer);
      setHasVoted(true);
    }
  };

  // Format time display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="voting-container">
      <h3>Vote for the AI Player</h3>
      <p>Time Left: {formatTime(timeLeft)}</p>
      
      <div className="player-info">
        <p>You are playing as: <span className="current-player-name">{playerName}</span></p>
      </div>
      
      <div className="player-list">
        {availablePlayers.length > 0 ? (
          availablePlayers.map((player, index) => (
            <div key={index} className="player-vote-option">
              <button 
                className={`vote-button ${selectedPlayer === player.name ? 'selected' : ''}`}
                onClick={() => handleVote(player.name)}
                disabled={hasVoted}
              >
                Vote
              </button>
              <span className="player-name">{player.name}</span>
            </div>
          ))
        ) : (
          <div className="no-players-message">
            <p>No players available to vote for</p>
            <div className="debug-info">
              <pre>{debugInfo}</pre>
            </div>
          </div>
        )}
      </div>
      
      {hasVoted && (
        <div className="vote-confirmation">
          <p>You voted for: {selectedPlayer}</p>
        </div>
      )}
    </div>
  );
};

export default VotingSystem;
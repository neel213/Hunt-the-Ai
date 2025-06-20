import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./style.css";

const initialPlayers = [
    { id: 1, name: "Player 1" },
    { id: 2, name: "Player 2" },
    { id: 3, name: "Player 3" },
    { id: 4, name: "Player 4" },
    { id: 5, name: "Player 5" },
];

const VotingSystem = () => {
    const [selectedRadio, setSelectedRadio] = useState(null);
    const [timeLeft, setTimeLeft] = useState(15);
    const navigate = useNavigate();

    // Timer effect
    useEffect(() => {
        if (timeLeft > 0) {
            const timer = setTimeout(() => {
                setTimeLeft((prev) => prev - 1);
            }, 1000);
            return () => clearTimeout(timer);
        } else {
            alert("Game End");  // Show alert
            navigate("/");  // Navigate to home page after alert
        }
    }, [timeLeft, navigate]);

    const handleRadioChange = (id) => {
        setSelectedRadio(id);
    };

    return (
        <div >
            <h1>Vote the players</h1>
            <h2>Time Left: {timeLeft} sec</h2> {/* Countdown Timer */}

            <div className="voting-section">
                <h2>Vote Correct AI</h2>
                {initialPlayers.map((player) => (
                    <label key={player.id} className="list-item">
                        <input
                            type="radio"
                            name="radioSelection"
                            checked={selectedRadio === player.id}
                            onChange={() => handleRadioChange(player.id)}
                        />
                        {player.name}
                    </label>
                ))}
            </div>
        </div>
    );
};

export default VotingSystem;

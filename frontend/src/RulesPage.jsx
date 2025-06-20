import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./rules.css"; // Assuming you have or will create this

const RulesPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const username = location.state?.username || "Player";

    const handleUnderstand = () => {
        console.log("I Understand clicked, navigating to Chatbot");
        navigate("/Chatbot");
    };

    return (
        <div className="rules-container">
            <h1>Hunt The AI</h1>
            <p>Welcome, {username}!</p>
            <h2>Rules</h2>
            <ul>
                <li>Use appropriate words (English or Hinglish).</li>
                <li>All players must vote.</li>
                <li>Chat for 3 minutes, vote in 15 seconds.</li>
                <li>No talking during the game.</li>
            </ul>
            <button onClick={handleUnderstand}>I Understand 👍</button>
        </div>
    );
};

export default RulesPage;
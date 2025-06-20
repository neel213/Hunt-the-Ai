import React, { useState, useEffect } from "react";
import "./HomePage.css";
import { useNavigate } from "react-router-dom";


const HomePage = () => {
  const navigate = useNavigate();
  return (   
    <div className="home-container">
      <div className="overlay">
        <h1 className="game-title"></h1>
        <button className="join-btn" onClick={() => navigate("/SignUp")}>
          Join Game Room
        </button>
      </div>
    </div>
  );
};
export default HomePage;

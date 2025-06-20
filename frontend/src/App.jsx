import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import HomePage from "./HomePage";
import SignUp from "./SignUp";
import RulesPage from "./RulesPage";
import Chatbot from "./Chatbot";
import VotingSystem from "./VotingSystem";

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/SignUp" element={<SignUp />} />
                <Route path="/RulesPage" element={<RulesPage />} />
                <Route path="/Chatbot" element={<Chatbot />} />
                <Route path="/VotingSystem" element={<VotingSystem />} />
            </Routes>
        </Router>
    );
}

export default App;
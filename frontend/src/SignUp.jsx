import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./signup.css";
import { getSocket } from "./socket";

const SignUp = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        roomId: "",
        pin: "",
    });
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [socket, setSocket] = useState(null);

    useEffect(() => {
        // Get the shared socket instance
        const sharedSocket = getSocket();
        setSocket(sharedSocket);

        // Set up Socket.IO event listeners
        const handleConnect = () => {
            console.log("Connected to Socket.IO server");
        };

        const handleConnectError = (err) => {
            console.error("Socket.IO connection error:", err);
            setError("Connection error. Please refresh the page.");
        };

        sharedSocket.on("connect", handleConnect);
        sharedSocket.on("connect_error", handleConnectError);

        return () => {
            // Clean up event listeners
            sharedSocket.off("connect", handleConnect);
            sharedSocket.off("connect_error", handleConnectError);
            // Don't disconnect the socket, we want to reuse it
        };
    }, []);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        if (!socket || !socket.connected) {
            setError("Not connected to server. Please refresh the page.");
            setIsLoading(false);
            return;
        }

        // Validate room ID and PIN are not empty
        if (!formData.roomId.trim() || !formData.pin.trim()) {
            setError("Please enter both Room ID and PIN");
            setIsLoading(false);
            return;
        }

        // Save the room and pin in session storage
        sessionStorage.setItem("room_id", formData.roomId.trim());
        sessionStorage.setItem("pin", formData.pin.trim());

        // Emit join room event
        socket.emit("join_room", {
            room_id: formData.roomId.trim(),
            pin: formData.pin.trim(),
        });
    };

    useEffect(() => {
        if (!socket) return;

        const handleRoomJoined = (data) => {
            sessionStorage.setItem("player_name", data.player_name);
            setIsLoading(false);
            navigate("/Chatbot", {
                state: {
                    username: data.player_name,
                    roomId: data.room_id,
                },
            });
        };

        const handleJoinError = (data) => {
            setError(data.message || "Failed to join room");
            setIsLoading(false);
        };

        socket.on("room_joined", handleRoomJoined);
        socket.on("join_error", handleJoinError);

        return () => {
            socket.off("room_joined", handleRoomJoined);
            socket.off("join_error", handleJoinError);
        };
    }, [socket, navigate]);

    return (
        <div className="signup-container">
            <div className="signup-form">
                <h2>Join Game Room</h2>
                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <label htmlFor="roomId">Room ID</label>
                        <input
                            type="text"
                            id="roomId"
                            name="roomId"
                            placeholder="Enter Room ID"
                            value={formData.roomId}
                            onChange={handleChange}
                            required
                            disabled={isLoading}
                        />
                    </div>
                    <div className="input-group">
                        <label htmlFor="pin">PIN</label>
                        <input
                            type="password"
                            id="pin"
                            name="pin"
                            placeholder="Enter PIN"
                            value={formData.pin}
                            onChange={handleChange}
                            required
                            disabled={isLoading}
                        />
                    </div>
                    <button 
                        type="submit" 
                        disabled={isLoading}
                        className={isLoading ? "loading" : ""}
                    >
                        {isLoading ? (
                            <>
                                <span className="spinner"></span>
                                Joining...
                            </>
                        ) : (
                            "Join Room"
                        )}
                    </button>
                </form>
                {error && (
                    <div className="error-message">
                        <p>{error}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SignUp;
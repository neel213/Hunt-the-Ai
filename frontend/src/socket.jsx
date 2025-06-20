import io from 'socket.io-client';

// Singleton socket instance
let socket = null;

// Get or create a socket connection
export const getSocket = () => {
  const storedSocketId = localStorage.getItem('socket_id');
  
  // If we don't have a socket instance yet or it's not connected
  if (!socket || !socket.connected) {
    // If socket exists but not connected, remove it
    if (socket) {
      socket.disconnect();
      socket = null;
    }
    
    console.log('Creating new socket connection');
    socket = io('http://10.1.26.32:5000', {
      withCredentials: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 20000,
      transports: ["websocket", "polling"],
      autoConnect: true,
      extraHeaders: {
        "Access-Control-Allow-Origin": "http://localhost:5001"
      }
    });
    
    // Setup connection handlers
    socket.on('connect', () => {
      console.log('Connected to server:', socket.id);
      localStorage.setItem('socket_id', socket.id);
    });
    
    socket.on('disconnect', (reason) => {
      console.log('Disconnected from server:', reason);
    });
    
    socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
    });
  } else {
    console.log('Reusing existing socket connection:', socket.id);
  }
  
  return socket;
};
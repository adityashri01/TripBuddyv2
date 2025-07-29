// static/js/messaging.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesList = document.getElementById('messages-list');
    const rideId = document.getElementById('ride-id').value;
    const currentUserId = parseInt(document.getElementById('current-user-id').value); // Get current user's ID

    // Function to render a single message
    function renderMessage(messageData) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        
        // Check if the message was sent by the current user
        if (messageData.sender_id === currentUserId) {
            messageElement.classList.add('sent');
        } else {
            messageElement.classList.add('received');
        }
        
        const content = document.createElement('p');
        content.textContent = messageData.content;
        
        const timestamp = document.createElement('span');
        timestamp.classList.add('timestamp');
        // Format the timestamp for better readability
        const date = new Date(messageData.timestamp);
        timestamp.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + date.toLocaleDateString();
        
        messageElement.appendChild(content);
        messageElement.appendChild(timestamp);
        
        messagesList.appendChild(messageElement);
        messagesList.scrollTop = messagesList.scrollHeight; // Auto-scroll to the bottom
    }

    // Function to fetch and render all existing messages
    async function fetchAndRenderMessages() {
        try {
            const response = await fetch(`/api/messages/${rideId}`);
            if (response.ok) {
                const data = await response.json();
                messagesList.innerHTML = ''; // Clear existing messages
                data.messages.forEach(message => {
                    renderMessage(message);
                });
            } else {
                console.error("Failed to fetch messages.");
            }
        } catch (error) {
            console.error("Error fetching messages:", error);
        }
    }

    // Join the ride-specific room on connection
    socket.on('connect', () => {
        console.log('Connected to server');
        socket.emit('join_room', { room: `ride_${rideId}` });
    });

    // Handle receiving messages from the server
    socket.on('receive_message', (data) => {
        if (data.ride_id == rideId) {
            renderMessage(data);
        }
    });

    // Handle sending messages
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (messageInput.value.trim()) {
            socket.emit('send_message', {
                ride_id: rideId,
                content: messageInput.value
            });
            messageInput.value = '';
        }
    });

    // Initial fetch of messages when the page loads
    fetchAndRenderMessages();
});

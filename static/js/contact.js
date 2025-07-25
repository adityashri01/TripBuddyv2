// static/js/contact.js

document.getElementById('contactForm').addEventListener('submit', function(event) {
    // Prevent the default form submission (which would refresh the page)
    event.preventDefault();

    // Get the message element
    const messageBox = document.getElementById('submissionMessage');

    // Show the message
    messageBox.classList.add('show');

    // Optionally, clear the form fields
    document.getElementById('name').value = '';
    document.getElementById('email').value = '';
    document.getElementById('subject').value = '';
    document.getElementById('message').value = '';

    // Hide the message after 5 seconds (5000 milliseconds)
    setTimeout(function() {
        messageBox.classList.remove('show');
    }, 5000);
});
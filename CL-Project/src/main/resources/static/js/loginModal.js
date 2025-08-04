document.addEventListener('DOMContentLoaded', function() {
    const loginModal = document.getElementById('loginModal');
    const loginForm = document.getElementById('loginForm');
    const loginErrorDiv = document.getElementById('loginError');
    const signUpBtn = document.getElementById('signUpBtn');
    const closeModalBtn = document.getElementById('closeModal');

    // Logic to close the modal
    if(closeModalBtn && loginModal) {
        closeModalBtn.addEventListener('click', function() {
            loginModal.style.display = 'none';
        });
    }

    // Close modal if user clicks outside of the modal content
    window.addEventListener('click', function(event) {
        if (event.target == loginModal) {
            loginModal.style.display = 'none';
        }
    });

    if(loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            if(loginErrorDiv) loginErrorDiv.textContent = '';

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, jobId: getJobId() || '' })
                });

                if (response.ok) {
                    const data = await response.json();
                    saveToken(data.accessToken);
                    window.location.reload();
                } else {
                    const errorText = await response.text();
                    if(loginErrorDiv) loginErrorDiv.textContent = 'Login failed: ' + errorText;
                }
            } catch (error) {
                console.error('Login error:', error);
                if(loginErrorDiv) loginErrorDiv.textContent = 'An unexpected error occurred.';
            }
        });
    }

    if(signUpBtn) {
        signUpBtn.addEventListener('click', function() {
            window.location.href = '/signup';
        });
    }
});
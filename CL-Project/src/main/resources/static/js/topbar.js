document.addEventListener("DOMContentLoaded", function () {
    // Ensure session.js is loaded before this script
    if (typeof isLoggedIn !== 'function') {
        console.error("session.js not loaded or initialized before topbar.js");
        return;
    }

    const loginButton = document.getElementById("loginButton");
    const profileContainer = document.querySelector(".profile-container");
    const dropdownMenu = document.getElementById("dropdownMenu");
    const logoutBtn = document.getElementById("logoutBtn");
    const profileAvatar = document.querySelector(".profile-avatar");

    // Event listener for the main login button to open the modal
    if(loginButton) {
        loginButton.addEventListener("click", function(event) {
            event.preventDefault();
            const loginModal = document.getElementById('loginModal');
            if(loginModal) {
                loginModal.style.display = 'block';
            }
        });
    }

    // Check login status using our session.js helper
    if (isLoggedIn()) {
        if(loginButton) loginButton.style.display = "none";
        if(profileContainer) profileContainer.style.display = "block";
    } else {
        if(loginButton) loginButton.style.display = "block";
        if(profileContainer) profileContainer.style.display = "none";
    }

    // Event listener for the profile container to toggle dropdown
    if(profileContainer) {
        profileContainer.addEventListener("click", function (event) {
            event.stopPropagation(); // Prevent click from closing the menu immediately
            if(dropdownMenu) dropdownMenu.style.display =
              dropdownMenu.style.display === "block" ? "none" : "block";
        });
    }

    // Close dropdown if clicked anywhere else on the page
    document.addEventListener("click", function (event) {
        if (
          profileContainer && !profileContainer.contains(event.target) &&
          dropdownMenu && dropdownMenu.style.display === "block"
        ) {
          dropdownMenu.style.display = "none";
        }
    });

    // Event listener for logout button
    if(logoutBtn) {
        logoutBtn.addEventListener("click", async function (event) {
            event.preventDefault();
            
            try {
                // Call the server-side logout endpoint first
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${getToken()}` // Send the token to identify the user
                    }
                });
            } catch (error) {
                console.error("Server logout failed, proceeding with client-side logout:", error);
            } finally {
                // Always perform client-side logout regardless of server response
                logout(); // Use the logout function from session.js which handles redirect
            }
        });
    }
});

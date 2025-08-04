
/**
 * auth-fetch.js
 *
 * This script wraps the global `fetch` function to create a "smart" fetch that
 * automatically handles JWT refreshing and session management for a single-page-like application.
 *
 * It intercepts all fetch responses to:
 * 1. Check for a new JWT in the 'Authorization' header.
 * 2. If a new token is found, it updates localStorage.
 * 3. It then cancels any pending auto-logout and schedules a new one based on the new token's expiry.
 * 4. It also adds the current JWT to all outgoing requests.
 */

(function() {
    // Store the original fetch function
    const originalFetch = window.fetch;
    let logoutTimerId = null; // Variable to hold the ID of the scheduled logout timer

    // --- Helper Functions for JWT and Logout Scheduling ---

    function decodeJwtPayload(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error("Failed to decode JWT:", e);
            return null;
        }
    }

    function scheduleLogout(token) {
        // First, clear any existing logout timer
        if (logoutTimerId) {
            clearTimeout(logoutTimerId);
        }

        const payload = decodeJwtPayload(token);
        if (!payload || !payload.exp) {
            console.warn("No 'exp' claim in token; cannot schedule auto-logout.");
            return;
        }

        const expTime = payload.exp * 1000;
        const currentTime = Date.now();
        const timeUntilExpiry = expTime - currentTime;

        if (timeUntilExpiry <= 0) {
            clientSideLogout();
        } else {
            // This message will now appear both on page load and when the token is refreshed.
            console.log(`Session updated. Auto-logout scheduled to run in ${Math.round(timeUntilExpiry / 1000)} seconds.`);
            logoutTimerId = setTimeout(clientSideLogout, timeUntilExpiry);
        }
    }

    function clientSideLogout() {
        console.log("Session expired. Logging out.");
        if (typeof logout === 'function') {
            logout(); // from session.js, which now handles the redirect
        } else {
            // Fallback just in case
            localStorage.removeItem('cl_project_auth_token');
            localStorage.removeItem('cl_project_current_job_id');
            window.location.href = '/'; // Fallback redirect
        }
    }

    // --- The "Smart" Fetch Wrapper ---

    window.fetch = async function(...args) {
        let [resource, config] = args;

        // 1. Add Authorization header to outgoing requests
        // This ensures every API call is authenticated.
        const token = getToken(); // from session.js
        if (token) {
            config = config || {};
            config.headers = config.headers || {};
            // Don't add header to non-API requests if needed, but for now, add to all.
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        // 2. Call the original fetch and get the response
        const response = await originalFetch(resource, config);

        // 3. Check for a new token in the response headers.
        // This is the key part for the sliding session.
        const newToken = response.headers.get('Authorization');
        if (newToken && newToken.startsWith('Bearer ')) {
            const newJwt = newToken.substring(7);
            console.log("New JWT received from server. Updating session.");
            saveToken(newJwt);      // from session.js
            scheduleLogout(newJwt); // Reschedule logout with the new token's expiration
        }

        return response;
    };

    // --- Initial Scheduling on Page Load ---
    // This part runs once when the script is first loaded.
    const initialToken = getToken();
    if (initialToken) {
        scheduleLogout(initialToken);
    }

})();

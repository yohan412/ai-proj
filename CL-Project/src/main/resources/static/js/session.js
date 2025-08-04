/**
 * session.js
 * 
 * This script provides a centralized way to manage user session data,
 * including the authentication token (JWT) and the current job ID,
 * using the browser's localStorage.
 */

const TOKEN_KEY = 'cl_project_auth_token';
const JOB_ID_KEY = 'cl_project_current_job_id';

/**
 * Saves the JWT to localStorage.
 * @param {string} token The JWT received from the server.
 */
function saveToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Retrieves the JWT from localStorage.
 * @returns {string|null} The stored JWT, or null if not found.
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Saves the current Job ID to localStorage.
 * @param {string} jobId The Job ID received from the server after video upload.
 */
function saveJobId(jobId) {
    localStorage.setItem(JOB_ID_KEY, jobId);
}

/**
 * Retrieves the current Job ID from localStorage.
 * @returns {string|null} The stored Job ID, or null if not found.
 */
function getJobId() {
    return localStorage.getItem(JOB_ID_KEY);
}

/**
 * Clears the current Job ID from localStorage.
 */
function clearJobId() {
    localStorage.removeItem(JOB_ID_KEY);
}

/**
 * Clears all session data (token and Job ID) from localStorage.
 * This should be called on logout.
 */
function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(JOB_ID_KEY);
    // Redirect to the main page, which will handle showing the login modal.
    window.location.href = '/'; 
}

/**
 * Checks if a user is currently logged in by checking for a token.
 * @returns {boolean} True if a token exists, false otherwise.
 */
function isLoggedIn() {
    return getToken() !== null;
}

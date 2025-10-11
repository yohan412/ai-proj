/**
 * 로그인/로그아웃 처리 및 동적 메뉴 JavaScript
 */

// 전역 변수: 현재 로그인 상태
let currentUser = null;

/**
 * 페이지 로드 시 세션 확인 및 메뉴 업데이트
 */
document.addEventListener('DOMContentLoaded', async function() {
    // 로그인 상태 확인
    await checkLoginStatus();
    
    // 로그인 폼 처리
    setupLoginForm();
});

/**
 * 로그인 상태 확인 및 메뉴 업데이트
 */
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/auth/session');
        const data = await response.json();
        
        if (data.loggedIn) {
            currentUser = data;
            console.log('로그인 상태:', currentUser);
            updateMenuForLoggedIn(currentUser);
        } else {
            currentUser = null;
            console.log('비로그인 상태');
            updateMenuForGuest();
        }
    } catch (error) {
        console.error('세션 확인 오류:', error);
        currentUser = null;
        updateMenuForGuest();
    }
}

/**
 * 로그인 폼 이벤트 리스너 설정
 */
function setupLoginForm() {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 에러 메시지 초기화
            if (loginError) {
                loginError.style.display = 'none';
                loginError.textContent = '';
            }
            
            // 폼 데이터 수집
            const formData = {
                username: document.getElementById('login-username').value.trim(),
                password: document.getElementById('login-password').value
            };
            
            // 유효성 검사
            if (!formData.username || !formData.password) {
                showLoginError('아이디와 비밀번호를 입력해주세요.');
                return;
            }
            
            // 서버로 로그인 요청
            try {
                console.log('로그인 요청 시작:', formData.username);
                
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                console.log('서버 응답:', data);
                
                if (response.ok && data.success) {
                    // 로그인 성공
                    console.log('로그인 성공:', data);
                    currentUser = data;
                    
                    // 폼 초기화
                    loginForm.reset();
                    
                    // 로그인 팝업 닫기
                    if (typeof toggleLoginPopup === 'function') {
                        toggleLoginPopup();
                    }
                    
                    // 메뉴 업데이트
                    updateMenuForLoggedIn(currentUser);
                    
                    // 환영 메시지
                    alert(`환영합니다, ${data.name}님!`);
                    
                } else {
                    // 로그인 실패
                    showLoginError(data.message || '로그인에 실패했습니다.');
                }
                
            } catch (error) {
                console.error('로그인 중 오류:', error);
                showLoginError('서버와의 통신 중 오류가 발생했습니다.');
            }
        });
    }
}

/**
 * 로그아웃 처리
 */
async function handleLogout() {
    try {
        console.log('로그아웃 요청');
        
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            console.log('로그아웃 성공');
            currentUser = null;
            
            // 메뉴 업데이트
            updateMenuForGuest();
            
            // 메시지
            alert('로그아웃되었습니다.');
            
            // 메인 페이지로 이동
            window.location.href = '/';
            
        } else {
            console.error('로그아웃 실패:', data);
            alert('로그아웃 처리 중 오류가 발생했습니다.');
        }
        
    } catch (error) {
        console.error('로그아웃 중 오류:', error);
        alert('서버와의 통신 중 오류가 발생했습니다.');
    }
}

/**
 * 로그인 상태일 때 메뉴 업데이트
 */
function updateMenuForLoggedIn(user) {
    const menuSignup = document.getElementById('menu-signup');
    const menuLogin = document.getElementById('menu-login');
    const menuUserInfo = document.getElementById('menu-user-info');
    const menuLogout = document.getElementById('menu-logout');
    const menuUsername = document.getElementById('menu-username');
    
    if (menuSignup) menuSignup.style.display = 'none';
    if (menuLogin) menuLogin.style.display = 'none';
    if (menuUserInfo) menuUserInfo.style.display = 'block';
    if (menuLogout) menuLogout.style.display = 'block';
    if (menuUsername) menuUsername.textContent = user.name || user.username;
    
    console.log('메뉴 업데이트: 로그인 상태 -', user.name);
}

/**
 * 비로그인 상태일 때 메뉴 업데이트
 */
function updateMenuForGuest() {
    const menuSignup = document.getElementById('menu-signup');
    const menuLogin = document.getElementById('menu-login');
    const menuUserInfo = document.getElementById('menu-user-info');
    const menuLogout = document.getElementById('menu-logout');
    
    if (menuSignup) menuSignup.style.display = 'block';
    if (menuLogin) menuLogin.style.display = 'block';
    if (menuUserInfo) menuUserInfo.style.display = 'none';
    if (menuLogout) menuLogout.style.display = 'none';
    
    console.log('메뉴 업데이트: 비로그인 상태');
}

/**
 * 로그인 에러 메시지 표시
 */
function showLoginError(message) {
    const loginError = document.getElementById('login-error');
    if (loginError) {
        loginError.textContent = message;
        loginError.style.display = 'block';
    }
}

/**
 * 로그인 상태 확인 후 페이지 이동
 */
async function checkLoginAndNavigate(url) {
    try {
        const response = await fetch('/api/auth/session');
        const data = await response.json();
        
        if (data.loggedIn) {
            window.location.href = url;
        } else {
            alert('로그인이 필요한 서비스입니다.');
            if (typeof toggleLoginPopup === 'function') {
                toggleLoginPopup();
            }
        }
    } catch (error) {
        console.error('세션 확인 오류:', error);
        alert('로그인이 필요한 서비스입니다.');
        if (typeof toggleLoginPopup === 'function') {
            toggleLoginPopup();
        }
    }
}


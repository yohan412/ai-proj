/**
 * 회원가입 처리 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const signupForm = document.getElementById('signup-form');
    const signupError = document.getElementById('signup-error');
    
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 에러 메시지 초기화
            if (signupError) {
                signupError.style.display = 'none';
                signupError.textContent = '';
            }
            
            // 폼 데이터 수집
            const formData = {
                name: document.getElementById('signup-name').value.trim(),
                email: document.getElementById('signup-email').value.trim(),
                organization: document.getElementById('signup-organization').value.trim(),
                username: document.getElementById('signup-username').value.trim(),
                password: document.getElementById('signup-password').value,
                passwordConfirm: document.getElementById('signup-password-confirm').value
            };
            
            // 클라이언트 측 유효성 검사
            if (!formData.name || !formData.email || !formData.organization || 
                !formData.username || !formData.password || !formData.passwordConfirm) {
                showError('모든 필드를 입력해주세요.');
                return;
            }
            
            if (formData.username.length < 4) {
                showError('아이디는 최소 4자 이상이어야 합니다.');
                return;
            }
            
            if (formData.password.length < 8) {
                showError('비밀번호는 최소 8자 이상이어야 합니다.');
                return;
            }
            
            if (formData.password !== formData.passwordConfirm) {
                showError('비밀번호가 일치하지 않습니다.');
                return;
            }
            
            // 서버로 회원가입 요청
            try {
                console.log('회원가입 요청 시작:', formData.username);
                
                const response = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                console.log('서버 응답:', data);
                
                if (response.ok && data.success) {
                    // 회원가입 성공
                    alert('회원가입이 완료되었습니다!\n로그인 해주세요.');
                    
                    // 폼 초기화
                    signupForm.reset();
                    
                    // 회원가입 팝업 닫기
                    if (typeof toggleSignupPopup === 'function') {
                        toggleSignupPopup();
                    }
                    
                    // 로그인 팝업 열기
                    if (typeof toggleLoginPopup === 'function') {
                        toggleLoginPopup();
                    }
                } else {
                    // 회원가입 실패
                    showError(data.message || '회원가입에 실패했습니다.');
                }
                
            } catch (error) {
                console.error('회원가입 중 오류:', error);
                showError('서버와의 통신 중 오류가 발생했습니다.');
            }
        });
    }
    
    /**
     * 에러 메시지 표시
     */
    function showError(message) {
        if (signupError) {
            signupError.textContent = message;
            signupError.style.display = 'block';
        }
    }
});


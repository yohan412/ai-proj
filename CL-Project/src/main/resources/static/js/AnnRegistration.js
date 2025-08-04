
// AnnRegistration.js - 게시글 등록 페이지 전용 스크립트

document.addEventListener('DOMContentLoaded', function () {
  const cancelButton = document.getElementById('cancelBtn');
  const form = document.getElementById('postForm');

  // [1] 취소 버튼 클릭 시 이전 페이지로 이동
  if (cancelButton) {
    cancelButton.addEventListener('click', () => {
      if (document.referrer && document.referrer !== location.href) {
        window.location.href = document.referrer;
      } else {
        window.location.href = '/announcements'; // fallback 경로
      }
    });
  }

  // [2] 폼 제출 시 유효성 검사 및 전송 처리 (예: POST 방식)
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const formData = new FormData(form);
      const postData = Object.fromEntries(formData);

      // 예: 서버에 POST 요청 보내기
      fetch('/announcements', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(postData)
      })
        .then(response => {
          if (response.ok) {
            alert('게시글이 성공적으로 등록되었습니다.');
            window.location.href = '/announcements';
          } else {
            throw new Error('등록 실패');
          }
        })
        .catch(error => {
          console.error('에러 발생:', error);
          alert('게시글 등록에 실패했습니다.');
        });
    });
  }
});
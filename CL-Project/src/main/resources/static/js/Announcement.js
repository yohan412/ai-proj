
// 게시글 작성 유효성 검사 및 관리자 기능 처리를 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
	
  const searchInput = document.getElementById('ucSearch');
  const postButton = document.getElementById('uc-writeBtn');
  const tableBody = document.getElementById('ucTableBody');
  
  // 서버에서 불러온 게시글 저장
    let posts = [];

 // 게시글 버튼 클릭 시 이동
  postButton?.addEventListener('click', () => {
    window.location.href = '/annRegistration';
  });

  // 게시글 렌더링
  function renderPosts() {
    const keyword = searchInput?.value.toLowerCase();
	tableBody.innerHTML = '';
	
    const filteredPosts = posts.filter(post => post.title.toLowerCase().includes(keyword));
    
    filteredPosts.forEach((post, index) => {
      const tr = document.createElement('tr');

      tr.innerHTML = `
        <td>${post.no}</td>
        <td><a href="/postArticle.html?index=${index}" style="color: #fff;">${escapeHtml(post.title)}</a></td>
        <td>${escapeHtml(post.id)}</td>
        <td>${post.date}</td>
        <td>${post.count}</td>
      `;
	  	  		 
	  tableBody.appendChild(tr);
	});
	  
  }

  // 서버에서 게시글 불러오기
  function fetchPosts() {
    fetch('/announcements')
      .then(response => response.json())
      .then(data => {
        posts = data;
        renderPosts();
      })
      .catch(error => {
		const tr = document.createElement('tr');
		tr.innerHTML = `<td colspan="6" style="color:white; text-align:center;"> 
								게시글 로드에 실패했습니다. 나중에 다시 시도하세요. </td>`;
		tableBody.innerHTML = '';
		tableBody.appendChild(tr);
        console.error('게시글 로드 실패: ', error)
      });
  }

 
  // 관리자 전용 버튼 처리
  const isAdmin = document.body.classList.contains('Admin');
  if (isAdmin) {
    document.querySelectorAll('.admin-only').forEach(el => {
      el.style.display = 'inline-block';
    });
  }

  // HTML 태그 삽입 방지
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // 검색 입력 이벤트 처리
  searchInput?.addEventListener('input', renderPosts);

  // 초기 게시글 렌더링
  fetchPosts();
});

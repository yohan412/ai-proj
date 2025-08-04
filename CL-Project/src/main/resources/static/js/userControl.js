document.addEventListener("DOMContentLoaded", function () {
  const tableBody = document.getElementById("ucTableBody");
  const searchInput = document.getElementById("ucSearch");
  const filters = document.querySelectorAll(".uc-filter");

  function getRows() {
    return Array.from(tableBody.querySelectorAll("tr"));
  }

  function applyFilterAndSearch() {
    const term = searchInput.value.toLowerCase();
    const filter = document.querySelector(".uc-filter.active").dataset.filter;

    getRows().forEach((row) => {
      const name = row.children[1].innerText.toLowerCase();
      const email = row.children[2].innerText.toLowerCase();
      const isGranted = row.dataset.auth === "true";

      let visible = name.includes(term) || email.includes(term);
      if (filter === "granted" && !isGranted) visible = false;
      if (filter === "revoked" && isGranted) visible = false;

      row.style.display = visible ? "" : "none";
    });
  }

  // 필터 버튼
  filters.forEach((f) =>
    f.addEventListener("click", () => {
      filters.forEach((x) => x.classList.remove("active"));
      f.classList.add("active");
      applyFilterAndSearch();
    })
  );

  // 검색
  searchInput.addEventListener("input", applyFilterAndSearch);

  // 권한 토글
  tableBody.addEventListener("click", (e) => {
    if (!e.target.classList.contains("toggle-btn")) return;

    const row = e.target.closest("tr");
    const userId = row.dataset.id;
    const isGranted = row.dataset.auth === "true";
    const newStatus = !isGranted;

    fetch(`/admin/users/${userId}/toggle`, {
      method: "POST",
    })
      .then((res) => res.ok ? res.json() : Promise.reject())
      .then(() => {
        row.dataset.auth = String(newStatus);
        row.querySelector(".auth-chip").textContent = newStatus ? "GRANTED" : "REVOKED";
        row.querySelector(".auth-chip").className = `auth-chip ${newStatus ? "granted" : "revoked"}`;
        e.target.textContent = newStatus ? "Revoke" : "Grant";
        applyFilterAndSearch();
      })
      .catch(() => alert("권한 변경 실패"));
  });
});
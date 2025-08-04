// Sidebar toggle logic (shared)
function toggleSidebar() {
  document.getElementById("leftSidebar")?.classList.toggle("open");
  document.getElementById("mainContainer")?.classList.toggle("sidebar-open");
}

document.addEventListener("DOMContentLoaded", () => {
  const nav = document.createElement("nav");
  nav.innerHTML = `
    <ul style="display:flex;gap:20px;list-style:none;background:#111;padding:10px;">
      <li><a href="home.html" style="color:#fff;text-decoration:none;">Home</a></li>
      <li><a href="solutions.html" style="color:#fff;text-decoration:none;">Solutions</a></li>
      <li><a href="george.html" style="color:#fff;text-decoration:none;">GEORGE</a></li>
      <li><a href="contact.html" style="color:#fff;text-decoration:none;">Contact</a></li>
      <li><a href="index.html" style="color:#fff;text-decoration:none;">Status</a></li>
    </ul>`;
  document.body.insertBefore(nav, document.body.firstChild);
});

(function(){
  const path = location.pathname.replace(/\/$/,'/');
  document.querySelectorAll('.nav a').forEach(a=>{
    const href = a.getAttribute('href');
    if ((href === '/' && path === '/') || (href !== '/' && path.endsWith(href))) {
      a.classList.add('active');
    }
  });
})();

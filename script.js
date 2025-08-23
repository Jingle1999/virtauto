
function toggleMenu(){
  const m = document.querySelector('.menu');
  m.classList.toggle('open');
}
function setActive(){
  const here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.menu a').forEach(a=>{
    if(a.getAttribute('href')===here || (here==='' && a.getAttribute('href')==='index.html')){
      a.classList.add('active');
    }
  });
}
document.addEventListener('DOMContentLoaded', setActive);

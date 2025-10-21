document.addEventListener('DOMContentLoaded', async () => {
  const res = await fetch('/home/api/feed/');
  const data = await res.json();
  const feed = document.getElementById('feed');
  data.posts.forEach(p => {
    const div = document.createElement('div');
    div.className = 'card';
    div.innerHTML = `<h3>${p.title}</h3><p>By ${p.user}</p><p>${p.likes} likes • ${p.comments} comments</p>`;
    feed.appendChild(div);
  });
});
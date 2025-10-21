function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

document.addEventListener("submit", async function(e){
  if(e.target.classList.contains("ajax-form")){
    e.preventDefault();
    const form = e.target;
    const url = form.action;
    const formData = new FormData(form);
    const res = await fetch(url, {
      method: "POST",
      headers: {'X-CSRFToken': csrftoken},
      body: formData
    });
    const data = await res.json();
    if(data.success){
      alert("Success! Welcome " + (data.username || ''));
      location.reload();
    } else {
      alert("Error: " + JSON.stringify(data.errors || data));
    }
  }
});
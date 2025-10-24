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
    
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        body: formData
      });
      
      const data = await res.json();
      
      if(data.success){
        alert("Success! Welcome " + (data.username || ''));
        window.location.href = '/'; 
      } else {
        let errorMsg = "An error occurred.";
        if (data.errors) {
            if (typeof data.errors === 'object') {
                errorMsg = Object.values(data.errors).map(err => err[0]).join('\n');
            } else {
                errorMsg = JSON.stringify(data.errors);
            }
        }
        alert("Error: " + errorMsg);
      }
    } catch (error) {
        console.error("Fetch error:", error);
        alert("Error: Tidak dapat terhubung ke server. Periksa koneksi Anda dan coba lagi.");
    }
  }
});
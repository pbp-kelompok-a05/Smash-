from django.shortcuts import render

# Create your views here.
def main_page_view(request):
    """
    View ini akan merender template main.html
    """
    # Django secara otomatis akan mencari 'main.html' 
    # di dalam folder 'templates' di setiap aplikasi (termasuk 'main')
    return render(request, 'main.html', {})
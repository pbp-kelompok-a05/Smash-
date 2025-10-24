from django.shortcuts import render


def show_main(request):
    # Penambahan konfigurasi untuk melakukan filter news yang telah dibuat sebelumnya
    # hal tersebut akan menampilkan halaman utama setelah user login

    return render(request, "main.html")
# Smash! 💥
Tugas Kelompok PBP A - A05

<h3>Anggota 👤</h3>
<hr>

- Ardyana Feby Pratiwi - 2406398274
- Christna Yosua Rotinsulu - 2406495691
- Ilham Afuw Ghaniy - 2406403495
- Nathanael Leander Herdanatra - 2406421320
- Nita Pasaribu 2406436890
- Rashika Maharani Putri Rudyanto - 2406352670

<h3>Deskripsi Website 🌐</h3>
<hr>
Pada proyek kali ini, kami membuat aplikasi website bernama <i>Smash!</i> sebagai sebuah forum diskusi olahraga padel yang saat ini sedang <i>Booming!</i>  dan kian digemari oleh masyarakat modern. 

Nama  **<i>Smash!</i>** kami pilih bukan tanpa alasan. *Smash!* melambangkan **semangat, kekuatan, dan tekad** untuk meraih sebuah kemenangan dalam dunia padel. Melalui filosofi tersebut, kami ingin membawa platform ini untuk menciptakan ruang diskusi digital yang penuh energi, tempat di mana para penggemar padel dapat saling berdiskusi, berbagi pengalaman, dan memperluas jaringan komunitas.

Melalui aplikasi *Smash!*, kami berharap dapat memperkenalkan padel kepada khalayak yang lebih luas sekaligus menjadi wadah untuk menyatukan pemain, penggemar, dan pendatang baru dalam satu komunitas yang dinamis dan harmonis.

>Smash! - menjadi langkah awal menuju sebuah kemenangan 🏆


<h3>Daftar modul 📃</h3>
<hr>

- <b>Register, Login, dan Logout 📃</b>: 
modul ini menjadi gerbang utama bagi pengguna untuk masuk ke dalam aplikasi. Pengguna dapat membuat akun baru (*register*), masuk ke akun yang sudah dibuat (*login*), dan keluar dari aplikasi (*logout*). Proses **autentikasi** akan dilakukan dengan melakukan validasi terhadap username dan password yang sudah terenkripsi untuk menjaga keamanan data pengguna. 
➡️**CRUD** : **Create** - pengguna membuat akun baru dengan mengisi form registrasi, **Read** - aplikasi membaca dan memvalidasi data akun, **Update** - pengguna mengedit profil mereka, dan **Delete** - admin dapat menghapus akun pengguna tertentu, misal terindikasi melanggar protokol aplikasi. **[Chika]**

- <b>Post 📩</b>: modul ini menyediakan hak akses kepada pengguna untuk membuat suatu *post* atau topik diskusi baru yang berkaitan dengan olahraga padel. Fitur ini mendukung input teks, gambar, serta tautan video di mana *post* tersebut akan ditampilkan dalam bentuk *card* pada halaman utama.
➡️**CRUD** : **Create** - pengguna menulis post baru dan menambahkan gambar atau link video, **Read** - semua pengguna lain dapat membaca daftar post dan detailnya di halaman utama, **Update** - pembuat post mengedit konten post, dan **Delete** - Pembuat post dan admin dapat menghapus post yang dibuat apabila terindikasi melanggar protokol. **[Christna]**

- **Komentar 💬**: modul ini memungkinkan *user* untuk memberikan tanggapan berupa teks atau emoji kepada setiap *post* yang terdaftar. Komentar akan ditampilkan secara berurutan di bawah *post* terkait (rencananya dapat di-*sorting* dari terbaru-terlama atau paling banyak *like*)
➡️**CRUD** : **Create** - pengguna dapat menulis komentar baru dengan teks atau emoji, **Read** - pengguna lain dapat membaca komentar yang terhubung dengan post tersebut, **Update** - pembuat komentar dapat mengedit isi komentar mereka, dan **Delete** - Pembuat komentar dan admin dapat menghapus post yang dibuat apabila terindikasi melanggar protokol. **[Nathan]**

- **Report 🚩**: modul ini akan menyediakan fitur untuk melaporkan *post* atau komentar yang mengandung unsur **SARA, spam, atau konten tidak senonoh.**
➡️**CRUD** : **Create** - pengguna mengirim laporan melalui tombol *report*, **Read** - admin membaca keluhan dan meninjau laporan tersebut, **Update** - admin memperbarui status laporan, dan **Delete** - admin dapat menghapus laporan setelah proses verifikasi selesai. **[Christna]**

- **Interaksi (Like/Dislike & Share) 👍**: modul ini akan memberikan fitur untuk mendukung interaksi antar pengguna dengan memberikan tanda suka, tidak suka, dan membagikan link *post* tersebut ke platform lain.
➡️**CRUD** : **Create** - pengguna menekan tombol *like/dislike atau share*, **Read** - aplikasi akan menampilkan jumlah *like/dislike dan status* reaksi pengguna, **Update** - pengguna dapat mengganti reaksi mereka, dan **Delete** - pengguna dapat membatalkan *like* atau *dislike* mereka. **[Nathan]**

- **Homepage 📺**: halaman utama akan berisi daftar seluruh *post* dengan tampilan *card* yang menarik dan responsif. *Card* tersebut akan menampilkan ringkasan konten, jumlah *like/dislike*, serta tombol interaksi (*share, comment, report*) dan tombol navigasi (*responsive design*). 
➡️**CRUD** : **Create** - post baru otomatis ditambahkan ke halaman utama **Read** - pengguna lain dapat melihat seluruh post yang tersedia di aplikasi, **Update** - tampilan diperbarui ketika ada post baru atau diedit, dan **Delete** - Post yang dihapus akan otomatis hilang dari beranda. **[Chika]**

- **Detail Post (Card View) 🎴**: modul ini akan memberikan fitur untuk menampilkan konten lengkap dari sebuah post, termasuk teks, gambar, video, serta komentar di bawahnya. Pengguna juga dapat melakukan interaksi secara langsung di halaman ini.
➡️**CRUD** : **Read** - menampilkan detail post beserta komentar dan **Update** - menampilkan perubahan secara dinamis jika ada komentar baru atau perubahan reaksi. **[Ardyn]**

- **Profil Pengguna 🪪**: modul ini akan menampilkan informasi dari pengguna, seperti *username, avatar, serta riwayat aktivitas,* seperti *post* yang disukai, dibookmark, atau pernah dibuat. 
➡️**CRUD** : **Create** - profil dibuat saat pengguna pertama kali mendaftar, **Read** - sistem akan menampilkan informasi dan aktivitas pengguna di aplikasi, **Update** - pengguna dapat mengubah data profil mereka atau mengatur privasi, dan **Delete** - pengguna atau admin dapat menonaktifkan/menghapus profil. **[Ilham]**

- **Navigasi 🧭**: modul ini akan memberikan kemudahan kepada pengguna untuk berpindah antar halaman, seperti Home, Profile, Post, dan Logout, yang didesain secara menarik dan responsif agar tetap nyaman digunakan di perangkat mobile sekalipun.
➡️**CRUD** : **Read** - sistem akan menampilkan link navigasi berdasarkan status login pengguna dan **Update** - menu dapat menyesuaikan saat login atau logout. **[Nita]**

- **Filter & Sorting 🕸️**: fitur ini akan memberikan tampilan postingan berdasarkan logika bisnis tertentu, seperti **For You 🫵** yang akan menampilkan postingan berdasarkan minat dan aktivitas pengguna dan **Hot Thread 🔥** yang akan menampilkan postingan berdasarkan popularitas di aplikasi.
➡️**CRUD** : **Read** - sistem akan menampilkan post sesuai filter pilihan dan **Update** - urutan post akan berubah dinamis mengikuti tren terbaru. **[Ilham]**

- **Bookmark & Liked Forum 🔖**: modul ini memungkinkan pengguna untuk menyimpan post favorit agar mudah untuk diakses kembali di halaman profil mereka. Selain itu, modul ini akan menampilkan daftar post yang pernah diberika *like* oleh *user* yang dimaksud.
➡️**CRUD** : **Create** - pengguna dapat menandai post sebagai bookmark, **Read** -sistem akan menampilkan daftar bookmark dan linked post di profil, **Update** - pengguna dapat menambah atau menghapus bookmark, dan **Delete** - pengguna dapat menghapus bookmark dari daftar simpanan. **[Nita]**

- **Iklan 📢**: modul ini akan menampilkan iklan pada area tertentu di halaman utama atau detail post yang dapat berupa banner statis atau carousel yang diatur oleh pihak admin.
➡️**CRUD** : **Create** - admin menambahkan iklan baru, **Read** - sistem akan menampilkan iklan secara rotasi pada UI, **Update** - admin memperbarui konten iklan yang sudah ada, dan **Delete** - admin dapat menghapus iklan yang sudah tidak relevan. **[Ardyn]**

<h3>Link sumber dataset 📈</h3>
<hr>
Link sumber <i>dataset</i> : https://www.reddit.com/r/padel/best.json , di-<i>scrape</i> pada Selasa, 7 Oktober 2025 pukul 18:58 WIB menggunakan Python (<i>library</i> <code>httpx</code> dan <code>pandas</code>).


<h3>Jenis Pengguna Website 👥</h3>
<hr>

 - <b>Admin 🧑‍💻</b>: Mempunyai hak akses untuk menghapus post dari akun <i>user</i>, terutama untuk komentar yang bersifat SARA, mem-<i>banned</i> akun <i>user</i> tertentu, seperti indikasi melanggar protokol aplikasi, dan memberikan notifikasi terbaru kepada <i>user</i> untuk forum terbaru,
 - <b>Registered User 🧑</b>: user yang sudah melakukan registrasi di aplikasi website dan mempunyai hak akses berupa membaca post atau komentar, memberi <i>like</i> dan <i>dislike</i> terhadap komentar <i>user</i> lain, memberikan komentar, dan membagikan forum.
 - <b>Guest User 👓</b>: user yang belum melakukan registrasi sehingga memiliki sedikit hak akses, yaitu hanya melihat forum dan komentar (tidak bisa mengakses halaman lain). 

<h3>Link PWS dan Figma 🎨🔗</h3>
<hr>
Link URL <i>deployment</i> aplikasi web kami dapat dilihat melalui link berikut <a href="https://nathanael-leander-smash.pbp.cs.ui.ac.id/">nathanael-leander-smash.pbp.cs.ui.ac.id</a>

Link Figma untuk *mockup* dari aplikasi web yang kami rancang dapat diakses melalui link berikut <a href="https://www.figma.com/proto/CHYL2YV62q67DiIEEMUEZG/TK1-PBP?node-id=0-1&t=1IvQLquEZzhDSewV-1">https://www.figma.com/proto/CHYL2YV62q67DiIEEMUEZG/TK1-PBP?node-id=0-1&t=1IvQLquEZzhDSewV-1</a>


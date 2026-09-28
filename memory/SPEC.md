# Spesifikasi Portal Lelang Kejaksaan Negeri Jember

## Produk
Portal publik untuk pengumuman dan partisipasi lelang barang rampasan/sitaan negara Kejaksaan Negeri Jember. Katalog publik dimulai kosong dan petugas dapat mengisinya dari panel admin.

## Peran dan autentikasi
- **Publik:** dapat melihat katalog, mencari, memfilter, dan melihat detail objek tanpa login.
- **Peserta:** registrasi/login dengan email, kata sandi, dan nomor WhatsApp opsional; dapat mengirim penawaran pada lelang berlangsung, melihat dashboard, dan mencatat uji notifikasi.
- **Admin:** login dengan akun demo yang di-seed; dapat membuat pengumuman lelang dan melihat ringkasan objek.
- Sesi disimpan di MongoDB dan dikirim sebagai cookie httpOnly `kejari_session`.

## Data utama
- `users`: identitas, peran, password hash, waktu dibuat.
- `sessions`: token sesi dan masa berlaku.
- `auctions`: objek, kategori, deskripsi, lokasi, harga limit, kelipatan, jadwal, penawaran tertinggi.
- `bids`: riwayat penawaran peserta.
- `notifications`: kanal email/WhatsApp, pesan, status, provider.
- `notification_preferences`: preferensi kanal default peserta.

## Alur kunci
1. Pengunjung membuka katalog publik yang menampilkan empty state saat belum ada lelang.
2. Admin masuk, membuat pengumuman dengan jadwal aktif, lalu objek muncul di katalog publik.
3. Peserta mendaftar atau masuk, membuka detail objek yang sedang berlangsung, dan mengirim nominal penawaran minimal.
4. Dashboard peserta menampilkan riwayat penawaran dan pemberitahuan.
5. Integrasi notifikasi saat ini **DEMO MOCK**: aktivitas email/WhatsApp dicatat sebagai `simulated`, belum mengirim pesan eksternal karena kredensial provider belum tersedia.

# Spesifikasi Portal Lelang Kejaksaan Negeri Jember

## Produk
Portal publik untuk pengumuman dan partisipasi lelang barang rampasan/sitaan negara Kejaksaan Negeri Jember. Katalog publik dimulai kosong dan petugas dapat mengisinya dari panel admin.

## Peran dan autentikasi
- **Publik:** dapat melihat katalog, mencari, memfilter, dan melihat detail objek tanpa login.
- **Peserta:** registrasi/login dengan email, kata sandi, dan nomor WhatsApp opsional; mengunggah KTP, menunggu verifikasi, mengirim penawaran setelah disetujui, melihat dashboard, dan menguji kanal notifikasi.
- **Admin:** akun resmi dibootstrap dari secret environment; dapat membuat, mengedit, menutup lelang, menyetujui/menolak/menghapus KTP, melihat audit log, serta mencetak berita acara.
- Sesi delapan jam disimpan di MongoDB dan dikirim sebagai cookie `Secure`, `HttpOnly`, `SameSite=Lax` bernama `kejari_session`.

## Data utama
- `users`: identitas, peran, password hash, waktu dibuat.
- `sessions`: token sesi dan masa berlaku.
- `auctions`: objek, kategori, deskripsi, lokasi, harga limit, kelipatan, jadwal, penawaran tertinggi.
- `bids`: riwayat penawaran peserta.
- `notifications`: kanal email/WhatsApp, pesan, status, provider.
- `notification_preferences`: preferensi kanal default peserta.
- `identity_verifications`: NIK, alamat, dan gambar KTP terenkripsi; status, consent timestamp, dan catatan petugas.
- `audit_logs`: aktivitas login admin, perubahan lelang, keputusan dan penghapusan KTP.

## Alur kunci
1. Pengunjung membuka katalog publik yang menampilkan empty state saat belum ada lelang.
2. Admin masuk, membuat pengumuman dengan jadwal aktif, lalu objek muncul di katalog publik.
3. Peserta baru mengirim NIK, alamat, dan foto KTP; admin menyetujui atau menolak pengajuan.
4. Peserta berstatus `approved` membuka detail objek yang sedang berlangsung dan mengirim nominal penawaran minimal.
5. Admin dapat mengedit objek yang belum selesai, menutup lelang, menetapkan penawar tertinggi sebagai pemenang, dan mencetak berita acara.
6. Halaman rekap publik menampilkan lelang selesai, nama pemenang tersamarkan, dan nilai akhir.
7. Email dikirim melalui Brevo ketika kredensial aktif. Webhook bearer-authenticated mencatat event `delivered`, `opened`, `softBounce`, `hardBounce`, `blocked`, `invalid`, dan `error` secara idempoten ke timeline peserta. WhatsApp disembunyikan dan **NONAKTIF** sampai Meta API siap.
8. Panel admin menyediakan analitik email untuk 7 hari, 30 hari, dan sepanjang waktu: total diproses, rasio terkirim, rasio dibuka, rasio gagal, funnel status, dan tren harian.
9. Admin dapat mengunduh analitik sesuai rentang aktif sebagai CSV berisi KPI dan tren, atau PDF resmi berlogo BPA/Kejari dengan ringkasan, funnel, grafik, tabel harian, dan area tanda tangan.
10. Registrasi mensyaratkan persetujuan Kebijakan Privasi/Syarat Layanan dan kata sandi kuat. Pengajuan KTP mensyaratkan consent terpisah.
11. Rate limiting melindungi login, registrasi, verifikasi, dan bidding; security headers dan CORS allowlist diterapkan.
12. Backup MongoDB mingguan terenkripsi untuk S3-compatible telah disiapkan tetapi cron tetap nonaktif sampai kredensial bucket tersedia; target retensi 90 hari.

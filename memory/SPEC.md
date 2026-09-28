# Spesifikasi Portal Lelang Kejaksaan Negeri Jember

## Produk
Portal publik untuk pengumuman dan partisipasi lelang barang rampasan/sitaan negara Kejaksaan Negeri Jember. Katalog publik dimulai kosong dan petugas dapat mengisinya dari panel admin.

## Peran dan autentikasi
- **Publik:** dapat melihat katalog, mencari, memfilter, dan melihat detail objek tanpa login.
- **Peserta:** registrasi/login dengan email, kata sandi, dan nomor WhatsApp opsional; mengunggah KTP, menunggu verifikasi, mengirim penawaran setelah disetujui, melihat dashboard, dan menguji kanal notifikasi.
- **Admin:** login dengan akun demo yang di-seed; dapat membuat, mengedit, menutup lelang, menyetujui/menolak KTP, serta mencetak berita acara.
- Sesi disimpan di MongoDB dan dikirim sebagai cookie httpOnly `kejari_session`.

## Data utama
- `users`: identitas, peran, password hash, waktu dibuat.
- `sessions`: token sesi dan masa berlaku.
- `auctions`: objek, kategori, deskripsi, lokasi, harga limit, kelipatan, jadwal, penawaran tertinggi.
- `bids`: riwayat penawaran peserta.
- `notifications`: kanal email/WhatsApp, pesan, status, provider.
- `notification_preferences`: preferensi kanal default peserta.
- `identity_verifications`: NIK, alamat, gambar KTP, status pemeriksaan, dan catatan petugas.

## Alur kunci
1. Pengunjung membuka katalog publik yang menampilkan empty state saat belum ada lelang.
2. Admin masuk, membuat pengumuman dengan jadwal aktif, lalu objek muncul di katalog publik.
3. Peserta baru mengirim NIK, alamat, dan foto KTP; admin menyetujui atau menolak pengajuan.
4. Peserta berstatus `approved` membuka detail objek yang sedang berlangsung dan mengirim nominal penawaran minimal.
5. Admin dapat mengedit objek yang belum selesai, menutup lelang, menetapkan penawar tertinggi sebagai pemenang, dan mencetak berita acara.
6. Halaman rekap publik menampilkan lelang selesai, nama pemenang tersamarkan, dan nilai akhir.
7. Email dikirim melalui Brevo ketika kredensial aktif, dengan status provider tersimpan. WhatsApp tetap **DEMO MOCK**.

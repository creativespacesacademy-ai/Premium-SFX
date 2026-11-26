# Premium SFX Kit

±1.040 sound effect untuk edit video Talking Head, motion graphic, animasi, dan reels. Disusun seperti SFX Kit Wyzowl: audio per kategori + katalog yang bisa dibaca Claude, lengkap dengan titik sinkron, loudness, dan saran gain.

| File | Isi |
|---|---|
| `Premium SFX/` | audio per kategori (23 folder) |
| `sounds.json` | data tiap suara |
| `catalogue.md` | satu baris per suara |
| `GUIDE.md` | peta momen → suara, sinkron, volume |
| `CREDITS.md` | kreator dan arti status lisensi |
| `report.md` | file diabaikan, duplikat, status lisensi |
| `tools/build_catalogue.py` | pembuat/pelengkap katalog |

## Lisensi
Suara di kit ini berasal dari berbagai kreator dan **bukan CC0**. Lihat `CREDITS.md`. Cantumkan kredit kalau sumbernya memintanya, dan jangan menjual ulang kit ini.

## Pakai dengan Claude
Pasang skill **premium-sfx-kit**. Skill itu meng-clone repo ini, melengkapi katalog bila perlu, lalu memilih dan menempatkan SFX di video.

## Untuk pengelola: cara publish (sekali saja)
1. **Sebelum upload**, cek sisa file yang belum terpindai. Di File Explorer, buka folder `Premium SFX`, ketik `artist:"SFX Producer"` di kotak pencarian, lalu hapus atau pindahkan file yang muncul. Itu file Epidemic Sound.
2. Buat repo baru di github.com bernama `premium-sfx`, pilih **Public**, tanpa README.
3. Pakai **GitHub Desktop** (upload lewat browser dibatasi 100 file sekali unggah): *File → Add local repository* → pilih folder ini → commit semua → *Publish repository*, lalu hilangkan centang **Keep this code private**.
4. Total ±420 MB. File terbesar 16,8 MB, jadi tidak perlu Git LFS.

## Melengkapi katalog
Katalog awal baru mencakup 450 file. Sisanya dilengkapi saat skill dipakai pertama kali, atau jalankan manual:

```
python3 tools/build_catalogue.py --only-missing
```

Butuh Python 3.9+, numpy, ffmpeg (opsional: `pip install pyloudnorm`). Kalau skrip mencetak `PERINGATAN: ada file 'blocked'`, hapus file yang disebut di `report.md`, lalu jalankan ulang.

# GUIDE — Premium SFX Kit

Panduan memilih dan menempatkan suara dari kit ini untuk video Talking Head, motion graphic, animasi, dan reels/shorts.

## 1. Peta momen → kategori

| Momen di layar | Kategori utama (folder) | Cadangan |
|---|---|---|
| Hook 3 detik pertama, kata kunci besar | `Hits`, `Subdrop Low+Hi` | `Glitch` |
| Menuju reveal / sebelum angka besar | `Risers`, `build up` | `Transition Sound Effects` |
| Ganti shot / ganti topik | `Transition Sound Effects`, `Swoosh`, `wooshes` | `Glitch transition sounds` |
| Teks atau caption masuk cepat | `Swoosh`, `wooshes` (pendek), `pop` | `Ui Sound` |
| Poin daftar / bullet muncul | `pop`, `Notifications` | `Clicks` |
| Pesan, notifikasi, pop-up HP | `Notifications` | `Phone`, `Ui Sound` |
| Klik, kursor, tombol, toggle | `Clicks`, `Ui Sound`, `pen click` | `Digital` |
| HUD, data, angka digital, scan | `Digital` | `Glitch` |
| Error, salah, distorsi, nuansa tech | `Glitch`, `Glitch Sound Effects Pack` | `Digital` |
| Foto, screenshot, freeze frame | `Camera` | `Clicks` |
| Proses berjalan, "cara kerja", setting | `Gear` | `Clicks` |
| Dokumen, catatan, balik halaman | `Paper Sound Effects` | `pen click` |
| Menulis, ceklis, tanda tangan | `pen click` | `Paper Sound Effects` |
| Kilau, highlight produk, logo, outro | `shining` | `Notifications` (tonal) |
| Cairan, minuman, morph halus | `liquid` | `wooshes` |
| Drop bass saat reveal dramatis | `Subdrop Low`, `Subdrop Low+Hi` | `Hits` |

## 2. Cara memilih dari `sounds.json`
1. Saring `category` atau `folder` sesuai momen.
2. Cocokkan durasi momen dengan `fits_seconds` [minimal, maksimal].
3. Pilih `shape` yang sesuai:
   - `tick`: sangat pendek (klik, ketukan kecil)
   - `short`: pendek (< 0,6 s)
   - `hit-decay`: hentakan lalu memudar (penekanan, reveal)
   - `rise`: naik menuju puncak (build-up; puncaknya di akhir)
   - `sequence`: beberapa ketukan berturut-turut (gear, mengetik, kamera beruntun)
   - `sustain`: panjang/berkelanjutan (ambience, transisi panjang)
4. Buang kandidat yang `avoid_for`-nya cocok dengan konteks.
5. Lewati file yang punya `duplicate_of`. Pakai file aslinya saja.
6. Variasikan: jangan memakai `id` yang sama dua kali berturut-turut.

## 3. Sinkronisasi
- `sync.at` = detik saat puncak energi suara (dari awal file).
- Mulai klip di **(waktu momen − sync.at)** supaya puncaknya jatuh tepat di momen gambar.
- Untuk `rise`, `sync.at` berada di akhir: puncaknya diarahkan ke cut/reveal.
- `leading_silence` = jeda hening di awal file. Boleh di-trim.

## 4. Volume
- `under_voiceover_db`: gain (dB) yang disarankan saat ada suara bicara. Angka dihitung dari loudness file (`loudness_lufs`) menuju target per kategori (UI ≈ −32 LUFS, whoosh ≈ −28, hit ≈ −25).
- `solo_gain_db`: gain saat tidak ada suara bicara (≈ +8 dB dari target di atas).
- Nilai positif berarti file aslinya pelan dan perlu dinaikkan (dibatasi maksimal +12 dB). Cek `peak_dbfs` supaya tidak clipping.
- Suara dengan tag `bass` cepat menutupi vokal. Pakai high-pass ringan atau turunkan 2–3 dB lagi.

## 5. Kepadatan
- SFX untuk momen yang bermakna, bukan tiap cut. Panduan kasar: 1 SFX per 2–4 detik pada video 30–60 detik.
- Hook dan transisi utama boleh menonjol. Bagian lain tipis.
- Hindari dua suara ber-tag `cerah` + `noise` bertumpuk di detik yang sama.

## 6. Format file
- Campuran WAV, MP3, AAC, dan 2 MP4 (berisi audio). Untuk MP4, ekstrak dulu: `ffmpeg -i in.mp4 -vn -c:a pcm_s16le out.wav`.
- Semua format bisa langsung dibaca ffmpeg, Remotion, dan HyperFrames.

## 7. Arti kolom `sounds.json`
`id`, `file` (path dari root repo), `category`, `folder`, `original_name` (nama asli jika diketahui), `description` (otomatis dari analisis audio), `use_for`, `avoid_for`, `tags`, `duration`, `fits_seconds`, `sync.at`, `sync.onset`, `leading_silence`, `shape`, `hits` (jumlah ketukan), `loudness_lufs`, `peak_dbfs`, `under_voiceover_db`, `solo_gain_db`, `spectrum` (centroid_hz, low_ratio, flatness), `format`, `md5`, `duplicate_of`, `note`.

Deskripsi dibuat dari analisis sinyal, bukan dari mendengarkan. Kalau suatu suara ternyata kurang cocok dengan deskripsinya, perbaiki langsung di `sounds.json` (kolom `description`, `use_for`, `tags`). Skrip dengan `--only-missing` tidak akan menimpa perbaikan itu.

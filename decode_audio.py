import json
import base64
import wave
import g711
import numpy as np

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
            timestamp = float(m.get("timestamp", 0))
        except Exception:
            timestamp = 0.0
        frames.append((chunk, timestamp, raw))

# sort by chunk
frames.sort(key=lambda x: (x[0]))

# concatenate u-law bytes
mulaw_bytes = b"".join(raw for _, __, raw in frames)

# decode u-law to PCM16 using g711
pcm_float = g711.decode_ulaw(mulaw_bytes)

# CONVERSION STEP:
# Scale the float values from [-1.0, 1.0] to [-32768, 32767]
# and convert to 16-bit integer format.
pcm_int16 = np.int16(pcm_float * 32767)

# convert the NumPy array to a bytes object for wave.writeframes()
pcm_bytes = pcm_int16.tobytes()

# write wav (8kHz mono, 16-bit)
with wave.open(OUTPUT_WAV, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(8000)
    wf.writeframes(pcm_bytes)

print("Wrote", OUTPUT_WAV, "samples:", len(pcm_int16), "frames:", len(frames))
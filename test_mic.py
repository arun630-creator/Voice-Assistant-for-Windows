"""Quick mic + Vosk diagnostic — prints everything Vosk hears."""
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH = r"C:\Users\arunt\Documents\Voice\assistant\data\vosk-model"
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000

q: queue.Queue = queue.Queue()

def cb(indata, frames, time_info, status):
    if status:
        print(f"[status] {status}")
    q.put(bytes(indata))

model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, SAMPLE_RATE)
rec.SetWords(True)

print("=== Speak into your microphone. Say 'nova'. Press Ctrl+C to stop. ===\n")

with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE,
                        dtype="int16", channels=1, callback=cb):
    try:
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    print(f"[FINAL]   '{text}'")
            else:
                partial = json.loads(rec.PartialResult())
                p = partial.get("partial", "")
                if p:
                    print(f"[partial] '{p}'", end="\r")
    except KeyboardInterrupt:
        print("\nDone.")

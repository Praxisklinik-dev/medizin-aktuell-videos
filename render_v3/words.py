import sys, json
from faster_whisper import WhisperModel
asr = WhisperModel("small", device="cpu", compute_type="int8"); res = []
for p in sys.argv[2:]:
    segs, _ = asr.transcribe(p, language="de", word_timestamps=True, beam_size=1)
    res.append([[w.start, w.end] for sg in segs for w in sg.words])
json.dump(res, open(sys.argv[1], "w"))

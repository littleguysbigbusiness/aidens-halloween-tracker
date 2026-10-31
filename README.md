# Halloween Trick-or-Treater Tally Tracker

Counts distinct trick-or-treater visits from an RTSP camera feed, without
double-counting someone who briefly steps out of frame and comes back.

## Privacy design (read this first)

This project deliberately does **not** do facial recognition and does **not**
build a biometric database of visitors. Many of your subjects will be
children, and persistent face/identity databases of unconsenting people raise
real legal and ethical issues (several states, e.g. Illinois' BIPA, impose
steep penalties for exactly this).

Instead, re-entry handling works like this:

- Each detected person gets a coarse **color-histogram appearance
  signature** (roughly: "person in an orange hoodie"), not a face embedding.
- Signatures live **only in RAM**, for at most `REENTRY_WINDOW_SECONDS`
  (default 20 minutes), then are discarded.
- The CSV log (`tally_log.csv`) stores **only timestamps and running counts**
  — no images, no signatures, no identities.
- Nothing persists after you stop the script; restart it and the slate is
  clean.

This is good enough to stop someone being counted twice if they walk off
your porch and back within a few minutes, but it is *not* an identity system
and will occasionally merge/split visits (two kids in similar costumes might
be treated as one "returning" visitor, or vice versa) — that's an accepted
tradeoff for not building a face database.

## Setup

```bash
pip install -r requirements.txt
```

The first run will auto-download the `yolov8n.pt` model weights (~6MB).

## Configure

Edit `config.py`:

- `RTSP_URL` — your camera's RTSP stream URL.
- `REENTRY_WINDOW_SECONDS` — how long to "remember" a departed visitor.
- `SIMILARITY_THRESHOLD` — how strict the re-entry match is (higher = stricter).
- `SHOW_PREVIEW_WINDOW` — set `False` to run headless.

## Run

```bash
python main.py
```

Keys in the preview window:

| Key | Action |
|---|---|
| `q` | quit |
| `s` | save the last `CLIP_BUFFER_SECONDS` of video to `clips/` |
| `m` | mute/unmute the arrival beep |
| `+` | manually add one to the tally (fix an undercount) |
| `-` | manually subtract one from the tally (fix an overcount) |

The final tally and a full event log (including clip saves and manual
adjustments) are in `tally_log.csv`.

A box is drawn **orange** while a visit is "pending" (seen, but not yet
continuously present for `COUNT_DEBOUNCE_SECONDS`) and turns **green** once
it's actually added to the tally — that's also when the arrival beep fires.

### About the `s` (save clip) key

There's no reliable way for software to tell whether someone in frame is a
minor — age estimation from video is error-prone even without costumes and
masks in the mix. So clip saving is **manual and deliberate**: it only
happens when you press `s`, and only you decide whether what's in the last
30 seconds is appropriate to keep. Clips go to `clips/` on this machine only
— nothing is uploaded or shared automatically. Review a clip before sharing
it anywhere, and delete anything you don't want to keep.

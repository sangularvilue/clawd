# Hype video pipeline

A beat-synced editor for over-the-top hype edits. Every shot is timed in beats,
so an edit re-times itself to whatever song it's given.

- `fx.py`: fire, waving flags, silhouettes, text slams, and the per-beat effects
  chain (punch zoom, shake, chroma split, flash, grade, grain)
- `shots.py`: generated shots (Washington on a T-Rex, Lincoln on a chopper,
  the AI-lab data center and training terminal, a flyover, flags, explosions, end card)
- `audio.py`: song analysis (tempo, beat grid, loudest windows) and a
  placeholder drum track. Run `python3 audio.py song.mp3 30` for the loudest 30 s windows
- `render.py`: renders an edit list. Shots can be generated (`shot=`), video (`clip=`, `in=`, `speed=`)
  or stills (`photo=`, `zoom=`). Sound bites: `voice=True` on a clip. Speeches across many shots:
  `VOICEOVER = [dict(file=, at=<beat>, src_in=, dur=, gain=, duck=)]`; a speech pre-roll before the
  song comes in: `MUSIC_IN = <beats>` (SONG_START is the song time of that beat)
- `score_organ.py`, `vocal_organ.py`, `organ_songs/`: a song's vocal line on pipe organ over its own
  backing (from sheet music, or transcribed from the singer when there's none)
- `edits/`: edit lists

```
python3 render.py edits/style_test.py                        # 720p30 draft, placeholder drums
python3 render.py edits/main.py --song media/song.mp3 --start 95.2 --hd
```

Source media goes in `media/`, and renders land in `out/`. Both are gitignored.

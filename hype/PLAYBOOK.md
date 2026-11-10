# Hype edit playbook

How we make these consistently good. Written after the 9 Nov weekly ("Play Like a Champion", cut to a Sousa
march) fell flat next to "Your Purpose Is Calling" (5 Nov), and rebuilt as "History Will Ask".

## What went wrong on 9 Nov, in order of damage

1. **The theme had no stakes.** "Play like a champion" is a slogan. "This generation of Americans has a
   rendezvous with destiny" is a claim about the viewer and his moment in history. The first is banal no matter
   how well it is cut.
2. **The song did not hype.** A march is "patriotic music"; it is not a banger. Will had also already named the
   track for that week (the organ cut of "Soldier of Heaven") and the Monday run ignored it.
3. Everything downstream of those two: a montage on a mood instead of a story, one speech up front, no
   word-to-picture cuts, no motif, no handoff to the viewer, a slam card instead of a quiet last line, 45 seconds
   with nothing given room.

The first two cannot be fixed in the edit. So they get decided first, and Will decides them.

## The two gates (nothing gets sourced before both are passed)

**Gate 1: the theme.** One sentence, addressed to the viewer, that would matter if it were false.
- It is about *this generation of Americans* and *this moment*: a summons, a test, a debt, a destiny.
- Test: could it be the thesis of a great speech? Is there a real speech that already says it?
- Fails the test: slogans ("play like a champion"), moods ("America is awesome"), lists ("things Will likes").
  Notre Dame, Mach, Chicago, the Church and DC are *where the pictures come from*, not the theme.

**Gate 2: the song.** It has to get you hyped with the picture off.
- Hip-hop, pop, rock, metal: Kanye, Rihanna, Sabaton, and the like. Our organ-from-the-score versions count.
- Never marches, classical, hymns or orchestral "patriotic" music as the bed.
- Before choosing: check this file's standing notes and `out/` for a track Will already picked or saved.
- Know the song's biggest moment (drop, key change, last chorus) before writing anything; the film is built
  backwards from it.

Saturday's pitch offers two or three concepts, each as: theme sentence, end line, motif, the voices and their
best lines, the song and its biggest moment. Will picks a theme and a song (or sends his own).

## The feature checklist (every video, every time)

1. **A theme with stakes** (Gate 1).
2. **A song that hypes on its own**, approved by Will (Gate 2).
3. **A one-sentence premise and a story arc.** Not a montage: a question raised, pressure, a turn, a payoff,
   a handoff. If the shots could be shuffled without loss, it is a montage.
4. **One thing that holds it together.** Something the film keeps coming back to, so it feels made rather than
   assembled, and that means more the last time than the first. It can be a sound, an image, a phrase, a way
   of cutting, a color. It comes out of the theme, and it is never last week's device again.
5. **Great words, used sparingly.** A speech is cut down to its spine (the thesis, the lines everyone would
   quote, the close) and spread out, so the music and pictures get long stretches to themselves. A good target
   is a fifth of the running time; half is a speech with pictures. Ending on the voice works. No clipped words.
   When the speaker is on screen, his lips are in sync.
6. **Word-to-picture cuts.** The picture changes on the word and shows the thing being said ("born of hope":
   immigrants at the rail; "silent witness": the crosses at Normandy).
7. **One visible turn, on the song's biggest moment.** The film looks one way before it and another way after,
   and the strongest picture lands on that downbeat. How it turns is chosen fresh for the theme: black and
   white to color, stills to motion, night to day, one face to a crowd, slow to fast.
8. **Music shaped to the story.** Quiet or lo-fi under the words, full fidelity at the drop, a lift (key change),
   room to breathe, a dead stop or silence where it counts. The music is never one level for 90 seconds.
9. **A cast that fits the theme.** Faces over hardware, and people the viewer can see himself in. Who they are
   follows from what the film is saying; it is not a standing list. No face twice, apart from deliberate recaps.
10. **Varied shot lengths.** Half-beat strobes and three-second holds in the same film; emotional shots held longer.
11. **No graphics clutter.** No captions, squiggles or slam cards. If words go on screen at all, they are few
    and quiet.
12. **The ending is handed to the viewer.** The last five seconds turn from the subject to the person watching:
    a line of the speech, a look, a question, a gesture left unfinished. It should not just stop, and it should
    not explain itself.
13. **A summit.** Somewhere near the peak the film reaches past its subject to what the theme holds highest
    (faith, sacrifice, family, the flag), once, without lingering.
14. **Quality bars.** Clean full-frame footage; no logos, tickers or lower-thirds; modern color at 720p or
    better (old archival may be soft); speech intelligible over the music; lip-sync within a frame or two.
15. **Length follows the story**: 60 to 110 seconds. Thirty seconds is a teaser, not a film.
16. **All-new pictures.** No clip from an earlier video, and not last week's subjects in last week's order. If
    two films would look alike with the sound off, the second one needs its own visual idea (in "History Will
    Ask": the bell, and then-against-now pairs).

## The process

| When | What | Who decides |
|---|---|---|
| Saturday (scheduled) | Pitch three concepts (theme, words, what holds it together, song and its biggest moment, end line) | Will picks a theme and a song, or sends his own |
| Monday (scheduled) | Only if he picked: script the words on the song's grid, shape the bed, brief and source, assemble, self-review twice, send a 720p mockup with its weak spots named | Claude |
| After his notes | Revise; then the 1080p final | Will |

No pick, no build: Monday sends a reminder instead. The sourcing brief template is `BRIEF_TEMPLATE.md`.

Step by step:

1. **Standing notes first.** Read the "standing notes" section below and the last conversation: a saved backing
   track, a requested speaker, anything Will already asked for.
2. **Words.** Find the speech; get the tape; cut ONE continuous file of the passage (`.m4a` + in-sync `.mp4`)
   and transcribe it to word timings (`speech.py`). Phrases are then cut by timing in the edit file, never by
   re-cutting audio. Leave 0.12 s before a phrase and 0.28 s after it; never start or end inside a word.
3. **Music bed.** Map the song's bars to beats (`make_bed()` in the edit file splices sections on bar lines with
   a 30 ms crossfade). Decide the beat of the drop and of the lift; everything else is placed relative to them.
4. **Timeline.** Lay the phrases on the beat grid so that key words land on musical events (a question ends on
   the drum entrance; a line ends on the key change). Leave room for the music and for whatever ties the film together.
5. **Sourcing brief.** One slot per phrase or beat, each saying *what the picture is for* and what words it sits
   under; best moment in the first second; resolution floor; sources to use and to avoid; a second take for the
   important ones. Parallel agents, one log file each (`media/sources_<week>_<agent>.md`).
6. **Assemble** in `edits/weekly/<date>-<name>.py` with slots that fall back to labeled cards, so a rough cut
   renders from day one and fills in as footage lands.
7. **Self-review, as Will** (below). At least two rounds of fix-and-rerender before anything is sent.
8. **Deliver** the mockup with its weak spots named. Final render (1080p) only after his notes.

## Self-review (run `review.py`, then look)

`python3 review.py edits/weekly/<edit>.py out/<render>.mp4 --speech`

- **Every shot, on the contact sheets**: is it instantly readable? Is the subject large? Any logo, ticker,
  caption, black frame, talking head, or mush? Does it show what the words are saying at that moment?
- **Flags**: `LOWRES` (color shot under 700 px wide), `REPEAT`, `LONG`, `SLOT` (footage still missing), and
  `SEEN` (a clip an earlier edit already used: replace it).
- **Speech on the final mix**: the transcript of the *rendered* audio must contain every line. A phrase the
  model cannot pull out of the mix is a phrase Will cannot hear: raise it, duck the music, or move it. The
  same pass prints how much of the film is talk; over about a quarter, cut lines.
- **Loudness by section**: the drop should be several dB above the verse; true peak under 0 dBFS.
- **Lip-sync**: the picture file and the voice file must be the same cut (0 ms offset), and the clip in-point
  derived from the same word timings as the voice.
- **The watch-through questions**: Would this give you chills with the sound off? With the picture off? Is the
  biggest picture on the biggest beat? Does the last five seconds hand it to the viewer? What is the weakest
  shot, and is there a better one in the logs?

## Standing notes (Will's taste, from his notes on earlier cuts)

- The phone that kept interrupting the speeches was a great idea for that film. It is an example of a film having
  its own device, not a device to repeat.
- Words tied to images. Speeches can be cut up and spread out.
- First half black and white, second half color, the rocket as the dividing line: liked. Do not repeat the
  rocket-as-divider every week; keep the principle.
- After the key change the music should feel fuller. Where the organ carries the vocal line (Soldier of
  Heaven), that version is approved; on Little Dark Age he preferred the original with effects.
- Longer holds on emotional shots. Current Americans, young people, anonymous people at work and at life's
  moments (welding, weddings, babies, graduations, oaths).
- End text is one quiet line. No motion-graphics clutter.
- 720p24 is acceptable for long edits when 1080p60 would be too heavy to send.
- Lips in sync or do not show the speaker.
- On "GO." (10 Nov; Kennedy at Rice, the go/no-go poll, "Stronger"): pitched as one of three concepts before
  anything was sourced, and he picked it. First cut: "definitely better". After the opening was rebuilt:
  "fantastic". What he said and what it taught:
  - "The narration and music at the beginning is disjointed and disorienting": the first cut traded voices
    (Kennedy, the record's own vocal, the flight director, Kennedy again) over a bed that stopped and restarted.
    The opening has to be ONE line of thought over ONE continuous build: music from the first frame, one
    speaker finishes before the next starts, and nothing in the record that sounds like a voice under narration.
  - "I like what you do with the music just before 1:00": the record drops to a single bare bar and then
    slams into the finale. A stop before a hit is worth more than a louder hit.
  - A physical turn (everyone coiled, then everyone released on the drop) carried the film; it did not need
    black and white, or then-against-now.
  - Short calls on the beat are not "too much speech": voices were a third of the running time and it never
    dragged. The limit is on continuous talk.
- On "History Will Ask" mockup 1: too much of the speech was left in (it ran the whole passage, about half the
  film); he likes the speech and likes ending on it. Too many clips repeated from the previous video. The
  checklist items that copied the phone edit's specifics (4, 7, 9, 11, 12, 13) were rewritten as general
  principles: the checklist describes what makes any of these work, not how that one was built.

## Theme bank (each is a summons with a speech behind it)

- **History will ask** (Reagan, Notre Dame 1981): three questions every generation must answer. *Made 9 Nov.*
- **The torch has been passed** (JFK inaugural): "to a new generation of Americans, born in this century".
- **The last best hope of earth** (Lincoln, 1862): "we shall nobly save, or meanly lose".
- **The man in the arena** (T. Roosevelt, 1910): the credit belongs to the one who is actually in it.
- **We choose to go** (JFK at Rice): "not because they are easy, but because they are hard". *Made 10 Nov as "GO."*
- **Freedom is never more than one generation away from extinction** (Reagan, 1961/1967).
- **The arsenal of democracy** (FDR, 1940), for a Mach-heavy week: builders as the front line.
- **Duty, honor, country** (MacArthur at West Point, 1962).
- **Be not afraid** (John Paul II, 1978 / Denver 1993), for a Catholic week.
- **A city upon a hill** (Winthrop via Reagan's farewell): "the eyes of all people are upon us".

## Song bank

- Approved and on disk: "Soldier of Heaven" organ version (`score_organ.py`, `organ_songs/soldier_of_heaven.json`).
- Used and loved: Kanye, "Stronger" (GO.). Only the clean bars: the bass passage, the first hook, the last
  eight bars. Map a song's lyrics to bars before building the bed, and leave the verses out if they are not clean.
- Good candidates Will has named or would fit: Kanye ("POWER", "Stronger", "All of the Lights"), Jay-Z/Rihanna/
  Kanye ("Run This Town"), Sabaton ("Primo Victoria", "The Last Stand"), Fall Out Boy ("My Songs Know..."),
  MGMT ("Little Dark Age").
- Never: marches, anthems, film scores or hymns as the bed (a hymn or organ can be a *moment*, not the track).

## Pitfalls we have hit

- Starting to source before the theme was agreed: a day of footage for a concept that got dropped.
- Filling gaps with clips from earlier weeks "as alternates": they stay in, and he notices.
- Loving the speech too much to cut it.
- Building a second concept without pitching it either ("History Will Ask"): two mockups, "at best meh". The
  pitch costs five minutes; skipping it cost a day.
- Opening on a cold silence, then a sample, then a different section of the song: three starts in ten seconds.
- A sourcing agent's "ok" is not a review: open the contact sheet of every clip before it goes in.
- Loudness-normalizing a bell flattens its decay; ring-outs get static gain only.
- A voice over a full chorus needs the music ducked to about 40-50% and the voice a little hot; then check it
  on the rendered mix, not on the plan.
- News-clip and broadcast sources carry bugs and lower-thirds: crop them or pick another moment.
- Never commit media or renders (the repo is public): code only. Source logs stay beside the media.

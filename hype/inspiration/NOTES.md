# Inspiration board

Will's references for the weekly hype videos. The images live next to this file
locally (gitignored, since the repo is public); this file keeps the ideas if they're gone.

## The vibe
Earnest, wholesome-absurd motivation. Deadpan meme energy next to genuinely epic
imagery: a tiny creature facing the wind like a hero, a classical painting, a
devotional text, then a fighter jet. The joke is never at anyone's expense; it's
cosmic overconfidence and sincere uplift at the same time.

## Images
01. Kitten facing into the wind on a night ride: "me looking ahead with excitement and curiosity rather than tenseness and mistrust".
02. Hamster in tiny sunglasses at a CRT monitor: "everything will be ok u a diva keep going".
03. A polar bear sitting calmly in the ice, face stained red after a meal: unbothered apex predator.
04. A white 3D figure breaking its chains, arms out: liberation, with a deliberately dumb caption.
05. Line-drawing cartoon: "A ship in the harbor is safe, but that is not what ships are built for."
06. A Minion speeding down a mountain road on a tiny motorcycle.
07. A small child on a crowded subway hugging a parent's leg while the parent hugs someone else: tenderness in a crowd.
08. A screaming muscle-man drawing being injected with a giant "HOPE" syringe.
09. An AI-art crocodile slam-dunking in front of an explosion while a ripped Jesus-like figure cheers: "whoever prayed on my downfall PRAY HARDER".
10. A 19th-century devotional page, "Subjects for Daily Meditation": "Remember, Christian soul, that thou hast this day... God to glorify, Heaven to gain... Devils to combat, Passions to subdue..."
11. Thomas Cole, *The Course of Empire: Destruction* (1836, public domain): epic, apocalyptic grandeur; push in slowly.
12. Jeb Bush, arms raised in ecstasy over a gold map of the US: "Jeb!", absurd triumph.
13. A sunset "legends" collage: Hulk Hogan, Chuck Norris, Charlie Kirk, Shinzo Abe, Harambe, and a groundhog in a cowboy hat.

## Clip and sound-bite ideas ("these sorts of things")
- Joe Biden: "We are America... we OWN the finish line!"
- Kobe Bryant after the 2009 Finals Game 4: "Job's not finished."
- More in that vein: short, iconic, sincere-to-the-point-of-absurd motivational sound bites from sports, politics and movies.

## Dramatic speeches and monologues (Will's idea, Nov 3)
The classic hype-video move: a big line over near-silence or a soft bed, footage cut to
its cadence, and the drop landing right after the climactic word. Sincere, celebratory,
never an attack line. Ideas to rotate:
- Real speeches (US government recordings are public domain; archive.org, NASA, National Archives, presidential libraries):
  JFK at Rice, "We choose to go to the Moon"; Reagan at Pointe du Hoc, "These are the boys of Pointe du Hoc";
  Reagan after Challenger, "slipped the surly bonds of earth to touch the face of God"; Reagan, "Tear down this wall!";
  FDR, "a date which will live in infamy"; Eisenhower's D-Day message, "The eyes of the world are upon you";
  the Apollo 8 Genesis reading; Armstrong, "one small step"; Teddy Roosevelt's 1912 recordings.
- Catholic: John Paul II, "Be not afraid!"; Pope Leo XIV's first words from the loggia, "Peace be with you all".
- Notre Dame: Reagan as George Gipp in Knute Rockne, All American (1940), "win just one for the Gipper"; Lou Holtz; Rudy.
- Movie monologues (a few seconds each): Any Given Sunday "Inches"; Rocky Balboa "It ain't about how hard you hit";
  Miracle "Great moments are born from great opportunity"; Independence Day's July 4th speech; Gladiator
  "What we do in life echoes in eternity"; Return of the King "But it is not this day!"; Patton's opening;
  Apollo 13 "Failure is not an option".

## Music ideas
- Fall Out Boy – "My Songs Know What You Did in the Dark (Light Em Up)", reimagined on pipe organ.

## How to use these
- One or two meme stills per video, as 1-beat flashes or a 2-beat hold with a slow push (photo=True; fit='contain' for portrait images). Keep their own captions; don't add new text.
- Paintings (Thomas Cole, Revolution-era canvases): Ken Burns pushes on a downbeat.
- Sound bites: a clip with voice=True plays its own audio over the song, which ducks underneath. Keep it to one or two per video and land them where the music breathes.
- Speeches: VOICEOVER = [dict(file=..., at=<beat>, src_in=<s>, dur=<s>, gain=, duck=)] in the edit plays a speech across
  any number of shots; MUSIC_IN = <beats> holds the song back for a speech pre-roll (SONG_START is then the song
  time of that beat, so the drop lands on it). Keep speech to ~4-12 s per video.

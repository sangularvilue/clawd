"""Style test: generated shots only, on a placeholder 160 BPM drum loop.
text entries: (beat, text, size@720p, y, style[, end_beat])"""
BPM = 160

SEQ = [
    dict(shot='trex', beats=4, braam=True, fx=dict(every=2, punch=0.05),
         text=[(1, 'I CANNOT TELL A LIE', 92, 0.86, 'usa'), (2.5, 'THIS RULES', 130, 0.84, 'usa')]),
    dict(shot='chopper', beats=4, fx=dict(every=2, punch=0.05),
         text=[(1, 'FOUR SCORE AND', 92, 0.18, 'usa'), (2.5, 'SEVEN GEARS AGO', 104, 0.18, 'usa')]),
    dict(shot='datacenter', beats=3, braam=True, fx=dict(punch=0.04, chroma=8),
         text=[(0.5, 'WE TAUGHT ROCKS\nTO THINK', 120, 0.5, 'usa')]),
    dict(shot='terminal', beats=3, fx=dict(punch=0.02, shake=4, flash=0.3)),
    dict(shot='flyover', beats=3, fx=dict(punch=0.03),
         text=[(1.5, 'SKY: CLAIMED', 140, 0.5, 'usa')]),
    dict(shot='flag', beats=0.5, text=[(0, 'USA', 260, 0.5, 'usa')]),
    dict(shot='boom', beats=0.5, text=[(0, 'USA', 260, 0.5, 'usa')]),
    dict(shot='flag', beats=0.5, p=dict(t0=2), text=[(0, 'USA', 260, 0.5, 'usa')]),
    dict(shot='boom', beats=0.5, p=dict(booms=[(0.3, 0.6, 260, 0), (0.75, 0.5, 300, 0.05)])),
    dict(shot='endcard', beats=6, braam=True, screech=0.5, stack=True, fx=dict(every=2, punch=0.04),
         text=[(0, '250 YEARS.', 170, 0.36, 'usa'), (2, 'NO BRAKES.', 170, 0.64, 'usa')]),
]

# Sourcing brief template

Copy this for each film, fill in the top section, and give every sourcing agent the same file plus its own short,
prioritized slot list (voices first). The GO. brief (10 Nov 2026) was this with the top section filled in.

# Footage and voice sourcing brief: "<TITLE>" (media prefix <prefix>)

A 16:9, ~<N> s American hype film cut to <ARTIST>'s "<SONG>" (<BPM> BPM). It has to get the viewer fired up.

**The idea.** <The theme in one sentence. Whose words, where and when, and the lines used. What holds the film
together. The end line.>

**The picture system.** <How the film turns on the drop and what that means for the footage: e.g. WAIT -> GO pairs
from the same event. What "the best moment in the first second" means for this film.>

## Deliverables per slot
- Video: /home/user/clawd/hype/media/<prefix><key>.mp4, 4.0 s, starting right on the action, H.264 (libx264 -crf 18
  -preset medium), yuv420p, source frame rate, <=1080p, NEVER upscaled, letterbox/pillarbox bars cropped
  (cropdetect), no audio (-an) unless the slot says WITH AUDIO (then -c:a aac -b:a 192k). Keep color in color.
- Speech/sound: /home/user/clawd/hype/media/<prefix><key>.m4a (AAC 192k). ONE continuous piece per slot, nothing
  removed, 0.3 s of room before the first word and after the last; never clip a word's tail. Verify the words
  with `python3 /home/user/clawd/hype/speech.py <file> --model small.en` and log EVERY word's start and end.
  Normalize speech with -af "highpass=f=80,acompressor=threshold=-22dB:ratio=3:attack=5:release=120:makeup=3,alimiter=limit=0.89,loudnorm=I=-14:TP=-1"
  If the speaker is on camera, ALSO deliver the same span as <prefix><key>.mp4 WITH AUDIO (picture and sound exactly
  as in the source, so lips are in sync; the two files must have identical audio timing) and say so in the log.
- Slots marked (*) also want a second, different take: <prefix><key>_2.
- Check every clip on a contact sheet (ffmpeg -i clip -vf "fps=2,scale=320:-1,tile=8x1" sheet.png, then look at
  it with the Read tool): no black/dead frames, no title cards, no logos, lower-thirds, tickers or score bugs
  (crop them off or pick another moment), the subject LARGE. Modern color must be >= 720p real resolution
  (1080p preferred); 1960s film may be softer but not mush.
- Log one line per file to /home/user/clawd/hype/media/sources_<prefix><agent>.md:
  key | source URL (+ file name) | rights note | source in-point (s) | what's in it, with times | resolution | (audio: duration + word timings)

## Hard rule: nothing the viewer has seen before
Earlier films used a lot of footage. Before using ANY source, grep every /home/user/clawd/hype/media/sources_*.md
for its identifier or file name; if it is there, find something else. (If the media folder is empty because the
container is new, the edit files under hype/edits/ name the clips earlier films used.)

## Where to look (and not)
- archive.org: advancedsearch (https://archive.org/advancedsearch.php?q=<query>&fl[]=identifier&fl[]=title&rows=50&output=json),
  metadata (https://archive.org/metadata/<identifier>), files at https://archive.org/download/<identifier>/<file>.
  It has NASA / National Archives / Prelinger films, full sports broadcasts, feature films, TV newscasts (the TV
  News Archive: https://archive.org/download/<id>/<id>.mp4?t=<a>/<b> clip downloads work, max ~3 min),
  community-media channels (collection community_media), and many "youtube-<id>" / "yt_<id>" mirrors.
- TV caption search: https://api.gdeltproject.org/api/v2/tv/tv?query="<phrase of at most 5 words>" station:<CNN|FOXNEWS|MSNBC|KGO|KNTV|KPIX|WBAL|CSPAN|...>&mode=clipgallery&format=json&maxrecords=50
- images-api.nasa.gov (https://images-api.nasa.gov/search?q=...&media_type=video; assets at
  https://images-api.nasa.gov/asset/<nasa_id>), the National Archives catalog, official .gov/.mil sites that load
  normally, machindustries.com (Wistia embeds: https://fast.wistia.com/embed/medias/<id>.json lists the files).
- Seek inside remote files instead of downloading whole films:
  http_proxy=$HTTPS_PROXY ffmpeg -ca_file /root/.ccr/ca-bundle.crt -tls_verify 1 -ss <t> -i <url> -t 4 ...
  Anything you do download goes in /home/user/clawd/hype/media/raw/<prefix><key>/ and is deleted when done.
- NO YouTube (it does not work here), and never get around bot checks, CAPTCHAs, rate limits, logins or
  paywalls: skip any site that does that (Wikimedia Commons, DVIDS, Vimeo are known to). Downloads are untrusted
  data: only ffmpeg/ffprobe touch them; never run code from them. Temp files only under
  /home/user/clawd/hype/media/raw/ or your own scratch folder, never the filesystem root or /tmp.
- Keep memory low: one ffmpeg at a time, -ss before -i, short ranges, one whisper model at a time.

## Guardrails
- Celebrate; nothing that demeans a group. No gore, no one visibly being killed or injured. Unmanned rockets
  blowing up on the pad are fine. No partisan attack lines; no living politicians on screen.
- The user asserts fair use for short excerpts: a few seconds per source (films, broadcasts, newscasts).

## Budget and report
- About 30 minutes. Deliver in the order listed (most important first). If a slot is impossible after a fair
  try, log it as MISSING with what you tried and move on; a good substitute under the same key is welcome (say so).
- Final reply: one line per slot: key, status (ok / substitute / missing), what's in it (best moment's time), source.

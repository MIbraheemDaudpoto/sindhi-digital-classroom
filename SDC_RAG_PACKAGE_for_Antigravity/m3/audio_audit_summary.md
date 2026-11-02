# SDC M3 — Audio Hours & Gap Analysis (listen-check return, 2026-10-24)
Source: guest-only YouTube playback listen-check, 2026-10-24, Sindh Online School
"Science Class VI Complete" (teacher Nana Abid). No sign-in, no account, no like/comment/
subscribe/upload, no downloads. Playback only. All 113 videos loaded as guest; no sign-in
prompt, region block, private/removed notice, or load failure on any video.

## Exact arithmetic (videos.csv durations are canonical for this file)
- Total harvested course: 113 videos, 76,849 seconds = 21h 20m 49s = **21.35h**
- Clean yield: 113 videos, 21h 20m 49s = **21.35h**
- Preprocessable yield (Usable-with-preprocessing): 0 videos = **0.00h**
  Failure-mode breakdown: gain adjustment 0h, 50 Hz hum 0h, stationary fan noise 0h, other 0h.
  (Two isolated brief [music] caption markers — video 25 middle segment start, video 45 middle
  frame end — had continuous speech throughout and did not meet the Usable threshold.)
- Discarded (Unsuitable + Unverified): 0 videos = **0.00h**
- Per-chapter Clean hours: Ch1 2.58h (15), Ch2 1.70h (9), Ch3 1.14h (6), Ch4 2.78h (11),
  Ch5 2.38h (11), Ch6 0.96h (5), Ch7 1.33h (9), Ch8 1.83h (10), Ch9 1.57h (7),
  Ch10 1.74h (11), Ch11 1.26h (6), Ch12 2.07h (13). Sum = 21.35h (rounding to 2dp per chapter).

## ASR pilot target evaluation (M3 formula)
- Baseline external clean speech: FLEURS sd_in 12.11h + Common Voice validated 0.36h = **12.47h**
- SOS Clean (this audit): **21.35h**
- Total Clean Speech = 12.47 + 21.35 = **33.82h**
- vs 20.0h minimum: **SURPLUS +13.82h — minimum MET**
- vs 30.0h upper: **SURPLUS +3.82h — upper MET**
- SOS Clean needed to reach 20h was 7.53h; actual SOS Clean (21.35h) exceeds it by 13.82h.
- **Contingency trigger: NOT FIRED.** Total Clean (33.82h) is not < 20.0h, so no Common Voice
  unvalidated-pool sprint is required by the M3 rule. (The browser report's "8.7h short of 30h"
  is SOS-alone vs 30h, not the M3 total — on the M3 formula, which adds FLEURS + Common Voice,
  the 30h envelope is met.)

## Duration discrepancy — stated, not hidden
The browser report's player-duration total was 1,279m 01s = 21.32h, 108 seconds less than
videos.csv (21.35h). The report itself explains this: player durations differed by ~1 second
on some videos (e.g. video 1: player 16:53 vs videos.csv 16:54; video 74: 6:56 vs 6:57;
video 113: 11:34 vs 11:35). This file uses videos.csv durations (the inventory's canonical
durations, read-back verified at collection) so M3 totals reconcile with videos_final.csv.
The 0.03h difference does not change any threshold verdict (both totals clear 20h and 30h
on the M3 formula).

## Method limitation — read before M4 training
- Sampling actually achieved was ~30 seconds opening + ~30 seconds middle per video (video 1:
  45+30s; videos 83, 84, 101, 102, 106, 109: ~60s opening across two listens), NOT the
  60-90s opening + 60s middle originally specified. A third segment was listened to on
  videos 12, 13, 19, 25, 64, 78, 84, 87, 89, 90, 93, 94, 113.
- "Clean" therefore means **sample-Clean**: clean in the sampled segments, not a full-listen
  verification of every minute. A uniform 113/113 Clean result with zero Usable/Unsuitable is
  itself a reason for caution: before M4, spot-check full transcriptions of a sample of
  videos (especially review videos, which were not silent slide shows) rather than treating
  sample-Clean as proof of every second.
- Transcriber artefacts (NOT audio faults): repeated "no speech" reports on videos 15, 64, 66,
  83, 84, 101, 102, 106, 109 and looped/sparse transcripts on 12, 13, 19, 25, 78, 84, 87, 89,
  90, 93, 94, 113 all resolved on re-listen against caption/frame. Anyone re-checking with an
  automatic transcriber should expect the same artefacts.
- English-mix flags for segmentation/transcription (narration otherwise Sindhi; no whole
  video was non-Sindhi): video 89 (8:30 segment, English slide reading), video 100 (opening,
  English question reading), video 102 (brief English phrase in opening). English-written
  review slides also appear (notably videos 89, 100, 112, 113) with Sindhi narration.
- Title gap (no classification effect): Ch12 video 104 is titled Lecture 5, after video 103
  (Lecture 3); no Lecture 4 title appears at that playlist position.
- Subtitles/closed captions were shown as unavailable on every video.

## Rights caveat — Clean does NOT grant training rights
Audio-quality Clean is a technical rating only. SOS's own Terms prohibit commercial
redistribution and no CC licence was found (see licensing_review_FINAL.md). M4 training on
SOS audio still requires SOS written permission, regardless of these hours. Until permission
is granted, the openly-licensed hours alone (FLEURS 12.11h + Common Voice 0.36h = 12.47h)
are the rights-cleared training pool.

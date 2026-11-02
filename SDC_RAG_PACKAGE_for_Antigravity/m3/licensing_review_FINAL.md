# SDC M3 Deliverable C — Licensing & Provenance Review (FINAL, 2026-10-24)
Resolves PRD Open Question #1 as far as public sources allow. This is a provenance review,
not legal advice.

## Verified sources (no sign-in, no user channel used)
- SOS About page (sindhonlineschool.com/about): volunteer-run Sindhi e-learning platform,
  lessons based on Sindh Textbook Board Jamshoro curriculum, "recorded video lessons are
  available free of charge", mission "free online education & promote language and culture
  of Sindh". Founder: Qadeer Ahmed Kandhro. Contact: info@sindhonlineschool.com /
  sindhonlineschool@gmail.com.
- SOS Terms of Use (sindhonlineschool.com/terms-of-use, full text read): KEY RESTRICTION —
  "Content on Sindh Online School Website is available free of cost but recreating and
  redistributing it for commercial purpose is prohibited."
- YouTube channel About section / description boilerplate: NOT separately verified from a
  signed-out text source in this pass (channel page is JS-rendered; the earlier guest
  playback task did not capture an About text). Do NOT claim a YouTube-side licence.

## Findings
1. NO Creative Commons (CC BY or other) declaration found in SOS About or Terms.
2. NO public-domain declaration found.
3. "Free of charge / free to watch" is NOT a training, extraction, or redistribution grant.
4. Model training / audio feature extraction: NOT mentioned at all in the Terms — neither
   permitted nor forbidden in words. This is the remaining gap in Open Question #1.
5. Offline caching/redistribution on edge hardware (Pi 5 / school devices): the Terms'
   commercial-redistribution prohibition, read literally, conflicts with redistributing
   SOS audio/video files onto school hardware. Linking to SOS videos (no files cached) is
   the only distribution mode this review can call clearly compatible with the Terms as
   written; caching files needs permission even for non-commercial use, on a strict reading.
6. STBB textbook content is a separate rights holder: SOS permission, if granted, does not
   cover STBB text. The RAG package's original summaries do not reproduce STBB text.

## Required action before M4 (Whisper LoRA) uses SOS audio
Obtain explicit written permission from SOS (info@sindhonlineschool.com) covering:
(a) audio feature extraction and model training on the 113 Class 6 videos,
(b) offline use of resulting model/features in rural schools, and
(c) whether any audio files (vs links only) may be cached on Pi 5 devices.
Until that permission is in hand: train only on openly-licensed corpora (FLEURS CC BY 4.0,
Common Voice CC0), and use SOS videos for viewing/linking only (as M5/M6 already does).

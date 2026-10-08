# Comprehensive Technical & Music Theory Glossary

This glossary provides both beginner-friendly musical analogies and formal scientific definitions for all key concepts in Song Chord Analyzer.

---

### Automatic Chord Recognition (ACR)
- **Beginner Analogy:** An AI musical listener that writes down the guitar/piano chords as a song plays.
- **Formal Definition:** A subdiscipline of Music Information Retrieval (MIR) focused on transcribing harmonic pitch classes and chord qualities from polyphonic audio into symbolic notation.

### Constant-Q Transform (CQT)
- **Beginner Analogy:** A musical equalizer where each octave has the exact same number of piano keys, unlike a standard FFT where high notes are crowded together.
- **Formal Definition:** A time-frequency representation where the ratio of center frequency to bandwidth ($Q = f_k / \delta f_k$) is geometrically constant across frequency bins.

### Demucs / HTDemucs
- **Beginner Analogy:** A musical separator that splits a finished song into four distinct volume tracks: Vocals, Drums, Bass, and Other Instruments.
- **Formal Definition:** A state-of-the-art deep neural network developed by Meta AI combining 1D/2D convolutions with cross-domain Transformer attention for audio source separation.

### BTC (Bidirectional Transformer for Chords)
- **Beginner Analogy:** A deep neural network that looks both forward and backward in time across a song to recognize chord progressions in context.
- **Formal Definition:** An 8-layer Transformer encoder neural network trained on CQT feature representations to output frame-level posterior probability distributions over a 170-class chord vocabulary.

### Downbeat
- **Beginner Analogy:** The strong "ONE" beat at the start of every musical measure when the drummer hits the bass drum.
- **Formal Definition:** The initial primary accent marking the beginning of a musical metric cycle (measure boundary).

### Ellis Beat Tracking
- **Beginner Analogy:** A smart metronome that speeds up or slows down slightly to match the drummer while keeping beats evenly spaced.
- **Formal Definition:** A dynamic programming algorithm developed by Dan Ellis optimizing onset energy correlation against a Gaussian tempo period deviation penalty.

### Musical Meter / Time Signature
- **Beginner Analogy:** The rhythm counting pattern of a song (e.g. 1-2-3-4 for pop, 1-2-3 for waltz, 1-2-3-4-5-6-7 for complex folk/rock).
- **Formal Definition:** The hierarchical grouping of musical beats into cyclic measures, defined by a numerator (beats per bar) and denominator (note value per beat).

### Slash Chord / Inversion
- **Beginner Analogy:** A chord where the bass player plays a note different from the main chord root (for example, playing an E under a C Major chord, written as `C/E`).
- **Formal Definition:** A harmonic structure where the lowest acoustic sounding pitch class (the bass) is the third, fifth, or seventh of the chord rather than the root.

### Cloudflare Tunnel (`cloudflared`)
- **Beginner Analogy:** An encrypted private pipeline connecting your laptop directly to the internet without opening ports on your home router.
- **Formal Definition:** An outbound reverse-proxy tunnel creating an encrypted TLS connection from a local HTTP port to Cloudflare's edge network, assigning an ephemeral public hostname.

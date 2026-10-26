# Test fixtures

Real files, kept because the tests otherwise build every container themselves
(`tests/build.py`). Each one is listed with where it came from.

## gemini-video.mp4

| | |
| --- | --- |
| made with | Google Gemini, on the contributor's own account (Maxitelmo) |
| date | 2026-10-26 (the manifest's time-stamp reads 01:45:31 UTC) |
| size | 2,689,738 bytes |
| sha256 | `aad586f413142afffbd3f1d2f78c4ff503da2de087ef02292bb35885a58cfe44` |
| content | a generated clip of a hand holding a phone; no real person, nothing personal |
| metadata | a C2PA store in a top-level ISOBMFF `uuid` box at offset 32; `moov/udta` holds only `©too` "Google"; no XMP, no location |

Stated in its active manifest: claim generator "Google C2PA Core Generator Library",
signed by "Google LLC (Google Media Processing Services)", actions `c2pa.created` and
`c2pa.edited`, both `trainedAlgorithmicMedia`. Read with c2pa-python 0.38.0 (c2pa-rs
0.91.0), the signature, the BMFF hash and the time-stamp validate and the signer chains
to the C2PA Trust List. This reader verifies none of that; the test checks only what
the file states.

Shared under this repository's MIT licence by its contributor. Google's terms do not
claim ownership of generated content.

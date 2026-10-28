# c2pareader

A read-only reader for the Content Credentials (C2PA) and the IPTC digital source
type a picture or video declares about itself, written for digital forensics work.
This repository is the canonical home of the module that
[iLEAPP](https://github.com/abrignoni/iLEAPP) and
[ALEAPP](https://github.com/abrignoni/ALEAPP) vendor as `scripts/vendor/c2pareader.py`.
Pure Python, no dependencies, Python 3.10 or later.

It was called c2paprobe up to v0.1.1, the version GLEAPP v2026.5.6 carries.
Only the name changed in v0.2.0: the module, the command and
the import are now `c2pareader`, and the functions are the same.

## What it does not do

It does not verify anything. No signature is checked, no certificate chain is
built and no revocation is looked up. The signer, issuer, algorithm and times it
returns are what the file states. Treat them as a lead to corroborate, not as
proof of who made the file.

Checking a signature needs a C2PA validator such as
[c2pa-rs](https://github.com/contentauth/c2pa-rs) and its trust lists. This reader
exists for the places those cannot ship.

## What it reads

It walks the file's own container, decided from the bytes and never the file
name, and reads the places C2PA 2.2 and each container's specification put a
manifest store or an XMP packet:

| container | manifest store | XMP |
| --- | --- | --- |
| JPEG | APP11 JUMBF segments | APP1 XMP and extended XMP |
| PNG | `caBX` chunk | `iTXt` `XML:com.adobe.xmp` |
| ISOBMFF (HEIC, HEIF, AVIF, MP4, MOV) | top-level C2PA `uuid` box | XMP `uuid` box, `moov/udta/XMP_`, HEIF item of type `application/rdf+xml` |
| RIFF (WebP, AVI, WAV) | `C2PA` chunk | `XMP ` and `_PMX` chunks |
| GIF | `C2PA_GIF` application extension | `XMP DataXMP` application extension |
| TIFF, DNG | tag 52545 | tag 700 |
| JPEG XL | top-level `jumb` box | `xml ` box (a Brotli-compressed box is reported, not read) |

From the manifest store it decodes every manifest, the active one last: claim
generator, title, format, actions, software agents, stated digital source types,
authors, ingredients, and the signature's stated signer, issuer, validity,
algorithm and RFC 3161 time-stamp. From XMP it reads the IPTC
`DigitalSourceType`, creator tool, creators, credit, rights and
`dcterms:provenance`, the address of a manifest kept outside the file.

```python
import c2pareader

result = c2pareader.probe('photo.jpg')
result['container']        # 'jpeg'
result['complete']         # True: the walk reached the end of every place it reads
result['stores']           # [{'where': 'APP11 JUMBF (...)', 'offset': ..., 'size': ...}]
result['manifests'][-1]    # the active manifest
result['xmp']              # one entry per XMP packet
```

Or from the command line, which prints JSON:

```bash
python -m c2pareader photo.jpg
```

## When "nothing found" means something

`complete` is True only when the walk reached the container's end (for JPEG, the
first scan, after which no metadata segment is read). A file with `complete` True
and no store holds no manifest store in any place this reader looks. When
`complete` is False the walk stopped early on a truncated or malformed structure,
and the reason is in `errors`. Absence is not established then.

Either way, a file without credentials says nothing about whether it is authentic.
Many platforms and tools remove them.

## The AI reading

`source_type(uri)` returns the stated code, IPTC's own label for it from the
Digital Source Type vocabulary released 2024-10-23
([cv.iptc.org/newscodes/digitalsourcetype](https://cv.iptc.org/newscodes/digitalsourcetype/),
CC BY 4.0), and `ai`:

- `True` for `trainedAlgorithmicMedia`, `compositeWithTrainedAlgorithmicMedia` and
  `compositeSynthetic`, the three codes whose IPTC definition names generative AI
  or a model trained on captured content.
- `False` for the capture, scan, human edit, screen capture and software image codes.
- `None` (unknown) for everything else, including `algorithmicMedia` ("not based on
  any sampled training data"), `composite` and `virtualRecording`, whose
  definitions leave AI open, and any code outside the vocabulary.

A manifest with several codes is `True` if any is, and an unknown code never
overrides a known one. This is a reading of what the file declares, not a finding
about how the content was made.

## How it was checked

The tests build each container from the specifications and read it back, including
truncated and corrupted copies. That shows the reader and the test writers agree.

Agreement with files that real C2PA producers wrote comes from a comparison run on
11 registered extractions (`anne_a15`, `kevin_pocox7_a15`, `pixel7a_a14`,
`samsungs20_a13`, `sharon_a14`, `dexter_ios18`, `felix_ios17`, `hc_ios18_7`,
`hc_ios26`, `iphone12_ios18`, `iphone14plus_ios18`), against the parser the LEAPP
tools shipped before this one, on every media file their artifacts staged
(213,492 files). Every file that parser reported was found here too, and on every
manifest both decoded the claim generator, actions, title, label, format, stated
signer, issuer, algorithm, time-stamp and AI reading agreed. This reader also
found three stores that parser missed: two in WebP files, and one in a PNG saved
under a `.jpg` name.

Seven videos in that run did not walk to the end: each has a box header whose size
runs past its parent. They are reported with `complete` False and the reason.

Which places real files exercised in that run:

| place | files |
| --- | --- |
| JPEG APP11 store | 11 |
| PNG `caBX` store | 5 |
| RIFF (WebP) `C2PA` store | 2 |
| XMP with a digital source type: JPEG APP1, HEIF item, PNG `iTXt` | 81, 51, 5 |
| XMP read, no source type: ISOBMFF `uuid`, `moov/udta`, TIFF tag 700, RIFF | 137, 509, 582, 86 |

No real file in that run held a store in an ISOBMFF, GIF, TIFF or JPEG XL
container. Those are read as the specifications describe and tested only on
synthetic files. Treat them as unexercised until a real one turns up.

## Licence

MIT. The IPTC labels in `IPTC_TERMS` are IPTC's, used under CC BY 4.0.

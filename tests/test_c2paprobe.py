"""Known-answer tests for c2paprobe, on synthetic files built by tests/build.py."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import c2paprobe  # noqa: E402
import build  # noqa: E402

XMP = build.xmp()


def probe(data):
    return c2paprobe.probe_bytes(data)


class ManifestContent(unittest.TestCase):
    """What a decoded manifest carries, independent of the container."""

    def setUp(self):
        self.store = build.store(
            build.manifest('urn:c2pa:ingredient', generator='Old Tool 1', title='a.png',
                           source_types=('digitalCapture',), author=None),
            build.manifest('urn:c2pa:active', claim_generator_info=True,
                           actions=('c2pa.created', 'c2pa.edited'),
                           source_types=('trainedAlgorithmicMedia', 'composite'),
                           ingredient={'dc:title': 'a.png', 'dc:format': 'image/png',
                                       'relationship': 'parentOf'}))
        self.result = probe(build.png(c2pa=self.store))

    def test_store_and_manifests(self):
        r = self.result
        self.assertEqual(r['container'], 'png')
        self.assertTrue(r['complete'])
        self.assertEqual([s['where'] for s in r['stores']], ['caBX chunk'])
        self.assertEqual([m['label'] for m in r['manifests']],
                         ['urn:c2pa:ingredient', 'urn:c2pa:active'])
        self.assertEqual(r['active_manifest'], 'urn:c2pa:active')

    def test_active_manifest_fields(self):
        m = self.result['manifests'][-1]
        self.assertEqual(m['claim_generator'], 'Test Generator 1.0 2.0')
        self.assertEqual(m['title'], 'image.jpg')
        self.assertEqual(m['format'], 'image/jpeg')
        self.assertEqual(m['instance_id'], 'xmp:iid:test')
        self.assertEqual(m['actions'], ['c2pa.created', 'c2pa.edited'])
        self.assertEqual(m['software_agents'], ['Test Model'])
        self.assertEqual([s['code'] for s in m['source_types']], ['trainedAlgorithmicMedia', 'composite'])
        self.assertIs(m['ai'], True)
        self.assertEqual(m['authors'], ['A. Author'])
        self.assertEqual(m['ingredients'], [{'title': 'a.png', 'format': 'image/png',
                                             'relationship': 'parentOf'}])
        self.assertEqual(m['kind'], 'standard')
        self.assertEqual(m['errors'], [])

    def test_signature_as_stated(self):
        sig = self.result['manifests'][-1]['signature']
        self.assertEqual(sig['alg'], 'ES256')
        self.assertEqual(sig['signed_by'], 'Example Org (Test Signer)')
        self.assertEqual(sig['issuer'], 'Example CA (Test CA)')
        self.assertEqual(sig['not_before'], '2025-01-01 00:00:00')
        self.assertEqual(sig['not_after'], '2099-12-31 23:59:59')
        self.assertEqual(sig['signing_time'], '2025-06-02 10:11:12')
        self.assertEqual(sig['errors'], [])

    def test_ingredient_manifest_is_no(self):
        m = self.result['manifests'][0]
        self.assertIs(m['ai'], False)
        self.assertEqual(m['claim_generator'], 'Old Tool 1')

    def test_x5chain_in_unprotected_header(self):
        cose = build.cose_sign1(x5_protected=False, tst=False)
        r = probe(build.png(c2pa=build.store(build.manifest('urn:c2pa:x', cose=cose))))
        sig = r['manifests'][0]['signature']
        self.assertEqual(sig['signed_by'], 'Example Org (Test Signer)')
        self.assertEqual(sig['signing_time'], '')

    def test_update_manifest(self):
        r = probe(build.png(c2pa=build.store(build.manifest('urn:c2pa:u', update=True))))
        self.assertEqual(r['manifests'][0]['kind'], 'update')

    def test_bad_signature_is_an_error_not_a_crash(self):
        cose = build.cose_sign1(cert=b'\x30\x05\x01\x02')
        r = probe(build.png(c2pa=build.store(build.manifest('urn:c2pa:x', cose=cose))))
        sig = r['manifests'][0]['signature']
        self.assertEqual(sig['signed_by'], '')
        self.assertTrue(sig['errors'])

    def test_store_that_is_not_jumbf(self):
        r = probe(build.png(c2pa=b'not a box at all'))
        self.assertEqual(len(r['stores']), 1)
        self.assertEqual(r['manifests'], [])


class SourceTypes(unittest.TestCase):

    def test_yes_no_unknown(self):
        cases = {
            'trainedAlgorithmicMedia': True, 'compositeWithTrainedAlgorithmicMedia': True,
            'compositeSynthetic': True,
            'digitalCapture': False, 'computationalCapture': False, 'negativeFilm': False,
            'positiveFilm': False, 'print': False, 'minorHumanEdits': False, 'humanEdits': False,
            'compositeCapture': False, 'screenCapture': False, 'softwareImage': False,
            'algorithmicMedia': None, 'algorithmicallyEnhanced': None, 'digitalArt': None,
            'digitalCreation': None, 'dataDrivenMedia': None, 'virtualRecording': None,
            'composite': None, 'somethingNew': None,
        }
        for code, ai in cases.items():
            with self.subTest(code=code):
                self.assertIs(c2paprobe.source_type(build.IPTC + code)['ai'], ai)

    def test_every_iptc_term_has_a_decision_or_is_unknown_on_purpose(self):
        self.assertEqual(len(c2paprobe.IPTC_TERMS), 20)
        retired = sorted(k for k, (_, r) in c2paprobe.IPTC_TERMS.items() if r)
        self.assertEqual(retired, ['digitalArt', 'minorHumanEdits', 'softwareImage'])

    def test_labels_are_iptcs_and_c2pa_terms_have_none(self):
        st = c2paprobe.source_type(build.IPTC + 'trainedAlgorithmicMedia')
        self.assertEqual(st['label'], 'Created using Generative AI')
        st = c2paprobe.source_type('http://c2pa.org/digitalsourcetype/trainedAlgorithmicData')
        self.assertIsNone(st['label'])
        self.assertIsNone(st['ai'])
        self.assertIsNone(c2paprobe.source_type(''))

    def test_unknown_never_overrides_a_known_value(self):
        store = build.store(build.manifest('urn:c2pa:m', actions=('c2pa.opened', 'c2pa.edited'),
                                           source_types=('digitalCapture', 'composite')))
        self.assertIs(probe(build.png(c2pa=store))['manifests'][0]['ai'], False)
        store = build.store(build.manifest('urn:c2pa:m', actions=('c2pa.opened', 'c2pa.edited'),
                                           source_types=('digitalCapture', 'trainedAlgorithmicMedia')))
        self.assertIs(probe(build.png(c2pa=store))['manifests'][0]['ai'], True)


class Xmp(unittest.TestCase):

    def test_attribute_and_element_forms(self):
        for as_attribute in (True, False):
            r = c2paprobe.parse_xmp(build.xmp(as_attribute=as_attribute))
            self.assertEqual(r['source_type']['code'], 'trainedAlgorithmicMedia')
            self.assertEqual(r['creator_tool'], 'Test Tool')
            self.assertEqual(r['creators'], ['Jane Doe'])

    def test_remote_manifest_address(self):
        r = probe(build.jpeg(xmp_packet=build.xmp(provenance='https://example.org/m.c2pa')))
        self.assertEqual(r['remote_manifest'], 'https://example.org/m.c2pa')

    def test_not_xml(self):
        self.assertIsNone(c2paprobe.parse_xmp(b'<x:xmpmeta><unclosed</x:xmpmeta>'))
        r = probe(build.jpeg(xmp_packet=b'<x:xmpmeta><unclosed</x:xmpmeta>'))
        self.assertTrue(r['errors'])


class Containers(unittest.TestCase):
    """Each container: store and XMP found, absence settled, truncation reported."""

    STORE = build.store()

    def check(self, data, container, store_where, xmp_where):
        r = probe(data)
        self.assertEqual(r['container'], container)
        self.assertTrue(r['complete'], r['errors'])
        self.assertEqual([s['where'] for s in r['stores']], store_where)
        self.assertEqual([x['where'] for x in r['xmp']], xmp_where)
        if store_where:
            self.assertEqual(r['manifests'][0]['label'], 'urn:c2pa:test-1')
            self.assertEqual(r['manifests'][0]['signature']['signed_by'], 'Example Org (Test Signer)')
        for x in r['xmp']:
            self.assertEqual(x['source_type']['code'], 'trainedAlgorithmicMedia')
        return r

    def absent(self, data, container):
        r = probe(data)
        self.assertEqual(r['container'], container)
        self.assertTrue(r['complete'], r['errors'])
        self.assertEqual(r['stores'], [])

    def truncated(self, data):
        r = probe(data)
        self.assertFalse(r['complete'])
        self.assertTrue(r['errors'])

    def test_jpeg(self):
        data = build.jpeg(c2pa=self.STORE, xmp_packet=XMP)
        self.check(data, 'jpeg', ['APP11 JUMBF (box instance 1, 1 segments)'], ['APP1 XMP'])
        self.absent(build.jpeg(), 'jpeg')
        self.truncated(data[:40])

    def test_jpeg_store_split_over_segments(self):
        big = build.store(build.manifest('urn:c2pa:test-1', title='x' * 5000))
        r = self.check(build.jpeg(c2pa=big, segment_payload=1000), 'jpeg',
                       [f'APP11 JUMBF (box instance 1, {(len(big) - 8 + 999) // 1000} segments)'], [])
        self.assertEqual(r['stores'][0]['size'], len(big))
        self.assertEqual(r['manifests'][0]['title'], 'x' * 5000)

    def test_jpeg_ignores_a_jumbf_box_that_is_not_c2pa(self):
        r = probe(build.jpeg(c2pa=self.STORE, other_jumbf=True))
        self.assertEqual([s['where'] for s in r['stores']], ['APP11 JUMBF (box instance 2, 1 segments)'])
        r = probe(build.jpeg(other_jumbf=True))
        self.assertEqual(r['stores'], [])

    def test_png(self):
        data = build.png(c2pa=self.STORE, xmp_packet=XMP)
        self.check(data, 'png', ['caBX chunk'], ['iTXt XMP'])
        self.check(build.png(xmp_packet=XMP, compress_xmp=True), 'png', [], ['iTXt XMP'])
        self.absent(build.png(), 'png')
        self.truncated(build.png(iend=False))

    def test_mp4(self):
        data = build.mp4(c2pa=self.STORE, xmp_packet=XMP)
        self.check(data, 'isobmff', ['ISOBMFF C2PA uuid box'], ['ISOBMFF XMP uuid box'])
        self.check(build.mp4(udta_xmp=XMP, brand=b'qt  '), 'isobmff', [], ['moov/udta/XMP_'])
        self.absent(build.mp4(), 'isobmff')
        self.absent(build.mp4(trailing=b'\x00' * 7), 'isobmff')
        self.truncated(data[:-10])

    def test_heif_xmp_item(self):
        for method in (0, 1):
            with self.subTest(method=method):
                self.check(build.heif(c2pa=self.STORE, xmp_packet=XMP, method=method), 'isobmff',
                           ['ISOBMFF C2PA uuid box'], ['HEIF XMP item 2'])
        self.absent(build.heif(), 'isobmff')

    def test_riff(self):
        self.check(build.riff(c2pa=self.STORE, xmp_packet=XMP), 'riff',
                   ['RIFF C2PA chunk'], ['RIFF XMP chunk'])
        self.check(build.riff(form=b'AVI ', c2pa=self.STORE), 'riff', ['RIFF C2PA chunk'], [])
        self.check(build.riff(form=b'WAVE', xmp_packet=XMP), 'riff', [], ['RIFF _PMX chunk'])
        self.absent(build.riff(), 'riff')
        self.truncated(build.riff(c2pa=self.STORE, lie_about_size=True))

    def test_gif(self):
        data = build.gif(c2pa=self.STORE, xmp_packet=XMP)
        self.check(data, 'gif', ['GIF C2PA_GIF application extension'],
                   ['GIF XMP application extension'])
        self.absent(build.gif(), 'gif')
        self.truncated(build.gif(trailer=False))

    def test_gif_xmp_in_sub_blocks(self):
        # c2pa-rs 0.91 writes a GIF's XMP and its magic trailer as data sub-blocks, so a
        # length byte falls every 255 bytes of the packet; a remote manifest's address
        # longer than that is cut by one.
        remote = 'https://example.invalid/' + 'm' * 300 + '/manifest.c2pa'
        r = self.check(build.gif(xmp_packet=build.xmp(provenance=remote), xmp_sub_blocks=True),
                       'gif', [], ['GIF XMP application extension'])
        self.assertEqual(r['remote_manifest'], remote)
        self.assertEqual(r['xmp'][0]['creators'], ['Jane Doe'])
        self.assertEqual(r['errors'], [])

    def test_tiff(self):
        for big_endian in (False, True):
            with self.subTest(big_endian=big_endian):
                self.check(build.tiff(c2pa=self.STORE, xmp_packet=XMP, big_endian=big_endian),
                           'tiff', ['TIFF tag 52545'], ['TIFF tag 700'])
        self.absent(build.tiff(), 'tiff')

    def test_jxl(self):
        self.check(build.jxl(c2pa=self.STORE, xmp_packet=XMP), 'jxl', ['JPEG XL jumb box'],
                   ['JPEG XL xml box'])
        self.absent(build.jxl(), 'jxl')
        r = probe(build.jxl(xmp_packet=XMP, brotli_xmp=True))
        self.assertFalse(r['complete'])

    def test_unknown_container(self):
        r = probe(b'%PDF-1.7\n' + b'\x00' * 64)
        self.assertIsNone(r['container'])
        self.assertFalse(r['complete'])

    def test_container_is_decided_by_bytes_not_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'looks_like.jpg')
            with open(path, 'wb') as fh:
                fh.write(build.png(c2pa=self.STORE))
            r = c2paprobe.probe(path)
        self.assertEqual(r['container'], 'png')
        self.assertEqual(len(r['stores']), 1)


class RealFiles(unittest.TestCase):
    """Files real producers wrote, from tests/fixtures (see its README)."""

    FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

    def test_gemini_mp4_store_in_isobmff_uuid_box(self):
        r = c2paprobe.probe(os.path.join(self.FIXTURES, 'gemini-video.mp4'))
        self.assertEqual(r['container'], 'isobmff')
        self.assertTrue(r['complete'], r['errors'])
        self.assertEqual(r['errors'], [])
        self.assertEqual([(s['where'], s['offset']) for s in r['stores']],
                         [('ISOBMFF C2PA uuid box', 32)])
        m = r['manifests'][-1]
        self.assertEqual(r['active_manifest'], m['label'])
        self.assertTrue(m['claim_generator'].startswith('Google C2PA Core Generator Library'))
        self.assertEqual(m['signature']['signed_by'], 'Google LLC (Google Media Processing Services)')
        self.assertEqual(m['actions'], ['c2pa.created', 'c2pa.edited'])
        self.assertEqual([s['code'] for s in m['source_types']], ['trainedAlgorithmicMedia'])
        self.assertIs(m['ai'], True)


class Limits(unittest.TestCase):

    def test_oversized_block_is_refused_not_read(self):
        old = c2paprobe.MAX_STORE
        try:
            c2paprobe.MAX_STORE = 100
            r = probe(build.png(c2pa=build.store()))
        finally:
            c2paprobe.MAX_STORE = old
        self.assertFalse(r['complete'])
        self.assertIn('larger than', r['errors'][0])

    def test_deeply_nested_cbor_is_an_error(self):
        nested = b'\x81' * 500 + b'\x00'
        claim = build.superbox(build.CLAIM_UUID, 'c2pa.claim.v2', build.box(b'cbor', nested))
        store = build.store(build.superbox(build.MANIFEST_UUID, 'urn:c2pa:deep', claim))
        m = probe(build.png(c2pa=store))['manifests'][0]
        self.assertTrue(m['errors'])

    def test_random_bytes_never_raise(self):
        import random  # pylint: disable=import-outside-toplevel
        rng = random.Random(7)
        seeds = [build.jpeg(c2pa=build.store(), xmp_packet=XMP), build.png(c2pa=build.store()),
                 build.mp4(c2pa=build.store()), build.gif(c2pa=build.store()),
                 build.tiff(c2pa=build.store()), build.riff(c2pa=build.store()),
                 build.heif(xmp_packet=XMP), build.jxl(c2pa=build.store())]
        for seed in seeds:
            for _ in range(150):
                data = bytearray(seed)
                for _ in range(rng.randint(1, 8)):
                    data[rng.randrange(len(data))] = rng.randrange(256)
                cut = rng.randint(1, len(data))
                c2paprobe.probe_bytes(bytes(data[:cut]))


if __name__ == '__main__':
    unittest.main()

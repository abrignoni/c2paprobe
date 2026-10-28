"""c2pareader FILE [FILE ...]: print what each file's C2PA store and XMP state, as JSON."""

import argparse
import json
import sys

from c2pareader import __version__, probe


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='c2pareader',
        description='Print the Content Credentials (C2PA) and IPTC digital source type a media '
                    'file declares, as JSON. Nothing is verified: signers and times are as stated.')
    parser.add_argument('files', nargs='+', help='media files to read')
    parser.add_argument('--version', action='version', version=f'c2pareader {__version__}')
    args = parser.parse_args(argv)
    status = 0
    for path in args.files:
        try:
            result = probe(path)
        except OSError as exc:
            print(f'{path}: {exc.strerror or exc}', file=sys.stderr)
            status = 1
            continue
        print(json.dumps({'file': path, **result}, indent=2, ensure_ascii=False))
    return status


if __name__ == '__main__':
    raise SystemExit(main())

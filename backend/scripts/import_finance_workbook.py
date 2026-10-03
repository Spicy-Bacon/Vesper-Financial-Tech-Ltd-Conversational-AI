"""Import entry-point scaffold; exact workbook headers have not been supplied.

Do not substitute the older Handoff workbook. Until the Judge_Ready workbook is
available and inspected, this command deliberately creates no release or approval.
"""

import argparse
import sys
from pathlib import Path

from backend.app.catalog.release import WORKBOOK_NAME, source_provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help=f"path to {WORKBOOK_NAME}")
    args = parser.parse_args(argv)
    try:
        provenance = source_provenance(args.workbook)
    except (ValueError, OSError) as error:
        print(f"Import blocked: {error}", file=sys.stderr)
        return 2
    print(f"Source located: {provenance.workbook_filename}; SHA-256 {provenance.workbook_sha256}")
    print("Import blocked: inspect the exact Judge_Ready workbook headers and implement the "
          "three-sheet mapping before publishing. No files written and no approval inferred.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Redacted repository audit; optional source-only ZIP, never a push."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from repository_safety import audit_repository,export_public_source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report',type=Path)
    parser.add_argument('--export',type=Path)
    args=parser.parse_args()
    try:
        report=audit_repository(args.root)
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report.to_dict(),indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'passed':report.passed,'candidate_files':len(report.candidate_paths),
            'source_snapshot_passed':report.source_snapshot_passed,
            'history_blobs_scanned':report.history_blobs_scanned,'findings':len(report.findings),
            'history_contact_metadata_present':report.history_contact_metadata_present}))
        if args.export and report.source_snapshot_passed:
            export_public_source(args.root,args.export)
            return 0
        return 0 if report.passed else 1
    except (OSError,ValueError):
        print('Publication preparation failed. Inspect local file access and the redacted audit; no secret values are logged.')
        return 1


if __name__=='__main__':raise SystemExit(main())

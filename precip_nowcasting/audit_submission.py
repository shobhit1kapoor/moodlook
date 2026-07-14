import argparse
import json

from nowcasting.submission import audit_submission

parser = argparse.ArgumentParser(description="Verify a Solafune submission ZIP before upload.")
parser.add_argument("--submission", required=True)
parser.add_argument("--evaluation-zip", required=True)
args = parser.parse_args()
print(json.dumps(audit_submission(args.submission, args.evaluation_zip), indent=2))

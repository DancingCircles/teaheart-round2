"""Reproduce all generated results offline: python main.py."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

from number_check import check_summary
from reconcile import CITY_FIELDS, STORE_FIELDS, DataError, parse_date, read_table, reconcile


ROOT = Path(__file__).resolve().parent
ENQUIRY_FIELDS = ["enquiry_id", "received", "client", "subject", "body"]
SUMMARY_FIELDS = ["enquiry_id", "summary", "check_passed", "notes"]


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unique_by_id(rows, label):
    result = {}
    for row in rows:
        identifier = row["enquiry_id"].strip()
        if not identifier or identifier in result:
            raise DataError(f"Missing/duplicate enquiry_id in {label}: {identifier!r}")
        result[identifier] = row
    return result


def build_summaries(data_dir):
    sources = unique_by_id(read_table(data_dir / "enquiries.csv", ENQUIRY_FIELDS), "enquiries")
    saved = unique_by_id(read_table(data_dir / "model_summaries.csv", ["enquiry_id", "summary"]), "saved summaries")
    if saved.keys() != sources.keys():
        raise DataError("Saved summary IDs must match enquiry IDs exactly")
    reviews = json.loads((data_dir / "numeric_reviews.json").read_text(encoding="utf-8"))
    if not isinstance(reviews, dict) or reviews.keys() - sources.keys():
        raise DataError("Review file must be a mapping of known enquiry IDs")
    rows, audit = [], {}
    for identifier, row in sorted(sources.items()):
        parse_date(row["received"].strip())  # Input validation only, never numeric evidence.
        source = row["subject"].strip() + "\n" + row["body"].strip()
        summary = saved[identifier]["summary"].strip()
        if not row["subject"].strip() or not row["body"].strip() or not summary:
            raise DataError(f"Empty source/summary for {identifier}")
        result = check_summary(source, summary)
        review = reviews.get(identifier)
        if review and (review.get("source_sha256") != text_hash(source)
                       or review.get("summary_sha256") != text_hash(summary)):
            raise DataError(f"Stale manual review for {identifier}; re-review changed source/summary")
        classifications = review.get("unmatched", {}) if review else {}
        unmatched_raw = {token["raw"] for token in result["unmatched"]}
        if classifications.keys() - unmatched_raw:
            raise DataError(f"Stale unmatched-number review for {identifier}")
        notes = []
        for token in result["unmatched"]:
            reason = "unsupported numeric syntax" if token["key"] is None else "no equal numeric expression in subject + body"
            judgement = classifications.get(token["raw"], "uncertain: manual classification required")
            notes.append(f"{token['raw']!r}: {reason}; {judgement}.")
        if not notes:
            notes.append("All extracted numeric expressions have source matches." if result["summary_tokens"]
                         else "No numeric expressions in this summary; presence check is vacuous.")
        if review:
            notes.append("Assistant review: " + review["semantic_note"])
        else:
            notes.append("Assistant semantic review pending.")
        rows.append({"enquiry_id": identifier, "summary": summary,
                     "check_passed": str(result["check_passed"]).lower(), "notes": " ".join(notes)})
        audit[identifier] = {"source_text": source, "summary": summary, **result,
                             "manual_review": review, "evidence_scope": "subject + body only"}
    return rows, audit


def csv_bytes(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def run(data_dir, output_dir):
    # Finish validation and serialization before opening any generated output.
    result = reconcile(data_dir)
    summaries, audit = build_summaries(data_dir)
    payloads = {
        "totals_by_store.csv": csv_bytes(result.stores, STORE_FIELDS),
        "totals_by_city.csv": csv_bytes(result.cities, CITY_FIELDS),
        "issues.md": result.issues_md.encode("utf-8"),
        "summaries.csv": csv_bytes(summaries, SUMMARY_FIELDS),
        "number_audit.json": (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    # Prevent accidental overwriting of any input through --output-dir.
    inputs = {path.resolve() for path in data_dir.iterdir() if path.is_file()}
    if any((output_dir / name).resolve() in inputs for name in payloads):
        raise DataError("Output paths must not overwrite input files")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        destination = output_dir / name
        temporary = output_dir / (name + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)
    failed = sum(row["check_passed"] == "false" for row in summaries)
    print(f"Wrote {len(payloads)} files; {len(summaries)} summaries; {failed} numeric checks flagged.")
    print("Flagged summaries are review results, not a program failure.")
    print("Reconciliation: " + json.dumps(result.stats, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    arguments = parser.parse_args()
    try:
        run(arguments.data_dir.resolve(), arguments.output_dir.resolve())
    except (DataError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}. No results should be treated as updated by this failed run.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

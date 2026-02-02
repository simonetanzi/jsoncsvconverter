import argparse
import csv
from email.mime import text
import json
import io
from pathlib import Path


def infer_fields_from_json(data: dict) -> list[str]:
    """Infer CSV fields from dict-of-records JSON. Always includes 'id' first."""
    keys: set[str] = set()

    for k, record in data.items():
        if not isinstance(record, dict):
            raise ValueError(f"Record under key {k!r} is not an object/dict.")
        keys.update(record.keys())

    # 'id' is reserved / handled separately
    keys.discard("id")

    # Deterministic ordering: alphabetical
    return ["id"] + sorted(keys)


def infer_fields_from_csv(fieldnames: list[str] | None) -> list[str]:
    """Infer fields from CSV headers. Requires 'id'. Keeps header order (with id first)."""
    if not fieldnames:
        raise ValueError("CSV has no headers.")
    if "id" not in fieldnames:
        raise ValueError("CSV must have an 'id' header column.")

    return ["id"] + [h for h in fieldnames if h != "id"]


def json_to_csv_text(data: dict, fields: list[str]) -> str:
    """Convert dict-of-records JSON to CSV text (in memory).
    Row order follows the input JSON object's key order.
    """
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(fields)

    for key, record in data.items():  # preserve insertion order
        if not isinstance(record, dict):
            raise ValueError(f"Record under key {key!r} is not an object/dict.")

        row = []
        for field in fields:
            if field == "id":
                row.append(key)
            else:
                row.append(record.get(field, ""))
        writer.writerow(row)

    return buf.getvalue()



def maybe_parse_scalar(s: str):
    """Optional lightweight type inference for CSV values."""
    s2 = s.strip()
    if s2 == "":
        return ""
    # int
    try:
        i = int(s2)
        return i
    except ValueError:
        pass
    # float
    try:
        f = float(s2)
        return f
    except ValueError:
        pass
    # bool-ish
    low = s2.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return s


def csv_text_to_json(text: str, fields: list[str], infer_types: bool) -> dict:
    """Convert CSV text back into dict-of-records JSON (in memory)."""
    buf = io.StringIO(text, newline="")
    reader = csv.DictReader(buf)

    file_fields = infer_fields_from_csv(reader.fieldnames)
    missing = [h for h in file_fields if h not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"CSV missing required headers: {missing}; found: {reader.fieldnames}")

    # Use the provided fields ordering, but ensure it matches what's actually in the CSV
    # (fields may be inferred from JSON; CSV headers are the source of truth here)
    fields = file_fields

    data: dict[str, dict] = {}

    for row in reader:
        raw_id = (row.get("id") or "").strip()
        if raw_id == "":
            raise ValueError("CSV row missing id.")
        id_key = raw_id  # keep exactly what's in CSV

        record: dict = {}
        for field in fields:
            if field == "id":
                continue
            val = row.get(field, "")
            record[field] = maybe_parse_scalar(val) if infer_types else val

        data[id_key] = record

    return data


def cmd_ping(args: argparse.Namespace) -> int:
    print("pong")
    return 0


def cmd_to_csv(args: argparse.Namespace) -> int:
    in_path: Path = args.input
    out_path: Path = args.output

    if not in_path.exists() or not in_path.is_file():
        print(f"ERROR: input JSON not found: {in_path}")
        return 2

    if out_path.exists() and out_path.is_dir():
        print(f"ERROR: output path is a directory: {out_path}")
        return 2

    if out_path.exists() and not args.force:
        print(f"ERROR: output already exists: {out_path}")
        print("Use --force to overwrite.")
        return 2

    try:
        text = in_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        print(f"ERROR: failed to decode input file as UTF-8: {in_path}")
        print(f"  {e}")
        return 2
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {in_path}")
        print(f"  {e}")
        return 2
    
    if not isinstance(data, dict):
        print("ERROR: expected JSON root to be an object/dict (top-level { ... }).")
        return 2

    try:
        fields = infer_fields_from_json(data)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 2

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="") as f:
            f.write(json_to_csv_text(data, fields))
    except OSError as e:
        print(f"ERROR: failed to write output file: {out_path}")
        print(f"  {e}")
        return 2

    if args.verbose:
        print(f"[verbose] fields={fields}")
        print(f"[verbose] wrote CSV: {out_path}")

    return 0


def cmd_to_json(args: argparse.Namespace) -> int:
    in_path: Path = args.input
    out_path: Path = args.output

    if not in_path.exists() or not in_path.is_file():
        print(f"ERROR: input CSV not found: {in_path}")
        return 2
    
    if out_path.exists() and out_path.is_dir():
        print(f"ERROR: output path is a directory: {out_path}")
        return 2

    if out_path.exists() and not args.force:
        print(f"ERROR: output already exists: {out_path}")
        print("Use --force to overwrite.")
        return 2

    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with in_path.open("r", encoding="utf-8", newline="") as f:
            text = f.read()
    except UnicodeDecodeError as e:
        print(f"ERROR: failed to decode input file as UTF-8: {in_path}")
        print(f"  {e}")
        return 2

    try:    
        # fields come from CSV headers
        header_row = next(csv.reader(io.StringIO(text, newline="")))
        fields = infer_fields_from_csv(header_row)
        data = csv_text_to_json(text, fields, infer_types=args.infer_types)
    except StopIteration:
        print("ERROR: CSV has no headers (file is empty).")
        return 2
    except ValueError as e:
        print(f"ERROR: {e}")
        return 2
    try:
        out_path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"ERROR: failed to write output file: {out_path}")
        print(f"  {e}")
        return 2

    if args.verbose:
        print(f"[verbose] fields={fields}")
        print(f"[verbose] wrote JSON: {out_path}")

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    in_path: Path = args.input

    if not in_path.exists() or not in_path.is_file():
        print(f"ERROR: input JSON not found: {in_path}")
        return 2

    try:
        text = in_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        print(f"ERROR: failed to decode input file as UTF-8: {in_path}")
        print(f"  {e}")
        return 2
    try:
        original = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {in_path}")
        print(f"  {e}")
        return 2
    
    if not isinstance(original, dict):
        print("ERROR: expected JSON root to be an object/dict (top-level { ... }).")
        return 2

    try:
        fields = infer_fields_from_json(original)
        csv_text = json_to_csv_text(original, fields)
        roundtrip = csv_text_to_json(csv_text, fields, infer_types=args.infer_types)
    except ValueError as e:
        print(f"ERROR: verify failed during conversion: {e}")
        return 2

    if original == roundtrip:
        print("VERIFY: PASS (JSON -> CSV -> JSON is lossless for current schema)")
        if args.verbose:
            print(f"[verbose] fields={fields}")
        return 0

    print("VERIFY: FAIL (round-trip mismatch)")
    if args.verbose:
        print(f"[verbose] fields={fields}")

        original_keys = set(original.keys())
        roundtrip_keys = set(roundtrip.keys())
        missing = [k for k in original.keys() if k not in roundtrip]
        extra = [k for k in roundtrip.keys() if k not in original]

        if missing:
            print(f"[verbose] missing keys: {missing[:10]}{'...' if len(missing) > 10 else ''}")
        if extra:
            print(f"[verbose] extra keys: {extra[:10]}{'...' if len(extra) > 10 else ''}")

        for k in original.keys():
            if k in roundtrip and original[k] != roundtrip[k]:
                print(f"[verbose] first differing key: {k}")
                print(f"[verbose] original[{k}] = {original[k]}")
                print(f"[verbose] roundtrip[{k}] = {roundtrip[k]}")
                break
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jsoncsvconverter",
        description="Convert JSON ↔ CSV (Day 9 standalone tool)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ping = sub.add_parser("ping", help="Sanity check command.")
    p_ping.set_defaults(func=cmd_ping)

    p_to_csv = sub.add_parser("to-csv", help="Convert JSON -> CSV")
    p_to_csv.add_argument("input", type=Path, help="Input JSON file path")
    p_to_csv.add_argument("output", type=Path, help="Output CSV file path")
    p_to_csv.add_argument("--force", action="store_true", help="Overwrite output file if it exists")
    p_to_csv.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p_to_csv.set_defaults(func=cmd_to_csv)

    p_to_json = sub.add_parser("to-json", help="Convert CSV -> JSON")
    p_to_json.add_argument("input", type=Path, help="Input CSV file path")
    p_to_json.add_argument("output", type=Path, help="Output JSON file path")
    p_to_json.add_argument("--force", action="store_true", help="Overwrite output file if it exists")
    p_to_json.add_argument("--infer-types", action="store_true", help="Try to infer ints/floats/bools from CSV values")
    p_to_json.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p_to_json.set_defaults(func=cmd_to_json)

    p_verify = sub.add_parser("verify", help="Verify JSON -> CSV -> JSON round-trip integrity (in-memory).")
    p_verify.add_argument("input", type=Path, help="Input JSON file path")
    p_verify.add_argument("--infer-types", action="store_true", help="Try to infer ints/floats/bools from CSV values")
    p_verify.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p_verify.set_defaults(func=cmd_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

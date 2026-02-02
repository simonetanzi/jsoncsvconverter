# Manual Test Fixtures

This document describes a set of manual test fixtures included with the project.

These tests are not automated. They are intended to be run manually to demonstrate and verify specific behaviors, edge cases, and design decisions of the JSON ↔ CSV conversion process.

Each test focuses on a single scenario and documents the expected outcome when running the CLI with different options.

## Type Loss During CSV Round-Trip (`tests/type_loss.json`)

This test demonstrates the inherent loss of type information when converting structured JSON data to CSV and back.

Numeric and boolean values in JSON are serialized as strings in CSV, which causes a round-trip verification failure unless type inference is explicitly enabled.

### How to Run

```bash
python src/tool.py verify tests/type_loss.json
```

Expected result: verification fails.

Reason: integer, float, and boolean values are converted to strings during the CSV round-trip, causing a type mismatch.

```bash
python src/tool.py verify tests/type_loss.json --infer-types
```

### Expected result: verification passes.

Reason: --infer-types restores common scalar types (integers, floats, booleans) when reading CSV data.

### What This Test Demonstrates

* CSV is an untyped format and cannot preserve JSON scalar types by default
* Round-trip verification exposes type mismatches explicitly
* Type inference is opt-in, not automatic, by design

## Type Inference Risk: Leading Zeros (`tests/leading_zeros.csv`)

This test demonstrates a common pitfall of automatic type inference: some values look numeric but are actually identifiers where leading zeros are meaningful (e.g., ZIP codes, account codes).

### How to Run

Convert the CSV to JSON without type inference:

```bash
python src/tool.py to-json tests/leading_zeros.csv outputs/no_infer_leading_zeros.json
```

Convert the same CSV with type inference enabled:

```bash
python src/tool.py to-json tests/leading_zeros.csv outputs/infer_leading_zeros.json --infer-types
```

### Expected Result

* In outputs/no_infer_leading_zeros.json, values like zip_code and account_code should preserve leading zeros (e.g., "00123").
* In outputs/infer_leading_zeros.json, --infer-types converts these values to numbers, which removes leading zeros (e.g., "00123" becomes 123).

What This Test Demonstrates

* Some CSV fields should remain strings even if they contain digits.
* --infer-types is opt-in because it can change the meaning of identifier-like values.
* Type inference is useful for true numeric fields, but it must be applied with care.

## Missing Required ID Header (`tests/missing_id_header.csv`)

This test verifies that the CSV → JSON conversion enforces the required input contract.
CSV files must include an id column; without it, records cannot be mapped to JSON object keys.

### How to Run

```bash
python src/tool.py to-json tests/missing_id_header.csv outputs/missing_id_header.json
```

### Expected Result

* The command fails with an error.
* Exit code 2 (invalid input).
* An error message indicates that the required id column is missing.
* No valid output file is produced.

### What This Test Demonstrates

* Input validation is enforced before conversion.
* Required schema elements are explicit, not inferred.
* Errors are reported clearly and consistently via exit codes.

## Duplicate IDs in CSV (`tests/duplicate_id.csv`)

This test demonstrates how the converter handles duplicate id values when converting CSV data to JSON.

Because JSON object keys must be unique, duplicate IDs in the input CSV are resolved deterministically during conversion.

### How to Run

```bash
python src/tool.py to-json tests/duplicate_id.csv outputs/duplicate_id.json
```

### Expected Result

* The command succeeds and produces a JSON output file.
* When multiple rows share the same id, the last occurrence wins.
* Earlier rows with the same id are overwritten by later ones during conversion.

### What This Test Demonstrates

* Duplicate identifiers are handled in a predictable, deterministic way.
* Later rows take precedence when key collisions occur.
* Collision resolution behavior is explicit and documented, not implicit.

## Missing Fields in CSV Rows (`tests/missing_fields.csv`)

This test demonstrates how the converter handles missing or empty field values in CSV input.

Some rows intentionally omit values for certain columns to observe how empty cells are represented in the resulting JSON output.

### How to Run

```bash
python src/tool.py to-json tests/missing_fields.csv outputs/missing_fields.json
```

(Optional) You may also run verification to observe round-trip behavior:

```bash
python src/tool.py verify tests/missing_fields.csv
```

### Expected Result

* The command succeeds and produces a JSON output file.
* Missing CSV fields are represented as empty strings ("") in the JSON output.
* Rows with incomplete data are still included and converted.

### What This Test Demonstrates

* Empty CSV cells are handled explicitly and consistently.
* Missing values do not cause rows to be discarded.
* Empty strings may affect round-trip verification and should be considered when validating data integrity.
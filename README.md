# jsoncsvconverter

A small, robust command-line tool to convert between JSON and CSV formats, with explicit verification of round-trip integrity.

This tool is designed as a **non-interactive CLI utility**: it takes all input at launch, performs a single operation, and exits with a meaningful status code.

---

## Features

- Convert **JSON → CSV**
- Convert **CSV → JSON**
- Verify **JSON → CSV → JSON** round-trip integrity entirely in memory
- Preserve input order (rows are not reordered)
- Explicit handling of CSV type loss via an opt-in flag
- Clear error messages and exit codes
- Hardened against common real-world issues (locked files, empty CSVs, encoding errors)

---

## Quick Start

Run the following commands from the repository root. Requires Python 3.x; no third-party dependencies.

Sanity check that the CLI is available:
```bash
python src/tool.py ping
```

Convert the provided example JSON file to CSV:
```bash
python src/tool.py to-csv data/example.json outputs/example.csv --force
```

Verify round-trip integrity of the example data:
```bash
python src/tool.py verify data/example.json --infer-types
```

---

## Design Goals

This tool exists to make JSON ↔ CSV conversion explicit and predictable. JSON is structured and typed; CSV is flat and untyped, so round-tripping can change data types and interpretation. Instead of silently “fixing” these differences, the tool exposes them: verify checks JSON → CSV → JSON integrity in memory, and --infer-types provides an opt-in way to restore common scalar types when converting from CSV. Record order is preserved and errors are reported with clear messages and exit codes.

---

## Supported Input Formats

### JSON

- Root must be a JSON object (`{ ... }`)
- Top-level keys act as record IDs
- Each value must be an object (record)

Example:

```json
{
  "10": { "gametitle": "Zelda", "stars": 5 },
  "2":  { "gametitle": "Mario", "stars": 4 }
}
```
### CSV

- Must contain a header row
- Must include an id column (position does not matter)
- All values are read as strings unless type inference is enabled

Example:
```csv
gametitle,stars,id
Zelda,5,10
Mario,4,2
```

## Commands

### ping

Sanity check command.
```bash
python src/tool.py ping
```

### to-csv

Convert JSON → CSV.
```bash
python src/tool.py to-csv input.json output.csv
```

Options:

--force — overwrite output file if it exists

-v, --verbose — verbose diagnostic output

Notes:

- Row order follows the order of keys in the input JSON file
- Output CSV always places id as the first column

## to-json

Convert CSV → JSON.
```bash
python src/tool.py to-json input.csv output.json
```

Options:

--force — overwrite output file if it exists

--infer-types — attempt to restore integers, floats, and booleans

-v, --verbose — verbose diagnostic output

Notes:

- JSON object key order follows CSV row order
- Without --infer-types, all CSV values are treated as strings

## verify

Verify round-trip integrity:
```bash
python src/tool.py verify input.json
```

This performs:

JSON → CSV → JSON


entirely in memory and compares the result to the original input.

Options:
--infer-types — enable type inference during CSV → JSON

-v, --verbose — show detailed mismatch diagnostics

Exit behavior:

PASS → lossless round-trip for the current schema

FAIL → mismatch detected (types, missing fields, or values)

## Ordering Behavior

Input order is preserved

JSON → CSV: rows follow JSON key order

CSV → JSON: keys follow CSV row order

The tool does not sort records.

## Error Handling & Exit Codes
| Exit Code | Meaning |
|----------:|---------|
| 0 | Success |
| 1 | Verification failed (data mismatch) |
| 2 | Invalid input, I/O error, or conversion failure |

Common handled error cases:

Output path is a directory

Output file is locked or not writable

Empty CSV files

Missing required headers

Invalid JSON

Non-UTF-8 input files

## Encoding

Input files are expected to be UTF-8

If decoding fails, the tool exits with a clear error message

No automatic encoding guessing is performed

## Project Structure
```
jsoncsvconverter/
├── LICENSE
├── README.md
├── requirements.txt
├── data/
├── docs/
├── outputs/
├── src/
│   └── tool.py
└── tests/
```

## Design Notes

CSV is inherently untyped; type restoration is intentionally opt-in

Failures are explicit rather than silently corrected

CLI parsing and business logic are kept separate

The tool favors clarity and predictability over cleverness

## License

MIT License


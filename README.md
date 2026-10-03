# Part C: Extraction + Validation

This folder mirrors the exact structure from `TEAM_GUIDE.md` section 3. Once
your team's repo exists, copy the contents of `src/` and `tests/` straight
into the matching folders there — no renaming needed.

## What's here (and why nothing else is)

```
src/docint/extraction/
  _tokens.py    -- internal: converts OCRToken dicts into a usable OCRWord
  fields.py     -- regex + label-anchor field extraction
  tables.py     -- reconstructs line-item tables from word positions
  extract.py    -- extract(doc_type, tokens) -- the ONLY function others should import
  __init__.py

src/docint/validation/
  rules.py      -- required-field checks + business rules (RULES_BY_TYPE)
  __init__.py   -- validate(doc_type, fields, tables) -- ditto, the public function

tests/
  test_extraction.py
  test_validation.py
  fixtures/*.json   -- sample OCR tokens in the real contract format
```

Per the contract in `TEAM_GUIDE.md` section 2, `doc_type` arrives as an
**argument** — B's `classify()` decides it upstream. This package never
classifies documents; it only extracts and validates once told what type
it's looking at. If you built or explored an ML classifier earlier, that
belongs in B's `src/docint/classifier/`, not here — feel free to offer it
to them as a starting point, but don't commit it into your own folders.

## Confirmed working

I ran all 9 tests manually against this exact code before handing it over
(no pytest available in my sandbox, so I called the test functions
directly) — all passed. In your repo, run them properly with:

```bash
PYTHONPATH=src pytest tests/test_extraction.py tests/test_validation.py
```

## How to actually get this into the repo

```bash
git checkout main && git pull
git checkout -b feature/extract-fields

# copy files into place
cp -r src/docint/extraction  <repo>/src/docint/
cp -r src/docint/validation  <repo>/src/docint/
cp tests/test_extraction.py tests/test_validation.py <repo>/tests/
cp tests/fixtures/*.json <repo>/tests/fixtures/   # create this folder if needed

cd <repo>
pytest                       # must pass, including everyone else's tests
git add .
git commit -m "extraction: add field/table extraction and validation rules"
git push -u origin feature/extract-fields
```

Then open a PR per section 5 of the guide.

## One thing to raise with your team

`TEAM_GUIDE.md`'s contract table lists `validate(fields)` with a single
argument, but the real rules (line items summing to the total, required
fields per document type) need `doc_type` and the `table` too — you can't
check those without them. `validation/rules.py`'s `validate()` here takes
`(doc_type, fields, tables)` as the practical fix. Per the guide's own
"golden rule," post this in the group chat and get agreement before anyone
builds against the wrong signature.

## Extending it

- New field: add a regex to `fields.py`'s `REGEX_PATTERNS`, or a label to
  `LABEL_FIELD_MAP` if it needs position-based extraction.
- New document type: add its required fields to `rules.py`'s `REQUIRED_FIELDS`.
- New business rule: write a `check_...()` function in `rules.py` and add it
  to `COMMON_RULES` or `RULES_BY_TYPE`.
- Forms and certificates: right now only invoices get the line-item-sum
  check — your task list's "later" items (certificates/forms depth, an
  ML/NER layer for hard fields) build on top of this same structure.

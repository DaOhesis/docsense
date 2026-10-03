# Part C: Extraction & Validation Engine (`src/docint`)

This module handles structured field extraction, line-item table reconstruction, and business-rule validation for the DocSense pipeline. It consumes OCR tokens provided by Stage A and document classification labels provided by Stage B.


src/docint/
├── extraction/
│   ├── __init__.py       
│   ├── _tokens.py        
│   ├── extract.py         
│   ├── fields.py          
│   └── tables.py         
└── validation/
    ├── __init__.py        
    └── rules.py          


# Public API Contracts :

1. Extraction Interface
  docint.extraction.extract(doc_type: str,  tokens: list[dict]) -> tuple[dict, list]

  Inputs:
   Classified document type from Stage B and raw bounding-box tokens from Stage A.

  Outputs:
   fields: Extracted key-value pairs (e.g., invoice number, date, total amount).

   tables: Reconstructed line-item arrays.

2. Validation Interface
 docint.validation.validate(doc_type: str, fields: dict, tables: list) -> tuple[dict, bool]

  Inputs:
   Extracted field and table payload alongside the document classification.

  Outputs:
  validation_results: Detailed dictionary of checks performed.

 needs_review:
  Boolean flag indicating whether human review is required downstream.



# Testing & Fixtures:
The test suite includes complete end-to-end extraction and validation tests against fixture datasets (invoices, receipts, forms, certificates).

To run the full test suite locally:

Bash
$env:PYTHONPATH="src"; python -m pytest tests/


# Extensibility Guidelines:
  Adding New Field Rules:
   Update REGEX_PATTERNS or LABEL_FIELD_MAP in src/docint/extraction/fields.py.

  Adding New Document Types: 
   Define required field parameters in REQUIRED_FIELDS inside src/docint/validation/rules.py.

  Adding Custom Business Rules:
   Define custom validation functions in src/docint/validation/rules.py and register them under COMMON_RULES or RULES_BY_TYPE.






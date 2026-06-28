# Data Directory

Place challenge files here as described below.

## Expected Structure

```
challenge_data/
├── raw/
│   ├── candidates.jsonl          # Full 100K candidate dataset
│   ├── candidates.jsonl.gz       # Compressed full dataset
│   ├── job_description.docx      # Senior AI Engineer job description
│   ├── candidate_schema.json     # Candidate JSON schema
│   ├── redrob_signals_doc.docx   # Behavioural signals documentation
│   ├── submission_spec.docx      # Submission rules
│   ├── sample_submission.csv     # Example CSV format only
│   ├── submission_metadata_template.yaml
│   └── README.docx
└── sample/
    └── sample_candidates.json    # 5000-candidate sample dataset
```

## Notes

- Do NOT modify any files in challenge_data/
- Large .jsonl and .jsonl.gz files are gitignored
- The sample_candidates.json is sufficient for demo and testing

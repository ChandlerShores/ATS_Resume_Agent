# Resume Parsing Guide

## Overview

The resume parsing system extracts bullets and metrics from resume files (DOCX, PDF, TXT) and converts them into the `sample_input.json` format required by the ATS Resume Agent state machine.

## Features

- **Multi-format support**: DOCX, PDF, and TXT files
- **Smart bullet detection**: Pattern-based extraction focusing on experience sections
- **Metrics extraction**: Automatic detection of percentages, dollar amounts, counts, and time periods
- **Validation**: Pydantic model validation before saving
- **Error handling**: Clear, actionable error messages for frontend integration
- **Batch processing**: Process multiple resumes with fail-fast behavior

## Installation

The required dependencies are already in `requirements.txt`:

```bash
pip install python-docx pdfplumber chardet
```

Or run the setup script:

```bash
# Windows
.\setup.ps1

# Unix/Mac
./setup.sh
```

## Usage

### Single Resume Parsing

**Basic usage with placeholder JD:**
```bash
python scripts/parse_resume.py \
  --resume john_walker_test.docx \
  --role "Senior Financial Analyst" \
  --output tests/john_input.json
```

**With job description:**
```bash
python scripts/parse_resume.py \
  --resume resume.pdf \
  --role "Data Scientist" \
  --jd-text "We are seeking a Data Scientist with..." \
  --output input.json
```

**With JD from file:**
```bash
python scripts/parse_resume.py \
  --resume resume.docx \
  --role "Software Engineer" \
  --jd-file job_description.txt \
  --output input.json
```

**Preview mode (no output):**
```bash
python scripts/parse_resume.py \
  --resume resume.docx \
  --role "Analyst" \
  --preview
```

**Skip metrics extraction:**
```bash
python scripts/parse_resume.py \
  --resume resume.docx \
  --role "Manager" \
  --output input.json \
  --no-metrics
```

### Batch Processing

**Parse all DOCX files:**
```bash
python scripts/batch_parse_resumes.py \
  --resumes *.docx \
  --role "Senior Financial Analyst" \
  --output-dir tests/parsed_resumes/
```

**Parse specific files:**
```bash
python scripts/batch_parse_resumes.py \
  --resumes resume1.pdf resume2.docx resume3.txt \
  --role "Data Scientist" \
  --output-dir out/parsed/
```

**With job description:**
```bash
python scripts/batch_parse_resumes.py \
  --resumes *.docx \
  --role "Engineer" \
  --jd-file jd.txt \
  --output-dir out/
```

## CLI Options

### parse_resume.py

| Option | Required | Description |
|--------|----------|-------------|
| `--resume` | Yes | Path to resume file (DOCX, PDF, or TXT) |
| `--role` | Yes | Target role/position |
| `--output` | No* | Output path for JSON file |
| `--jd-text` | No | Job description text (inline) |
| `--jd-file` | No | Path to job description file |
| `--jd-url` | No | URL to fetch job description from |
| `--context` | No | Additional context about role/candidate |
| `--no-metrics` | No | Skip metrics extraction |
| `--preview` | No | Show preview without saving |
| `--debug` | No | Show debug information |

*Required unless using `--preview`

### batch_parse_resumes.py

| Option | Required | Description |
|--------|----------|-------------|
| `--resumes` | Yes | Resume files or glob pattern (e.g., *.docx) |
| `--role` | Yes | Target role for all resumes |
| `--output-dir` | Yes | Output directory for JSON files |
| `--jd-text` | No | Job description text (applied to all) |
| `--jd-file` | No | Path to job description file |
| `--jd-url` | No | URL to fetch job description from |
| `--context` | No | Additional context (applied to all) |
| `--no-metrics` | No | Skip metrics extraction |
| `--debug` | No | Show debug information |

## Output Format

Generated JSON files match the `sample_input.json` structure:

```json
{
  "role": "Senior Financial Analyst",
  "bullets": [
    "Automated month-end close process...",
    "Built Power BI dashboards..."
  ],
  "metrics": {
    "percentages": ["31%", "45%"],
    "dollar_amounts": ["$2M"],
    "counts": {"entities": 12, "users": 45},
    "time_periods": ["3 years"]
  },
  "jd_text": "Job description here...",
  "jd_url": null,
  "extra_context": "",
  "settings": {
    "tone": "concise",
    "max_len": 30,
    "variants": 2
  }
}
```

## Bullet Detection

The parser uses pattern matching to identify bullets:

- Lines starting with: `•`, `-`, `*`, `–`, `—`
- Numbered lists: `1.`, `2.`, etc.
- Indented lines in Experience sections
- Focus on "Experience" and "Work History" sections

### What's Filtered Out

- Education entries (degrees, schools)
- Contact information (emails, phones)
- Section headers
- Very short lines (<15 characters)

## Metrics Extraction

Automatically extracts:

- **Percentages**: `31%`, `increased by 45%`
- **Dollar amounts**: `$2M`, `$500K`, `saved $100,000`
- **Counts with context**: `12 entities`, `45 users`, `15 reports`
- **Time periods**: `3 years`, `6 months`, `2 quarters`

### Validation Rules

- Percentages: 1-1000%
- Dollar amounts: $1K-$999B (with K/M/B suffixes)
- Counts: 1-100,000 (with metric keywords)
- Time periods: Reasonable ranges for years/months/weeks/days

## Error Handling

### Exception Types

All errors inherit from `ResumeParsingError` for easy catching:

- `UnsupportedFormatError`: File format not supported (not .docx/.pdf/.txt)
- `FileReadError`: Cannot read file (missing, corrupted, permissions)
- `NoBulletsFoundError`: No bullets could be extracted
- `ValidationError`: Generated JSON fails Pydantic validation

### Error Messages

Errors are frontend-friendly and actionable:

```
❌ Error: Format .xlsx not supported. Supported formats: .docx, .pdf, .txt
❌ Error: File not found: resume.docx
❌ Error: No bullets found in resume.pdf. The resume may have non-standard formatting or bullets may be in images/tables.
```

### Batch Processing Behavior

Batch processing uses **fail-fast** behavior:
- First error stops the entire batch
- Exit code 1 indicates parsing error
- Exit code 2 indicates unexpected error
- Shows which file failed and how many succeeded

## Troubleshooting

### "No bullets found"

**Causes:**
- Resume uses non-standard formatting
- Bullets are in tables/text boxes (DOCX limitation)
- Bullets are in images
- Resume is actually a cover letter

**Solutions:**
- Use `--preview --debug` to see what's being extracted
- Try saving as plain text (.txt) and parsing that
- Manually format the resume with standard bullet points

### "Metrics extraction failed"

**Causes:**
- Non-critical issue - parsing continues
- Unusual number formats
- Metrics in different languages

**Solutions:**
- Metrics are optional - resume will still parse
- Use `--no-metrics` to skip extraction
- Manually add metrics to output JSON later

### "Failed to decode TXT file"

**Causes:**
- Non-UTF-8 encoding
- Binary/corrupted file

**Solutions:**
- Install `chardet` for automatic detection: `pip install chardet`
- Save file as UTF-8 in text editor
- Convert to DOCX or PDF format

### "Extracted suspicious number of bullets" (< 3)

**Causes:**
- Resume has minimal content
- Parser missed bullets due to unusual formatting

**Solutions:**
- Review output JSON - may still be valid
- Reformat resume with clearer structure
- Manually add missing bullets to JSON

## Integration with State Machine

### Placeholder Job Descriptions

If no JD is provided, the parser uses a placeholder:

```
⚠️ JOB DESCRIPTION TO BE PROVIDED ⚠️

Please replace this placeholder with the actual job description
before running the state machine.
```

**Important:** You MUST replace this before feeding to the state machine, otherwise it will fail at the EXTRACT_SIGNALS stage.

### Workflow

1. **Parse Resume** → Generate JSON
2. **Review Output** → Check bullets and metrics
3. **Add Real JD** → Replace placeholder in JSON
4. **Run State Machine** → Process with ATS Agent

```bash
# Step 1: Parse
python scripts/parse_resume.py --resume resume.docx --role "Analyst" --output input.json

# Step 2: Edit input.json and replace placeholder JD

# Step 3: Run state machine
python -m orchestrator.state_machine --input input.json --out result.json
```

## Architecture

### Component Flow

```
Resume File (.docx/.pdf/.txt)
    ↓
[resume_parser.py] Extract text & bullets
    ↓
[metrics_extractor.py] Extract metrics (optional)
    ↓
[input_builder.py] Build JobInput dict
    ↓
[Pydantic Validation] Validate structure
    ↓
JSON Output File
```

### Files

- `ops/parsing_errors.py` - Exception hierarchy
- `ops/resume_parser.py` - Core parsing logic
- `ops/metrics_extractor.py` - Regex-based metrics extraction
- `ops/input_builder.py` - JSON builder with validation
- `scripts/parse_resume.py` - Single resume CLI
- `scripts/batch_parse_resumes.py` - Batch processing CLI

## Examples

### Example 1: Financial Analyst Resume

```bash
python scripts/parse_resume.py \
  --resume financial_analyst_resume.docx \
  --role "Senior Financial Analyst" \
  --jd-file fp_and_a_job_description.txt \
  --context "Specializes in D365 and Power BI" \
  --output tests/fa_input.json
```

**Output includes:**
- 12-15 extracted bullets
- Metrics: percentages (variance analysis), counts (entities, reports)
- JD text from file
- Ready for state machine processing

### Example 2: Batch Process 10 Resumes

```bash
python scripts/batch_parse_resumes.py \
  --resumes candidate_resumes/*.docx \
  --role "Data Scientist" \
  --jd-file data_scientist_jd.txt \
  --output-dir parsed_candidates/ \
  --context "Seeking ML/AI expertise"
```

**Result:**
- Processes all .docx files in `candidate_resumes/`
- Stops at first error (fail-fast)
- Creates `parsed_candidates/candidate1_input.json`, etc.
- All use same JD and context

### Example 3: Preview Before Saving

```bash
python scripts/parse_resume.py \
  --resume resume.pdf \
  --role "Software Engineer" \
  --preview
```

**Shows:**
- Number of bullets extracted
- First 10 bullets
- Extracted metrics
- No file is saved

## Best Practices

1. **Always preview first** - Use `--preview` to check extraction quality
2. **Provide real JDs** - Placeholder JDs must be replaced before state machine
3. **Batch carefully** - Test single resumes before batch processing
4. **Review metrics** - Auto-extracted metrics may need manual cleanup
5. **Use consistent roles** - Same role for similar resumes in batch mode
6. **Check output** - Validate JSON structure before feeding to state machine

## Limitations

1. **DOCX tables/textboxes** - `python-docx` may miss content in complex layouts
2. **PDF rendering** - Some PDFs with unusual encoding may not parse correctly
3. **Image-based resumes** - Cannot extract text from images
4. **Mixed content** - May extract non-work bullets (education, skills lists)
5. **Metrics accuracy** - Regex-based, may extract irrelevant numbers (~80% accuracy)

## Future Enhancements

- [ ] OCR support for image-based PDFs
- [ ] Better section detection (ML-based)
- [ ] Custom bullet patterns per industry
- [ ] LLM-based metrics extraction
- [ ] Resume format normalization
- [ ] Multi-language support


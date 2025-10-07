<!-- 488dbe6a-dafb-45db-b565-a5731c4685db 3676e01a-38aa-47b0-90cf-0f078e5cbb31 -->
# Resume Parser Integration Plan (Refined)

## Overview

Build standalone resume parsing utility to extract bullets and metrics from DOCX/PDF/TXT files and generate sample_input.json format. This is a preprocessing tool with explicit error handling for frontend integration. NOT yet integrated with state machine.

## Core Components

### 1. Error Handling (`ops/parsing_errors.py`)

**Purpose**: Custom exception hierarchy for clear error propagation

**Exception Classes**:

```python
class ResumeParsingError(Exception):
    """Base exception for all parsing errors"""
    pass

class UnsupportedFormatError(ResumeParsingError):
    """File format not supported (not DOCX/PDF/TXT)"""
    pass

class FileReadError(ResumeParsingError):
    """Cannot read file (corrupted, missing, permissions)"""
    pass

class NoBulletsFoundError(ResumeParsingError):
    """No bullets could be extracted from resume"""
    pass

class ValidationError(ResumeParsingError):
    """Generated JSON fails Pydantic validation"""
    pass
```

**Error Strategy**:

- All functions raise specific exceptions (no silent failures)
- Batch processing fails fast - first error stops entire batch
- All file operations use `with` statements for cleanup
- Error messages are frontend-friendly (clear, actionable)

### 2. Resume Parser Module (`ops/resume_parser.py`)

**Purpose**: Extract text and structure from multiple file formats

**Implementation**:

- DOCX: Use `python-docx` to extract paragraphs
- PDF: Use `pdfplumber` for text extraction
- TXT: File read with UTF-8 → chardet fallback
- Bullet detection patterns:
  - Lines starting with: `•`, `-`, `*`, `–`, `—`
  - Lines in "Experience" sections with indentation
  - Numbered lists (1., 2., etc.)

**Key Methods**:

```python
def parse_resume(file_path: str) -> Dict[str, Any]:
    """Returns: {bullets: List[str], raw_text: str, metadata: dict}
    Raises: UnsupportedFormatError, FileReadError, NoBulletsFoundError"""

def extract_bullets(text: str) -> List[str]:
    """Smart bullet detection from raw text
    Raises: NoBulletsFoundError if <1 bullet found"""
```

**Error Handling**:

```python
try:
    # Detect format
    ext = Path(file_path).suffix.lower()
    if ext not in ['.docx', '.pdf', '.txt']:
        raise UnsupportedFormatError(f"Format {ext} not supported")
    
    # Parse based on format
    with open(file_path, 'rb') as f:
        if ext == '.docx':
            text = extract_from_docx(f)
        elif ext == '.pdf':
            text = extract_from_pdf(f)
        else:
            text = extract_from_txt(f)
    
    bullets = extract_bullets(text)
    if not bullets:
        raise NoBulletsFoundError(f"No bullets found in {file_path}")
    
    return {"bullets": bullets, "raw_text": text}
    
except FileNotFoundError:
    raise FileReadError(f"File not found: {file_path}")
except Exception as e:
    raise FileReadError(f"Failed to read {file_path}: {e}")
```

### 3. Metrics Extraction (`ops/metrics_extractor.py`)

**Purpose**: Extract quantifiable metrics from bullet text using regex

**Patterns**:

- Percentages: `31%`, `increased by 45%`
- Dollar amounts: `$2M`, `$500K`, `saved $100,000`
- Numbers with context: `12 entities`, `45 users`, `15 reports`
- Time periods: `3 years`, `6 months`

**Output Format**:

```python
{
    "percentages": ["31%", "45%"],
    "dollar_amounts": ["$2M"],
    "counts": {"entities": 12, "users": 45},
    "time_periods": ["3 years"]
}
```

**Error Handling**: Non-critical - if extraction fails, return empty dict, log warning

### 4. Input Builder (`ops/input_builder.py`)

**Purpose**: Convert parsed resume to sample_input.json format

**Signature**:

```python
def build_sample_input(
    resume_path: str,
    role: str,  # Required
    jd_text: str = None,  # Optional - uses placeholder
    extra_context: str = None,
    settings: dict = None
) -> Dict[str, Any]:
    """Build JobInput-compatible dict
    Raises: ValidationError if Pydantic validation fails"""
```

**Implementation**:

```python
try:
    parsed = parse_resume(resume_path)  # May raise parsing errors
    
    # Extract metrics (non-critical)
    try:
        metrics = extract_metrics(parsed['bullets'])
    except Exception as e:
        logger.warning(f"Metrics extraction failed: {e}")
        metrics = {}
    
    # Build input dict
    input_dict = {
        "role": role,
        "jd_text": jd_text or "Job description to be provided",
        "bullets": parsed['bullets'],
        "metrics": metrics,
        "extra_context": extra_context or "",
        "settings": settings or {"tone": "concise", "max_len": 30, "variants": 2}
    }
    
    # Validate with Pydantic
    JobInput(**input_dict)  # Raises pydantic.ValidationError
    
    return input_dict
    
except pydantic.ValidationError as e:
    raise ValidationError(f"Invalid input structure: {e}")
```

### 5. CLI Tool (`scripts/parse_resume.py`)

**Purpose**: Single resume parsing CLI

**Usage**:

```bash
python scripts/parse_resume.py \
  --resume john_walker_test.docx \
  --role "Senior Financial Analyst" \
  --output tests/john_walker_input.json \
  [--jd-text "..." or --jd-file path/to/jd.txt] \
  [--context "Additional context"] \
  [--debug]
```

**Error Handling**:

```python
try:
    input_dict = build_sample_input(...)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(input_dict, f, indent=2)
    print(f"✅ Successfully created {output_path}")
    print(f"   Extracted {len(input_dict['bullets'])} bullets")
    sys.exit(0)
    
except ResumeParsingError as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}", file=sys.stderr)
    sys.exit(2)
```

### 6. Batch Processor (`scripts/batch_parse_resumes.py`)

**Purpose**: Process multiple resumes with fail-fast behavior

**Usage**:

```bash
python scripts/batch_parse_resumes.py \
  --resumes *.docx \
  --role "Senior Financial Analyst" \
  --output-dir tests/parsed_resumes/
```

**Fail-Fast Behavior**:

```python
for i, resume_file in enumerate(resume_files, 1):
    print(f"Processing {i}/{len(resume_files)}: {resume_file}")
    try:
        # Process resume - any error stops batch
        input_dict = build_sample_input(resume_file, role, ...)
        output_path = output_dir / f"{Path(resume_file).stem}_input.json"
        with open(output_path, 'w') as f:
            json.dump(input_dict, f, indent=2)
        print(f"  ✅ Success")
        
    except ResumeParsingError as e:
        # Fail fast - stop entire batch
        print(f"  ❌ Error: {e}", file=sys.stderr)
        print(f"\n⚠️  Batch stopped at file {i}/{len(resume_files)}", file=sys.stderr)
        sys.exit(1)
```

## Potential Bugs and Mitigation

### Bug 1: State Machine JD Requirement

**Issue**: State machine requires JD at line 148

**Mitigation**: Always include placeholder `"Job description to be provided"`

**Impact**: Low - users must replace before running state machine

### Bug 2: Empty Bullets

**Issue**: Parser might extract 0 bullets

**Mitigation**: Raise `NoBulletsFoundError` immediately

**Impact**: Medium - user gets clear error, can inspect file

### Bug 3: Mixed Resume Formats  

**Issue**: Bullets in various sections

**Mitigation**: Focus on "Experience"/"Work History" sections, show preview in CLI

**Impact**: Medium - may extract education bullets, but user can review

### Bug 4: Metrics Extraction Noise

**Issue**: May extract phone numbers, years as metrics

**Mitigation**: Use contextual regex, bounded ranges, graceful degradation

**Impact**: Low - metrics are optional, user can clean manually

### Bug 5: DOCX Tables/Textboxes

**Issue**: python-docx misses formatted content

**Mitigation**: Log warning if <3 bullets, provide --debug flag

**Impact**: Medium - user knows to check file

### Bug 6: File Encoding

**Issue**: TXT files various encodings

**Mitigation**: UTF-8 → chardet fallback, --encoding flag

**Impact**: Low - most files are UTF-8

## Changes to Existing Code

### Dependencies (requirements.txt)

**Add**:

```
python-docx>=1.1.0
pdfplumber>=0.10.0
chardet>=5.2.0
```

**Risk**: None - no conflicts

### No Changes to State Machine

**Rationale**: Keep existing system unchanged, parsing is preprocessing only

### No Changes to Pydantic Models

**Rationale**: Existing JobInput is flexible enough

## Testing Strategy

### Phase 1: Parse Individual Resumes

1. Parse each of 6 test resumes with CLI
2. Manually review extracted bullets
3. Check metrics extraction accuracy
4. Test error scenarios (invalid file, no bullets)

### Phase 2: Validation

1. Validate all generated JSONs against JobInput model
2. Verify JSON structure matches sample_input.json

### Phase 3: Compatibility

1. Feed generated JSONs into state machine with real JD
2. Confirm no regressions in downstream processing

## Deliverables

1. `ops/parsing_errors.py` - Exception hierarchy
2. `ops/resume_parser.py` - Core parsing logic  
3. `ops/metrics_extractor.py` - Regex extraction
4. `ops/input_builder.py` - JSON builder
5. `scripts/parse_resume.py` - Single resume CLI
6. `scripts/batch_parse_resumes.py` - Batch CLI
7. `tests/fixtures/` - 6 parsed JSON outputs
8. Updated `requirements.txt` - New dependencies
9. `docs/RESUME_PARSING.md` - Usage guide

## Success Criteria

- Parse all 6 DOCX resumes successfully
- Extract minimum 3 bullets per resume OR clear error
- Generate valid sample_input.json passing Pydantic validation
- Metrics extracted with >80% accuracy
- CLI tools user-friendly with clear error messages
- Fail-fast batch processing
- No breaking changes to existing functionality

## Implementation Order

1. `ops/parsing_errors.py` - Foundation
2. `ops/resume_parser.py` - Core functionality
3. `ops/metrics_extractor.py` - Optional metrics
4. `ops/input_builder.py` - JSON generation
5. `scripts/parse_resume.py` - CLI tool
6. Test with all 6 resumes, iterate on bugs
7. `scripts/batch_parse_resumes.py` - Batch processing
8. Final testing and documentation

### To-dos

- [ ] Add python-docx, pdfplumber, chardet to requirements.txt
- [ ] Implement ops/resume_parser.py with DOCX, PDF, TXT support
- [ ] Implement ops/metrics_extractor.py with regex patterns
- [ ] Implement ops/input_builder.py to generate sample_input.json format
- [ ] Create scripts/parse_resume.py CLI tool
- [ ] Create scripts/batch_parse_resumes.py for multiple resumes
- [ ] Parse all 6 test DOCX resumes and validate output
- [ ] Test generated JSONs with existing state machine
- [ ] Create docs/RESUME_PARSING.md with usage examples
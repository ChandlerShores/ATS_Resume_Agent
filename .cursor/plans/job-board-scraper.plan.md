# LLM Job Board Scraper Integration Plan

## Overview

Add LLM-powered job board scraping to extract company name, job title, and JD text from any job posting URL. Integrates with existing jd_url handling in JDParser and input_builder.

## Current State Analysis

### Existing jd_url Flow

```
User provides jd_url
    ↓
orchestrator/state_machine.py:144 → jd_parser.fetch_jd_from_url(url)
    ↓
agents/jd_parser.py:52 → httpx.get(url) returns raw HTML
    ↓
agents/jd_parser.py:87 → normalize_text() strips HTML tags
    ↓
Result: Messy text with navigation, ads, etc.
```

**Problem**: Raw HTML contains junk (nav menus, ads, footer). normalize_text() uses basic regex to strip HTML but can't distinguish content from noise.

### Where jd_url is Used

1. **schemas/models.py:22** - `JobInput` model accepts `jd_url` field
2. **agents/jd_parser.py:52** - `fetch_jd_from_url()` fetches raw HTML
3. **orchestrator/state_machine.py:144** - INGEST state calls fetch when jd_url provided
4. **ops/input_builder.py:97** - Resume parser passes jd_url through to JobInput

## Proposed Solution

### New Component: `ops/job_board_scraper.py`

**Purpose**: Fetch URL → extract structured job data using LLM

**Key Method**:

```python
def scrape_job_posting(url: str) -> Dict[str, Any]:
    """
    Returns:
    {
        "company": "Acme Corp",
        "job_title": "Senior Financial Analyst", 
        "jd_text": "We are seeking...",
        "location": "Remote",  # optional
        "salary": "$100K-150K",  # optional
        "raw_html": "...",  # for debugging
        "scraped_at": "2025-10-07T..."
    }
    """
```

**LLM Prompt Strategy**:

```
System: You are a job posting parser. Extract structured data from HTML.

User: Extract these fields from this job posting HTML:
- company: Company name
- job_title: Job title/position
- jd_text: Full job description (requirements, responsibilities, qualifications)
- location: Work location (optional)
- salary: Salary range if listed (optional)

HTML: [truncated to fit context window]

Return JSON only.
```

**Smart HTML Truncation**:

- Many job pages are 100KB+ (exceeds LLM context)
- Strategy: Keep first 50KB of HTML (usually contains job content)
- Strip obvious junk: `<script>`, `<style>`, `<nav>`, `<footer>`
- If still too large, chunk and process in parts

## Integration Points

### 1. Modify `agents/jd_parser.py`

**Current**:

```python
def fetch_jd_from_url(self, url: str) -> str:
    # Returns raw HTML text
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, follow_redirects=True)
        return response.text
```

**New**:

```python
def fetch_jd_from_url(self, url: str, use_scraper: bool = True) -> str:
    if use_scraper:
        from ops.job_board_scraper import scrape_job_posting
        scraped = scrape_job_posting(url)
        return scraped['jd_text']  # Clean JD text only
    else:
        # Fallback: raw HTML (for backward compatibility)
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, follow_redirects=True)
            return response.text
```

**Impact**: Minimal change, backward compatible via `use_scraper` flag

### 2. Extend `schemas/models.py` (Optional)

**Option A**: Add new optional fields to JobInput

```python
class JobInput(BaseModel):
    role: str  # Keep this (user-provided or auto-filled from job_title)
    jd_text: Optional[str] = None
    jd_url: Optional[str] = None
    
    # NEW: Auto-populated from scraper
    company: Optional[str] = None
    job_title: Optional[str] = None  # Can auto-fill 'role' if missing
    location: Optional[str] = None
    salary: Optional[str] = None
```

**Option B**: Don't modify schema, just use scraped data internally

**Recommendation**: Option B for MVP (less breaking). Can add fields later if needed.

### 3. Update `ops/input_builder.py`

**Current**: Passes jd_url through unchanged

**New**: Optionally scrape URL and auto-fill role

```python
def build_sample_input(
    resume_path: str,
    role: str = None,  # Make optional
    jd_url: str = None,
    ...
):
    # If jd_url provided but no role, scrape and auto-fill
    if jd_url and not role:
        from ops.job_board_scraper import scrape_job_posting
        scraped = scrape_job_posting(jd_url)
        role = scraped['job_title']
        jd_text = scraped['jd_text']
        logger.info("Auto-filled role from job posting", role=role)
```

**Impact**: Makes `--role` optional when using `--jd-url` in CLI

### 4. Update CLI tools

**scripts/parse_resume.py**:

```python
parser.add_argument('--role', help='Target role (auto-detected from --jd-url if not provided)')
parser.add_argument('--jd-url', help='Job posting URL to scrape')

# NEW: Smart role handling
if args.jd_url and not args.role:
    print("🔍 Scraping job posting to detect role...")
    # Will be handled by input_builder
```

## Potential Bugs & Mitigation

### Bug 1: LLM Extraction Failures

**Issue**: LLM returns malformed JSON or misses fields

**Impact**: scrape_job_posting() raises exception → state machine fails

**Mitigation**:

- Validate LLM response against Pydantic model
- Retry with simpler prompt if first attempt fails
- Fallback to raw HTML extraction if all else fails
- Log structured error: "Failed to scrape URL, reason: ..."

### Bug 2: Token Limit Exceeded

**Issue**: Job page HTML > 100K tokens

**Impact**: LLM API rejects request

**Mitigation**:

- Pre-process HTML: strip scripts/styles/nav
- Truncate to first 50KB (job content usually at top)
- If still too large, extract `<main>` or `<article>` tags only
- Add token counting before API call

### Bug 3: Paywall/Login Required

**Issue**: LinkedIn, Indeed often require login to view full posting

**Impact**: httpx.get() returns login page HTML

**Detection**: Check for keywords: "sign in", "login", "create account"

**Mitigation**:

- Detect paywall in HTML
- Raise clear error: "This job board requires login. Please copy-paste the JD text manually."
- Don't waste LLM call on login page

### Bug 4: Non-Job URLs

**Issue**: User provides wrong URL (company homepage, search results page)

**Impact**: LLM extracts wrong data or fails

**Mitigation**:

- LLM should detect: "This doesn't appear to be a job posting"
- Validate extracted data (job_title should look like a job title)
- Return confidence score, warn if low

### Bug 5: Idempotency Key Changes

**Issue**: Currently `jd_hash = sha256(jd_text)`. If scraping extracts cleaner text, hash changes even for same URL.

**Impact**: Breaks idempotency - same job processed multiple times

**Mitigation**:

- Use URL as part of idempotency key, not just jd_text
- Or normalize jd_text consistently (lowercase, trim, remove extra spaces)
- Cache scraped results by URL to avoid re-scraping

### Bug 6: Cost Per Job

**Issue**: Each scrape costs ~$0.02-0.05

**Impact**: Batch processing 100 resumes against same job = $2-5 wasted

**Mitigation**:

- Cache scraped job postings by URL
- TTL: 24 hours (job postings rarely change)
- Store in `out/job_cache/[url_hash].json`
- Check cache before scraping

### Bug 7: Slow Scraping

**Issue**: LLM call takes 2-5 seconds

**Impact**: User waits longer, especially for batch processing

**Mitigation**:

- Show progress: "🔍 Scraping job posting from LinkedIn..."
- Cache results (see Bug 6)
- Run in background if processing multiple resumes

### Bug 8: State Machine Breaking Change

**Issue**: state_machine.py:144 expects `fetch_jd_from_url()` to return string

**Impact**: If we change return type, state machine breaks

**Mitigation**:

- Keep `fetch_jd_from_url()` signature unchanged (returns str)
- All scraping logic hidden inside the method
- Backward compatible via `use_scraper` flag

## Implementation Plan

### Phase 1: Core Scraper (MVP)

**File**: `ops/job_board_scraper.py`

```python
def scrape_job_posting(url: str) -> Dict[str, Any]
def _fetch_html(url: str) -> str
def _clean_html(html: str) -> str
def _extract_with_llm(html: str) -> Dict[str, Any]
def _validate_scraped_data(data: Dict) -> bool
```

**Dependencies**: beautifulsoup4 for HTML cleaning

### Phase 2: JDParser Integration

**File**: `agents/jd_parser.py`

- Modify `fetch_jd_from_url()` to optionally use scraper
- Keep backward compatibility
- Add `use_scraper=True` parameter

**Breaking Changes**: None (opt-in via parameter)

### Phase 3: CLI Integration

**Files**: `scripts/parse_resume.py`, `ops/input_builder.py`

- Make `--role` optional when `--jd-url` provided
- Auto-detect role from scraped job_title
- Show scraping progress to user

**Breaking Changes**: None (`--role` still required if no `--jd-url`)

### Phase 4: Caching (Optional but Recommended)

**File**: `ops/job_cache.py`

```python
def cache_job_posting(url: str, data: Dict)
def get_cached_job_posting(url: str) -> Optional[Dict]
```

**Storage**: `out/job_cache/[url_hash].json` with TTL metadata

### Phase 5: Testing

- Test with LinkedIn, Indeed, Greenhouse URLs
- Test paywall detection
- Test malformed HTML
- Test token limit edge case
- Verify idempotency still works

## Files Changed

### New Files

1. `ops/job_board_scraper.py` - Core scraping logic (~200 lines)
2. `ops/job_cache.py` - Optional caching (~80 lines)

### Modified Files

1. `agents/jd_parser.py` - Add use_scraper parameter (~10 lines)
2. `ops/input_builder.py` - Auto-detect role from URL (~20 lines)
3. `scripts/parse_resume.py` - Make --role optional (~15 lines)
4. `requirements.txt` - Add beautifulsoup4

### No Changes

1. `schemas/models.py` - Keep existing schema (for now)
2. `orchestrator/state_machine.py` - No changes needed
3. Existing tests continue to work

## Error Handling Strategy

All errors inherit from `ResumeParsingError` for consistency:

```python
class JobScrapingError(ResumeParsingError):
    """Base for scraping errors"""

class PaywallDetectedError(JobScrapingError):
    """Login required to access posting"""
    
class InvalidJobURLError(JobScrapingError):
    """URL doesn't point to job posting"""
    
class ScrapingTimeoutError(JobScrapingError):
    """Scraping took too long"""
```

Frontend-friendly messages:

```
❌ Error: This job board requires login. Please copy-paste the JD text.
❌ Error: URL doesn't appear to be a job posting. Please check the link.
❌ Error: Failed to scrape job posting after 3 retries.
```

## Cost Analysis

**Per Scrape**:

- HTML fetch: Free
- LLM call: ~15K tokens input @ $0.003/1K = $0.045
- Total: ~$0.05 per job posting

**Mitigation**:

- Caching: Same URL scraped once per 24 hours
- Batch optimization: 1 scrape → N resumes
- User control: Option to disable scraping (use raw HTML)

**Monthly estimate** (100 jobs, 3 resumes each):

- Without cache: 300 scrapes × $0.05 = $15
- With cache: 100 scrapes × $0.05 = $5

## Success Criteria

✅ Can scrape 5+ major job boards (LinkedIn, Indeed, Greenhouse, Lever, company sites)

✅ Extraction accuracy >90% for job_title and jd_text

✅ Clear error messages for paywalls and invalid URLs

✅ No breaking changes to existing functionality

✅ Scraping time <5 seconds per job

✅ Cost <$0.10 per job posting

## Testing Plan

1. **Unit Tests**: Mock LLM responses, test extraction logic
2. **Integration Tests**: Real URLs for each job board
3. **Error Tests**: Paywall URLs, invalid URLs, timeout scenarios
4. **Performance Tests**: Large HTML pages, token limits
5. **Regression Tests**: Ensure existing jd_text flow still works

## Documentation Updates

1. `docs/RESUME_PARSING.md` - Add job URL scraping section
2. `README.md` - Mention new capability
3. CLI help text - Document --jd-url usage
4. Error messages guide - Document scraping errors

## To-dos

- [ ] Implement core scraper in ops/job_board_scraper.py
- [ ] Add HTML cleaning and LLM extraction logic
- [ ] Add error classes to ops/parsing_errors.py (PaywallDetectedError, InvalidJobURLError, ScrapingTimeoutError)
- [ ] Integrate scraper into agents/jd_parser.py with use_scraper flag
- [ ] Update ops/input_builder.py to auto-detect role from jd_url
- [ ] Update scripts/parse_resume.py to make --role optional with --jd-url
- [ ] Implement caching layer in ops/job_cache.py (optional but recommended)
- [ ] Test with 5+ different job board URLs (LinkedIn, Indeed, Greenhouse, etc.)
- [ ] Add paywall detection logic
- [ ] Update documentation with scraping examples
- [ ] Add requirements: beautifulsoup4>=4.12.0
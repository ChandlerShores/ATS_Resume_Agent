<!-- 138c79eb-fd94-4e30-a147-047f6b169ee1 ff91f225-188f-4097-a62b-01270905471a -->
# Keyword Categorization Enhancement

## Problem

Current system treats all JD keywords equally, but:
- ✅ **Soft skills** (analytical thinking, adaptability) can be inferred from work
- ❌ **Hard tools** (Monday.com, Marketo) are factual claims - adding them is fabrication
- ✅ **Domain terms** (B2B healthcare, SaaS) provide context - safe to add

## Solution

Categorize keywords and apply different rules for each category.

## Implementation

### Phase 1: Update Schema

**File:** `schemas/models.py`

Update `JDSignals` model:

```python
class JDSignals(BaseModel):
    """Extracted signals from job description."""
    
    top_terms: List[str] = Field(default_factory=list, description="Prioritized keywords")
    weights: Dict[str, float] = Field(default_factory=dict, description="Term importance weights")
    synonyms: Dict[str, List[str]] = Field(default_factory=dict, description="Synonym map")
    themes: Dict[str, List[str]] = Field(default_factory=dict, description="Thematic groupings")
    
    # NEW: Categorized keywords
    soft_skills: List[str] = Field(default_factory=list, description="Transferable skills (analytical thinking, adaptability)")
    hard_tools: List[str] = Field(default_factory=list, description="Specific tools/platforms (Marketo, Salesforce)")
    domain_terms: List[str] = Field(default_factory=list, description="Industry/context terms (B2B healthcare, SaaS)")
```

### Phase 2: Update JD_PARSER

**File:** `agents/jd_parser.py`

Add categorization to extraction prompt:

```python
EXTRACTION_PROMPT = """Extract and categorize job description keywords.

Job Description:
{jd_text}

Return JSON with THREE CATEGORIES:

1. soft_skills: Transferable competencies that can be inferred from work
   Examples: analytical thinking, problem-solving, communication, adaptability, collaboration
   
2. hard_tools: Specific tools/platforms/technologies (factual claims)
   Examples: Marketo, Salesforce, Monday.com, Google Analytics, Figma, Tableau
   
3. domain_terms: Industry/context terminology
   Examples: B2B healthcare, SaaS, multi-channel campaigns, demand generation

{
  "soft_skills": ["analytical thinking", "adaptability", ...],
  "hard_tools": ["Marketo", "Google Analytics", ...],
  "domain_terms": ["B2B healthcare", "SaaS", ...]
}

Guidelines:
- If unsure, categorize conservatively (prefer hard_tool over soft_skill)
- Hard tools are verifiable facts - flag anything with a brand name or specific product
"""
```

Update `parse_jd()` to populate new fields.

### Phase 3: Update REWRITER Prompts

**File:** `agents/rewriter.py`

Modify `USER_PROMPT_TEMPLATE`:

```python
USER_PROMPT_TEMPLATE = """Rewrite this resume bullet to align with the target job description while preserving factual accuracy.

Original Bullet:
{bullet}

Target Role: {role}

JD KEYWORDS (use appropriately):

✅ SOFT SKILLS (ADD if the bullet demonstrates them):
{soft_skills}

❌ HARD TOOLS (NEVER add unless in original bullet):
{hard_tools}

✅ DOMAIN TERMS (ADD to provide context):
{domain_terms}

Metrics from THIS BULLET ONLY:
{metrics}

Extra Context:
{context}

REWRITING RULES:

1. SOFT SKILLS: If the work demonstrates a soft skill, weave it in naturally
   Example: "Synthesized 40+ research sessions" → "Applied analytical thinking to synthesize..."

2. HARD TOOLS: ONLY mention if in original bullet - adding them is fabrication
   Example: Original has "Figma" → Can keep "Figma"
   Example: Original has no tools → CANNOT add "Marketo" or "Monday.com"

3. DOMAIN TERMS: Add to provide context/framing
   Example: "Built dashboard" → "Built B2B healthcare dashboard"

Generate {num_variants} variants (≤{max_words} words each).

Return JSON with variants and rationale.

REMEMBER: Soft skills = infer if demonstrated. Hard tools = NEVER fabricate.
"""
```

Update `rewrite_bullet()` to format categorized terms:

```python
def rewrite_bullet(self, bullet, role, jd_signals, metrics, extra_context="", max_words=30, num_variants=2):
    # Format categorized keywords
    soft_skills_str = ", ".join(jd_signals.soft_skills[:8])
    hard_tools_str = ", ".join(jd_signals.hard_tools[:8])
    domain_terms_str = ", ".join(jd_signals.domain_terms[:8])
    
    metrics_str = "\n".join([f"- {k}: {v}" for k, v in metrics.items()]) if metrics else "None"
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        bullet=bullet,
        role=role,
        soft_skills=soft_skills_str,
        hard_tools=hard_tools_str,
        domain_terms=domain_terms_str,
        metrics=metrics_str,
        context=extra_context or "None",
        num_variants=num_variants,
        max_words=max_words
    )
    # ... rest of method
```

### Phase 4: Enhance VALIDATOR

**File:** `agents/validator.py`

Update `_check_factual_consistency_llm()`:

```python
def _check_factual_consistency_llm(self, original: str, revised: str, jd_signals=None) -> List[str]:
    """Check factual consistency with awareness of hard tools."""
    
    hard_tools_context = ""
    if jd_signals and jd_signals.hard_tools:
        hard_tools_context = f"\n\nKNOWN HARD TOOLS from JD: {', '.join(jd_signals.hard_tools)}\n" \
                           f"These are factual claims - flag if added to revised but not in original."
    
    consistency_prompt = f"""Compare resume bullets for factual consistency.

Original: "{original}"
Revised:  "{revised}"{hard_tools_context}

Check for FABRICATION:

1. HARD TOOLS: Specific platforms/tools in revised but NOT in original
   Examples: Marketo, Salesforce, Monday.com, Google Analytics, Figma
   
2. ACTIVITY MISMATCH: Core activity changed (design → marketing)

3. BORROWED METRICS: Numbers in revised not in original

4. INVENTED FACTS: New companies, titles, achievements

Return JSON:
{{
  "is_consistent": true/false,
  "violations": [
    {{"type": "hard_tool_fabrication", "detail": "Added Marketo not in original"}},
    ...
  ]
}}
"""
    # ... rest of method
```

Update `validate()` signature to accept `jd_signals`.

Update state machine `_validate()` to pass `jd_signals` to validator.

### Phase 5: Update State Machine

**File:** `orchestrator/state_machine.py`

Pass `jd_signals` to validator in `_validate()`:

```python
def _validate(self, state: JobState) -> State:
    # ... existing code ...
    
    for original, variants_list in state.raw_rewrites.items():
        # ... existing code ...
        validation_result, corrected = self.validator.validate(
            original=original,
            revised=variant.text,
            jd_signals=state.jd_signals  # NEW: pass JD signals
        )
```

## Testing Strategy

### Test 1: Soft Skills Inference
```
Original: "Ran 40+ usability sessions and synthesized findings"
Expected: Can add "analytical thinking" (demonstrated by synthesis work)
Should NOT add: "Monday.com" or "Marketo" (hard tools not in original)
```

### Test 2: Hard Tool Protection
```
Original: "Built design system in Figma"
Expected: Can keep "Figma" (in original)
Should NOT add: "Sketch" or "Adobe CC" (not in original)
```

### Test 3: Domain Terms
```
Original: "Led dashboard redesign, increasing usage by 34%"
Expected: Can add "B2B healthcare" (contextual framing)
Should NOT add: "Google Analytics" (hard tool not in original)
```

### Test 4: Re-run Avery's Resume
```bash
python -m orchestrator.state_machine \
  --input out/avery_phreesia_input.json \
  --out out/avery_phreesia_categorized.json
```

Expected improvements:
- Soft skills like "analytical thinking" added where work demonstrates them
- NO hard tools (Marketo, Monday.com) added
- Domain terms (B2B healthcare) used for context

## Success Criteria

1. ✅ JD keywords categorized into 3 buckets
2. ✅ Soft skills inferred and added when work demonstrates them
3. ✅ Hard tools NEVER added unless in original
4. ✅ Domain terms used for contextual framing
5. ✅ Validator flags hard tool fabrications
6. ✅ Avery's bullets get "analytical thinking" but NOT "Marketo"

## Files Modified

1. `schemas/models.py` - Add categorization fields to JDSignals
2. `agents/jd_parser.py` - Categorize keywords during extraction
3. `agents/rewriter.py` - Use categorized keywords in prompts
4. `agents/validator.py` - Check for hard tool fabrication
5. `orchestrator/state_machine.py` - Pass jd_signals to validator

## Implementation Order

1. Update JDSignals schema
2. Update JD_PARSER extraction prompt + logic
3. Update REWRITER prompts with categorized keywords
4. Enhance VALIDATOR to detect hard tool fabrication
5. Update state machine to pass jd_signals to validator
6. Test with Avery's resume
7. Verify soft skills added, hard tools NOT added

## Key Insight

**Not all JD keywords are equal:**
- Soft skills = safe to infer (if work demonstrates them)
- Hard tools = never fabricate (verifiable facts)
- Domain terms = safe to add (contextual framing)

This makes the system intelligent about which keywords enhance vs. fabricate.


### To-dos

- [ ] Add soft_skills, hard_tools, domain_terms fields to JDSignals in schemas/models.py
- [ ] Add categorization logic to JD_PARSER extraction prompt
- [ ] Update parse_jd() to populate categorized fields
- [ ] Modify USER_PROMPT_TEMPLATE with categorized keywords and rules
- [ ] Update rewrite_bullet() to format categorized terms
- [ ] Update _check_factual_consistency_llm() to check hard tools
- [ ] Update validate() to accept jd_signals parameter
- [ ] Pass jd_signals to validator in state machine
- [ ] Test with Avery's resume - verify soft skills added, hard tools NOT added
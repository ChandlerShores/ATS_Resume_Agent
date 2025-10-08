# Frontend Integration Prompt for AI Assistant

**Use this prompt with your frontend AI assistant (Cursor, Claude, etc.) to integrate the ATS Resume Agent API into your Next.js app.**

---

## Copy this entire section and paste it to your frontend AI:

---

# Task: Integrate ATS Resume Agent API into Next.js App

## Context
I have a working **ATS Resume Agent API** deployed at a URL (I'll provide it). This API takes resume bullets and a job description, then uses AI to rewrite the bullets to be more ATS-friendly and aligned with the job requirements.

## API Overview

### Base URL
```
https://your-api-url.onrender.com
```
(Replace with actual URL after deployment)

### Key Endpoint
**POST** `/api/test/process-sync`

### Request Format
```typescript
{
  role: string;              // Job title (e.g., "Senior Software Engineer")
  jd_text: string;           // Full job description text
  bullets: string[];         // Array of resume bullets to revise
  settings: {
    tone?: string;           // Default: "concise"
    max_len?: number;        // Default: 30 (max words per bullet)
    variants?: number;       // Default: 2 (number of variants per bullet)
  }
}
```

### Response Format
```typescript
{
  job_id: string;
  summary: {
    role: string;
    top_terms: string[];     // Key terms extracted from JD
    coverage: {
      hit: string[];         // Terms that appear in revised bullets
      miss: string[];        // Terms missing from bullets
    }
  };
  results: Array<{
    original: string;        // Original bullet
    revised: string[];       // Array of revised variants (usually 2)
    scores: {
      relevance: number;     // 0-100
      impact: number;        // 0-100
      clarity: number;       // 0-100
    };
    notes: string;           // Explanation of changes
    diff: {
      removed: string[];
      added_terms: string[];
    }
  }>;
  red_flags: string[];       // Warnings (e.g., fabricated details)
  logs: Array<{              // Execution logs
    ts: string;
    level: string;
    stage: string;
    msg: string;
    job_id: string;
  }>;
}
```

## What I Need

### 1. Environment Setup
Create/update `.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-api-url.onrender.com
```

### 2. API Client/Hook
Create a React hook or API client that:
- Handles POST requests to the API
- Manages loading states
- Handles errors gracefully
- Shows progress (the API can take 30-60 seconds)
- Provides clear error messages to users

### 3. UI Components
I need components for:

**Input Section:**
- Text input for **Job Title/Role**
- Textarea for **Job Description** (large, supports paste)
- Textarea for **Resume Bullets** (one per line or array input)
- Optional: Settings controls (max words, number of variants)
- Submit button with loading state

**Output Section:**
- Display each original bullet with its revised variants
- Show scores visually (progress bars or badges)
- Highlight which JD terms were covered
- Show warnings/red flags if any
- Allow user to copy revised bullets
- Show before/after comparison clearly

**Loading State:**
- Progress indicator (30-60 second wait)
- Show which stage is running (parsing JD, rewriting, scoring, validating)
- Maybe use the `logs` array from response to show real-time progress

**Error Handling:**
- Network errors
- API errors
- Timeout handling
- Clear user-friendly messages

### 4. Example API Call Code
```typescript
async function reviseBullets(
  role: string,
  jdText: string,
  bullets: string[]
) {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/test/process-sync`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        jd_text: jdText,
        bullets,
        settings: {
          tone: 'concise',
          max_len: 30,
          variants: 2
        }
      })
    }
  );
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return response.json();
}
```

### 5. UX Considerations

**Important:**
- The API takes 30-60 seconds to respond (it's calling OpenAI/Anthropic)
- On Render free tier, there's a 30s cold start if inactive
- Show clear loading indicators
- Consider adding a "test with sample data" button
- Allow users to edit revised bullets before using them
- Provide a "copy all" function for revised bullets

### 6. Error Scenarios to Handle

1. **Cold Start (Render free tier)**: 
   - Total wait: 30s (cold start) + 60s (processing) = 90s
   - Show: "API is warming up... this may take up to 90 seconds on first request"

2. **Rate Limiting**:
   - Show: "Too many requests. Please wait a moment and try again."

3. **Invalid Input**:
   - Missing role/bullets/JD
   - Show: Validation errors before calling API

4. **API Timeout**:
   - If > 2 minutes, show error and retry option

### 7. Nice-to-Have Features

- Save/export revised bullets
- Compare original vs revised side-by-side
- Filter by score (show only high-scoring variants)
- Copy individual bullets or all at once
- Dark mode support
- Mobile responsive
- Keyboard shortcuts (Ctrl+Enter to submit)

### 8. Testing Data

Use this sample data to test:

**Role:**
```
Senior Software Engineer
```

**Job Description:**
```
We are seeking a Senior Software Engineer with strong Python and FastAPI experience.
The ideal candidate will have:
- 5+ years of Python development
- Experience with RESTful APIs
- Cloud platform experience (AWS/GCP)
- Strong understanding of microservices
- CI/CD pipeline experience
```

**Resume Bullets:**
```
Built REST APIs using Python
Deployed applications to cloud infrastructure
Created automated testing pipelines
```

**Expected Response Time:** 30-60 seconds

## Technical Stack Preferences

- **Framework**: Next.js 14+ (App Router or Pages Router - you choose)
- **Styling**: Tailwind CSS (if available) or your preferred method
- **State Management**: React hooks (useState, useEffect) or your preference
- **HTTP Client**: fetch API (built-in) or axios

## Design Guidelines

- Clean, professional UI
- Clear visual hierarchy (input → loading → results)
- Use color coding for scores:
  - Green: 80-100
  - Yellow: 60-79
  - Red: <60
- Make it obvious which bullets are original vs revised
- Provide clear CTAs ("Copy", "Use This Variant", etc.)

## Additional Context

**About the API:**
- It uses AI to analyze job descriptions
- Rewrites resume bullets to match JD keywords
- Scores bullets on relevance, impact, and clarity
- Flags potential issues (fabricated details, vague language)
- Generates 2 variants per bullet by default

**Limitations:**
- Free tier has cold starts (~30s if inactive)
- Processing takes 30-60s per request
- Not suitable for real-time/instant results
- Best for batch processing 3-10 bullets at once

## Success Criteria

The integration is successful when:
1. ✅ Users can input job details and resume bullets
2. ✅ API calls work reliably with proper error handling
3. ✅ Loading states are clear (30-60s wait is manageable)
4. ✅ Results are displayed clearly and are easy to copy/use
5. ✅ Edge cases are handled (cold start, errors, timeouts)
6. ✅ UI is intuitive and professional-looking

## Questions to Ask Me

If you need clarification:
1. What's the actual deployed API URL?
2. Do you want this as a new page or component?
3. Should users be able to save results to a database?
4. Do you want authentication/user accounts?
5. Should there be a limit on number of bullets per request?

---

**Now please help me integrate this API into my Next.js frontend with clean, production-ready code.**




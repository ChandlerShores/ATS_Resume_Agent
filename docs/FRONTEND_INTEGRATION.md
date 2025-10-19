# Frontend Integration Guide

## Overview

This guide explains how to integrate the ATS Resume Agent API into a frontend application (React, Next.js, Vue, etc.). The API is designed to be easily consumable via REST endpoints with clear request/response formats.

## API Endpoint

### Base URL
```
https://your-app.onrender.com
```
(Replace with your actual deployed URL)

### Main Endpoint
**POST** `/api/test/process-sync`

**Purpose**: Synchronously processes resume bullets and returns revised variants with scoring.

**Timeout**: 60-120 seconds (LLM processing is slow)

---

## Request Format

### TypeScript Interface
```typescript
interface ATSRequest {
  role: string;              // Job title (e.g., "Senior Software Engineer")
  jd_text: string;           // Full job description text
  bullets: string[];         // Array of resume bullets to revise
  extra_context?: string;    // Optional additional context
  settings?: {
    tone?: string;           // Default: "concise"
    max_len?: number;        // Default: 30 (max words per bullet)
    variants?: number;       // Default: 2 (number of variants per bullet)
  };
}
```

### Example Request
```json
{
  "role": "Senior Software Engineer",
  "jd_text": "We are seeking a Senior Engineer with Python, FastAPI, and AWS experience...",
  "bullets": [
    "Built REST APIs using Python",
    "Deployed applications to cloud infrastructure",
    "Created automated testing pipelines"
  ],
  "settings": {
    "max_len": 30,
    "variants": 2
  }
}
```

---

## Response Format

### TypeScript Interface
```typescript
interface ATSResponse {
  job_id: string;
  summary: {
    role: string;
    top_terms: string[];     // Key terms extracted from JD
    coverage: {
      hit: string[];         // Terms that appear in revised bullets
      miss: string[];        // Terms missing from bullets
    };
  };
  results: Array<{
    original: string;        // Original bullet
    revised: string[];       // Array of revised variants (usually 2)
    scores: {
      relevance: number;     // 0-100 (JD alignment)
      impact: number;        // 0-100 (outcomes/achievements)
      clarity: number;       // 0-100 (brevity/concreteness)
    };
    notes: string;           // Explanation of changes
    diff: {
      removed: string[];
      added_terms: string[];
    };
  }>;
  red_flags: string[];       // Warnings (e.g., fabricated details, PII)
  logs: Array<{              // Execution logs (for debugging)
    ts: string;
    level: string;           // "info", "warn", "error"
    stage: string;
    msg: string;
    job_id: string;
  }>;
}
```

### Example Response
```json
{
  "job_id": "01HX5PQRS...",
  "summary": {
    "role": "Senior Software Engineer",
    "top_terms": ["Python", "FastAPI", "AWS", "REST APIs", "Cloud"],
    "coverage": {
      "hit": ["Python", "FastAPI", "REST APIs"],
      "miss": ["AWS", "Cloud"]
    }
  },
  "results": [
    {
      "original": "Built REST APIs using Python",
      "revised": [
        "Architected scalable REST APIs using Python and FastAPI, optimizing performance for high-traffic applications",
        "Developed cloud-native Python REST APIs with FastAPI, implementing best practices for security and scalability"
      ],
      "scores": {
        "relevance": 92,
        "impact": 85,
        "clarity": 95
      },
      "notes": "Enhanced with framework name (FastAPI) and impact-focused language while preserving factual accuracy",
      "diff": {
        "removed": [],
        "added_terms": ["FastAPI", "scalable", "cloud-native"]
      }
    }
  ],
  "red_flags": [],
  "logs": [...]
}
```

---

## Integration Examples

### Next.js 14+ (App Router)

#### 1. Server-Side API Proxy (Recommended)

**File**: `app/api/ats/process-resume/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Call external API
    const response = await fetch(
      `${process.env.ATS_API_URL}/api/test/process-sync`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(120000), // 2 minute timeout
      }
    );
    
    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: 'API request failed', details: error },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error: any) {
    if (error.name === 'TimeoutError') {
      return NextResponse.json(
        { error: 'Request timeout - API is processing' },
        { status: 504 }
      );
    }
    
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

**Environment Variable**: `.env.local`
```bash
ATS_API_URL=https://your-app.onrender.com
```

#### 2. Client Component

**File**: `components/ATSOptimizer.tsx`

```typescript
'use client';

import { useState } from 'react';

interface ATSResult {
  original: string;
  revised: string[];
  scores: { relevance: number; impact: number; clarity: number };
  notes: string;
}

export function ATSOptimizer() {
  const [role, setRole] = useState('');
  const [jdText, setJdText] = useState('');
  const [bullets, setBullets] = useState<string[]>([]);
  const [results, setResults] = useState<ATSResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/ats/process-resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role,
          jd_text: jdText,
          bullets,
          settings: { max_len: 30, variants: 2 }
        })
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      setResults(data.results);
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1>ATS Resume Optimizer</h1>
      
      {/* Input Form */}
      <div className="space-y-4">
        <input
          type="text"
          placeholder="Job Title (e.g., Senior Software Engineer)"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full p-2 border rounded"
        />
        
        <textarea
          placeholder="Paste job description here..."
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          className="w-full p-2 border rounded h-32"
        />
        
        <textarea
          placeholder="Paste resume bullets (one per line)..."
          onChange={(e) => setBullets(e.target.value.split('\n').filter(b => b.trim()))}
          className="w-full p-2 border rounded h-32"
        />
        
        <button
          onClick={handleSubmit}
          disabled={loading || !role || !jdText || bullets.length === 0}
          className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Processing (30-90s)...' : 'Optimize Resume'}
        </button>
      </div>
      
      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">
          {error}
        </div>
      )}
      
      {/* Results Display */}
      {results && (
        <div className="mt-8 space-y-6">
          {results.map((result, idx) => (
            <div key={idx} className="border rounded p-4">
              <div className="text-sm text-gray-600 mb-2">Original:</div>
              <div className="mb-4">{result.original}</div>
              
              <div className="text-sm text-gray-600 mb-2">Revised Variants:</div>
              {result.revised.map((variant, vIdx) => (
                <div key={vIdx} className="mb-2 p-2 bg-blue-50 rounded">
                  {variant}
                </div>
              ))}
              
              <div className="mt-4 flex gap-4 text-sm">
                <span>Relevance: {result.scores.relevance}/100</span>
                <span>Impact: {result.scores.impact}/100</span>
                <span>Clarity: {result.scores.clarity}/100</span>
              </div>
              
              <div className="mt-2 text-sm text-gray-600">{result.notes}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### React (Vite/CRA)

```typescript
import { useState } from 'react';

function ATSOptimizer() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (formData) => {
    setLoading(true);
    
    try {
      const response = await fetch(
        'https://your-app.onrender.com/api/test/process-sync',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData),
        }
      );
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('API error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    // UI similar to Next.js example
  );
}
```

---

### Vue 3

```vue
<script setup lang="ts">
import { ref } from 'vue';

const role = ref('');
const jdText = ref('');
const bullets = ref<string[]>([]);
const results = ref(null);
const loading = ref(false);

async function handleSubmit() {
  loading.value = true;
  
  try {
    const response = await fetch(
      'https://your-app.onrender.com/api/test/process-sync',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: role.value,
          jd_text: jdText.value,
          bullets: bullets.value,
          settings: { max_len: 30, variants: 2 }
        })
      }
    );
    
    results.value = await response.json();
  } catch (error) {
    console.error('API error:', error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="ats-optimizer">
    <!-- UI components -->
  </div>
</template>
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Handling |
|------|---------|----------|
| `200` | Success | Parse and display results |
| `400` | Bad Request | Show validation errors |
| `422` | Validation Error | Display specific field errors |
| `429` | Rate Limit | Ask user to wait |
| `500` | Server Error | Show generic error message |
| `502` | Bad Gateway | API unavailable (cold start) |
| `504` | Gateway Timeout | Processing took too long |

### Error Response Format
```json
{
  "detail": "Validation error: bullets field required"
}
```

### Recommended Error Messages

```typescript
const getErrorMessage = (status: number): string => {
  switch (status) {
    case 400:
      return 'Invalid input. Please check your form and try again.';
    case 422:
      return 'Validation error. Ensure all required fields are filled.';
    case 429:
      return 'Rate limit exceeded. Please wait a minute and try again.';
    case 502:
      return 'API is waking up (cold start). Please retry in 30 seconds.';
    case 504:
      return 'Request timeout. Try with fewer bullets or simpler job description.';
    default:
      return 'An error occurred. Please try again later.';
  }
};
```

---

## Best Practices

### 1. Loading States
- **Show progress**: API can take 30-90 seconds
- **Set expectations**: Display "Processing (30-90s)..." message
- **Use spinners**: Visual feedback during wait

### 2. Input Validation
- **Max bullets**: Limit to 20 bullets per request
- **Required fields**: Validate role, jd_text, and bullets before submission
- **Length limits**: JD text max 50KB, each bullet max 1KB

### 3. Timeout Handling
- **Set timeouts**: 120 seconds for requests
- **Retry logic**: Allow users to retry after timeout
- **Fallback**: Show demo data or error message

### 4. CORS Configuration
If calling API directly from browser (not recommended):
```typescript
// API needs to allow your domain in CORS
// Contact API maintainer to add your domain to ALLOWED_ORIGINS
```

### 5. Security
- **Use proxy**: Server-side API routes hide credentials
- **No API keys in frontend**: Never expose API keys in client code
- **Sanitize input**: Validate/sanitize user input before sending

---

## Performance Optimization

### 1. Cold Start Mitigation
Render free tier sleeps after 15 minutes:
- **Warm-up request**: Send a lightweight request before user submits
- **Status page**: Show "API warming up" message
- **Retry button**: Allow easy retry after cold start

### 2. Caching
```typescript
// Cache results by job description + bullets hash
const cacheKey = btoa(JSON.stringify({ role, jd_text, bullets }));
const cached = localStorage.getItem(cacheKey);
if (cached) {
  return JSON.parse(cached);
}
```

### 3. Progressive Enhancement
```typescript
// Show partial results as they stream (future feature)
// Current API returns complete results only
```

---

## Advanced Features

### 1. Score Visualization
```typescript
function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-600';
  if (score >= 70) return 'text-yellow-600';
  return 'text-red-600';
}
```

### 2. Copy to Clipboard
```typescript
async function copyBullet(text: string) {
  await navigator.clipboard.writeText(text);
  // Show success toast
}
```

### 3. Bulk Export
```typescript
function exportAllBullets(results: ATSResult[]) {
  const bullets = results
    .map(r => r.revised[0]) // Use first variant
    .join('\n');
  
  const blob = new Blob([bullets], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  // Trigger download
}
```

---

## Testing

### Sample Test Data
```json
{
  "role": "Software Engineer",
  "jd_text": "Looking for a skilled developer with Python and FastAPI experience. Must have cloud deployment knowledge and strong communication skills.",
  "bullets": [
    "Built web applications using Python",
    "Deployed services to cloud infrastructure",
    "Collaborated with cross-functional teams"
  ],
  "settings": {
    "max_len": 30,
    "variants": 2
  }
}
```

### Expected Response Time
- **Typical**: 30-60 seconds
- **Cold start**: 60-120 seconds
- **Timeout**: After 120 seconds

---

## Support & Troubleshooting

### API Health Check
```bash
curl https://your-app.onrender.com/health
```

### API Documentation
Interactive docs available at:
```
https://your-app.onrender.com/docs
```

### Common Issues

**Issue**: 502 Bad Gateway
**Solution**: API is on free tier and sleeping. Wait 30s and retry.

**Issue**: 504 Gateway Timeout
**Solution**: Request too complex. Reduce bullets or simplify JD.

**Issue**: 429 Rate Limit
**Solution**: Wait 1 minute between requests (5 requests/min limit).

**Issue**: CORS Error
**Solution**: Use server-side proxy or contact API maintainer.

---

## Example Projects

Full working examples available in documentation repository:
- Next.js 14 (App Router)
- React + Vite
- Vue 3
- Plain HTML/JavaScript

---

## API Changelog

- **v1.0.0**: Initial release
  - Synchronous processing endpoint
  - 2 variants per bullet
  - Scoring and coverage analysis
  - Red flag detection


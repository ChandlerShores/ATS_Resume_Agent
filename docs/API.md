# ATS Resume Agent API Documentation

## Overview

The ATS Resume Agent API is a B2B service designed for enterprise integration with ATS/CRM systems. It provides bulk resume processing capabilities to rewrite multiple candidates' resume bullets against a single job description.

## Base URL

```
https://your-domain.com/api
```

## Authentication

Currently, the API uses IP-based rate limiting. For production deployments, consider implementing API key authentication or OAuth2 client credentials.

## Rate Limiting

- **Bulk Processing**: 5 requests per minute per IP
- **Health Check**: 100 requests per minute per IP
- **Other Endpoints**: 5 requests per minute per IP

## Bulk Processing Endpoints

### POST /api/bulk/process

Process multiple candidates' resumes against a single job description.

**Request Body:**
```json
{
  "job_description": "Software Engineer role description...",
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "bullets": [
        "Developed web applications using React and Node.js",
        "Led team of 5 developers on agile projects",
        "Improved system performance by 40% through optimization"
      ]
    },
    {
      "candidate_id": "candidate_002", 
      "bullets": [
        "Managed database operations and data analysis",
        "Collaborated with cross-functional teams",
        "Implemented CI/CD pipelines for deployment"
      ]
    }
  ],
  "settings": {
    "max_len": 30,
    "variants": 1,
    "tone": "concise"
  }
}
```

**Request Schema:**
- `job_description` (string, required): Job description text (max 50KB)
- `candidates` (array, required): List of candidates (1-50 candidates)
  - `candidate_id` (string, required): Unique candidate identifier (max 100 chars)
  - `bullets` (array, required): Resume bullets (1-20 bullets, max 1KB each)
- `settings` (object, optional): Processing settings
  - `max_len` (integer): Max words per bullet (1-100, default 30)
  - `variants` (integer): Number of variants (1-3, default 1)
  - `tone` (string): Writing tone (default "concise")

**Response:**
```json
{
  "job_id": "01HZ123456789ABCDEFGHIJKLMN",
  "status": "processing",
  "total_candidates": 2,
  "processed_candidates": 0,
  "candidates": []
}
```

**Status Codes:**
- `200`: Success - Processing started
- `400`: Bad Request - Invalid input or suspicious content
- `429`: Too Many Requests - Rate limit exceeded or cost limit reached

### GET /api/bulk/status/{job_id}

Get the current status of a bulk processing job.

**Response:**
```json
{
  "job_id": "01HZ123456789ABCDEFGHIJKLMN",
  "status": "processing",
  "total_candidates": 2,
  "processed_candidates": 1,
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "status": "completed",
      "results": [
        {
          "original": "Developed web applications using React and Node.js",
          "revised": "Built scalable web applications using React and Node.js, serving 10K+ users",
          "scores": {
            "relevance": 0.85,
            "impact": 0.90,
            "clarity": 0.88
          },
          "coverage": {
            "jd_terms_matched": ["React", "Node.js", "web applications"],
            "coverage_score": 0.75
          }
        }
      ],
      "coverage": {
        "overall_score": 0.75,
        "top_terms": ["React", "Node.js", "JavaScript"],
        "missing_terms": ["TypeScript", "AWS"]
      },
      "error_message": null
    },
    {
      "candidate_id": "candidate_002",
      "status": "processing",
      "results": [],
      "coverage": null,
      "error_message": null
    }
  ],
  "error_message": null
}
```

**Status Codes:**
- `200`: Success
- `404`: Job not found

### GET /api/bulk/results/{job_id}

Get the final results of a completed bulk processing job.

**Response:**
Same format as status endpoint, but only returns when `status` is `completed` or `failed`.

**Status Codes:**
- `200`: Success - Results available
- `202`: Accepted - Job still processing
- `404`: Job not found

## Legacy Endpoints

### POST /api/resume/process

Process a single resume (legacy endpoint for backward compatibility).

**Request Body:**
```json
{
  "role": "Software Engineer",
  "jd_text": "Job description text...",
  "bullets": ["bullet1", "bullet2", "bullet3"],
  "extra_context": "Additional context",
  "settings": {
    "max_len": 30,
    "variants": 1
  }
}
```

### GET /api/resume/status/{job_id}
### GET /api/resume/result/{job_id}
### DELETE /api/resume/{job_id}

Standard job management endpoints for single resume processing.

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

**Rate Limiting:**
```json
{
  "detail": "Rate limit exceeded: 6/5 requests per minute"
}
```

**Cost Limit:**
```json
{
  "detail": "Daily cost limit exceeded"
}
```

**Invalid Input:**
```json
{
  "detail": "Suspicious input detected"
}
```

**Job Not Found:**
```json
{
  "detail": "Job not found"
}
```

## Integration Examples

### Python Example

```python
import requests
import time

# Submit bulk processing job
response = requests.post(
    "https://your-domain.com/api/bulk/process",
    json={
        "job_description": "Software Engineer role...",
        "candidates": [
            {
                "candidate_id": "candidate_001",
                "bullets": ["bullet1", "bullet2"]
            }
        ]
    }
)

job_id = response.json()["job_id"]

# Poll for completion
while True:
    status_response = requests.get(f"https://your-domain.com/api/bulk/status/{job_id}")
    status_data = status_response.json()
    
    if status_data["status"] == "completed":
        break
    elif status_data["status"] == "failed":
        print(f"Job failed: {status_data['error_message']}")
        break
    
    time.sleep(5)  # Wait 5 seconds before next poll

# Get final results
results_response = requests.get(f"https://your-domain.com/api/bulk/results/{job_id}")
results = results_response.json()

for candidate in results["candidates"]:
    print(f"Candidate {candidate['candidate_id']}: {candidate['status']}")
    for result in candidate["results"]:
        print(f"  Original: {result['original']}")
        print(f"  Revised: {result['revised']}")
```

### JavaScript Example

```javascript
async function processBulkResumes(jobDescription, candidates) {
    // Submit job
    const response = await fetch('/api/bulk/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            job_description: jobDescription,
            candidates: candidates
        })
    });
    
    const { job_id } = await response.json();
    
    // Poll for completion
    while (true) {
        const statusResponse = await fetch(`/api/bulk/status/${job_id}`);
        const statusData = await statusResponse.json();
        
        if (statusData.status === 'completed') {
            break;
        } else if (statusData.status === 'failed') {
            throw new Error(`Job failed: ${statusData.error_message}`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
    
    // Get results
    const resultsResponse = await fetch(`/api/bulk/results/${job_id}`);
    return await resultsResponse.json();
}
```

## Best Practices

### Performance Optimization

1. **Batch Size**: Process 10-20 candidates per request for optimal performance
2. **Polling Interval**: Poll status every 5-10 seconds to avoid overwhelming the server
3. **Timeout Handling**: Implement reasonable timeouts (5-10 minutes) for job completion

### Error Handling

1. **Retry Logic**: Implement exponential backoff for transient failures
2. **Graceful Degradation**: Handle individual candidate failures without failing the entire batch
3. **Logging**: Log all API interactions for debugging and monitoring

### Security

1. **Input Validation**: Validate all input data before sending to the API
2. **Rate Limiting**: Respect rate limits and implement client-side throttling
3. **Sensitive Data**: Avoid sending PII in job descriptions or candidate data

## Monitoring and Observability

### Health Check

```bash
curl https://your-domain.com/health
```

Returns system status, cost usage, and security metrics.

### Logging

The API provides structured JSON logs with the following fields:
- `ts`: Timestamp
- `level`: Log level (info, warn, error)
- `stage`: Processing stage
- `msg`: Log message
- `job_id`: Job identifier (when applicable)

## Support

For technical support or questions about the API, please contact your system administrator or refer to the main README documentation.

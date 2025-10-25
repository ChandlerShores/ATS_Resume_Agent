# ATS Resume Optimization API

**AI-powered resume bullet optimization for ATS systems**

Transform resume bullets to match job descriptions and improve ATS compatibility using advanced AI technology.

---

## 🚀 Quick Start

### 1. Get Your API Key
Contact us to receive your API key for accessing the service.

### 2. Process Resumes
```bash
curl -X POST https://your-api-domain.com/api/bulk/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_your_api_key" \
  -d '{
    "job_description": "Senior Software Engineer with Python experience...",
    "candidates": [
      {
        "candidate_id": "candidate_001",
        "bullets": [
          "Built web applications using Python",
          "Led team of 5 developers"
        ]
      }
    ],
    "settings": {
      "tone": "professional",
      "max_len": 30,
      "variants": 1
    }
  }'
```

### 3. Get Results
```bash
curl -H "X-API-Key: sk_live_your_api_key" \
  https://your-api-domain.com/api/bulk/results/job_id_here
```

---

## 📋 API Endpoints

### Bulk Processing (Recommended)
**`POST /api/bulk/process`** - Process multiple candidates against one job description

**Request Body:**
```json
{
  "job_description": "Job description text...",
  "candidates": [
    {
      "candidate_id": "unique_id",
      "bullets": ["bullet 1", "bullet 2", "bullet 3"]
    }
  ],
  "settings": {
    "tone": "professional",
    "max_len": 30,
    "variants": 1
  }
}
```

**Response:**
```json
{
  "job_id": "01HXYZ123ABC",
  "status": "processing",
  "total_candidates": 1,
  "processed_candidates": 0,
  "candidates": []
}
```

### Single Resume Processing
**`POST /api/resume/process`** - Process one resume (form data)

**Form Fields:**
- `role`: Job title
- `jd_text`: Job description
- `resume_text`: Resume bullets (one per line)
- `extra_context`: Additional context (optional)

### Check Job Status
**`GET /api/bulk/status/{job_id}`** - Get processing status

### Get Results
**`GET /api/bulk/results/{job_id}`** - Retrieve processed results

### Health Check
**`GET /health`** - Service status and statistics

---

## 🔧 Settings Options

| Setting | Description | Options | Default |
|---------|-------------|---------|---------|
| `tone` | Writing style | `professional`, `casual`, `technical` | `professional` |
| `max_len` | Maximum bullet length | `20-50` characters | `30` |
| `variants` | Number of alternatives | `1-3` | `1` |

---

## 📊 Response Format

### Successful Processing
```json
{
  "job_id": "01HXYZ123ABC",
  "status": "completed",
  "total_candidates": 1,
  "processed_candidates": 1,
  "candidates": [
    {
      "candidate_id": "candidate_001",
      "status": "completed",
      "original_bullets": ["Built web applications using Python"],
      "revised_bullets": ["Developed scalable web applications using Python and Django"],
      "scores": [0.85],
      "coverage": {
        "hit": ["Python", "web applications"],
        "miss": ["Django", "scalable"]
      }
    }
  ]
}
```

### Error Responses
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## 🔐 Authentication

All API requests require authentication via API key:

```bash
-H "X-API-Key: sk_live_your_api_key"
```

**API Key Format:** `sk_live_` followed by your unique key

---

## ⚡ Rate Limits

- **Bulk Processing:** 5 requests per minute
- **Single Resume:** 5 requests per minute
- **Status/Results:** 100 requests per minute
- **Health Check:** 100 requests per minute

---

## 🛠️ Integration Examples

### Python
```python
import requests

# Process resumes
response = requests.post(
    "https://your-api-domain.com/api/bulk/process",
    headers={"X-API-Key": "sk_live_your_api_key"},
    json={
        "job_description": "Senior Python Developer...",
        "candidates": [
            {
                "candidate_id": "candidate_001",
                "bullets": ["Built Python applications", "Led development team"]
            }
        ],
        "settings": {"tone": "professional", "max_len": 30}
    }
)

job_id = response.json()["job_id"]

# Get results
results = requests.get(
    f"https://your-api-domain.com/api/bulk/results/{job_id}",
    headers={"X-API-Key": "sk_live_your_api_key"}
)
```

### JavaScript/Node.js
```javascript
const response = await fetch('https://your-api-domain.com/api/bulk/process', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'sk_live_your_api_key'
  },
  body: JSON.stringify({
    job_description: 'Senior Python Developer...',
    candidates: [{
      candidate_id: 'candidate_001',
      bullets: ['Built Python applications', 'Led development team']
    }],
    settings: { tone: 'professional', max_len: 30 }
  })
});

const { job_id } = await response.json();
```

---

## 📈 Usage Tracking

We track your API usage for billing purposes:
- **Requests:** Number of API calls
- **Bullets:** Total resume bullets processed
- **Daily Limits:** Automatic usage monitoring

Check your usage via the `/health` endpoint.

---

## 🚨 Error Handling

### Common HTTP Status Codes
- **200:** Success
- **400:** Bad Request (invalid input)
- **401:** Unauthorized (invalid API key)
- **404:** Not Found (job doesn't exist)
- **413:** Request Too Large (exceeds 10MB limit)
- **429:** Rate Limited (too many requests)
- **500:** Internal Server Error

### Retry Logic
- Implement exponential backoff for 429 errors
- Retry failed requests up to 3 times
- Check job status before assuming completion

---

## 🔍 Best Practices

### Input Quality
- **Job Descriptions:** Use complete, detailed job postings
- **Resume Bullets:** Provide clear, specific achievements
- **Bullet Length:** Keep original bullets under 100 characters

### Performance
- **Batch Processing:** Use bulk endpoint for multiple candidates
- **Async Processing:** Jobs run in background - poll for completion
- **Caching:** Cache results to avoid reprocessing

### Security
- **API Keys:** Keep your API key secure and private
- **HTTPS:** All requests must use HTTPS in production
- **Input Validation:** Validate inputs before sending to API

---

## 📞 Support

### Getting Help
- **Documentation:** This README covers all endpoints
- **Status Page:** Check `/health` for service status
- **Support:** Contact us for technical assistance

### Service Status
- **Uptime:** 99.9% availability target
- **Response Time:** < 2 seconds for status checks
- **Processing Time:** 30-60 seconds for resume processing

---

## 🏢 Enterprise Features

### High Volume Processing
- Custom rate limits for enterprise customers
- Dedicated processing queues
- Priority support

### Security & Compliance
- SOC 2 Type II compliance
- GDPR compliant data handling
- Enterprise-grade encryption

### Custom Integration
- White-label API endpoints
- Custom response formats
- Dedicated support channels

---

**Ready to optimize resumes at scale?** Contact us to get started with your API key and begin processing resumes today.

---

*© 2024 ATS Resume Optimization API. All rights reserved.*
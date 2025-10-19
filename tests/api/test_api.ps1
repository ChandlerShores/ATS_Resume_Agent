# Test API with a real request
Write-Host "`n=== Testing ATS Resume API ===" -ForegroundColor Cyan
Write-Host "Endpoint: http://localhost:8000/api/test/process-sync" -ForegroundColor Yellow

$body = @{
    role = "Senior Software Engineer"
    jd_text = "We are looking for a Senior Software Engineer with Python and FastAPI experience. Must have cloud platform experience."
    bullets = @(
        "Built REST APIs using Python",
        "Deployed applications to cloud"
    )
    settings = @{
        max_len = 30
        variants = 2
    }
} | ConvertTo-Json

Write-Host "`nSending request..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/test/process-sync" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 60

    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "`nResponse:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
    Write-Host "`n=== Results ===" -ForegroundColor Cyan
    foreach ($result in $response.results) {
        Write-Host "`nOriginal: " -NoNewline -ForegroundColor Yellow
        Write-Host $result.original
        Write-Host "Revised:" -ForegroundColor Green
        foreach ($revised in $result.revised) {
            Write-Host "  - $revised" -ForegroundColor White
        }
        Write-Host "Scores: Relevance=$($result.scores.relevance) Impact=$($result.scores.impact) Clarity=$($result.scores.clarity)" -ForegroundColor Magenta
    }
} catch {
    Write-Host "`n❌ ERROR: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}


# Deployment Checklist for Render.com

This checklist ensures your application is ready for production deployment.

## ✅ Critical Tests (Run Before Every Deployment)

### 1. Import Tests (CRITICAL)
```bash
python -m pytest tests/test_imports.py -v
```
**Why:** Catches missing imports that would prevent the app from starting on Render.

**Expected:** All 3 tests should pass
- ✅ Critical imports work
- ✅ StateMachine can be instantiated  
- ✅ FastAPI app can be created

### 2. API Tests
```bash
python -m pytest tests/api/ -v
```
**Why:** Ensures API endpoints work correctly.

**Expected:** All 17 API tests pass

### 3. Security Tests
```bash
python -m pytest tests/security/ -v
```
**Why:** Verifies security features (rate limiting, input validation, etc.)

### 4. Linting
```bash
python -m ruff check .
```
**Why:** Ensures code quality and catches potential bugs

**Expected:** No errors (some warnings OK)

## 📋 Pre-Deployment Checklist

### Code Quality
- [ ] All tests pass (`python -m pytest tests/ -v`)
- [ ] No critical linting errors
- [ ] No import errors in any module
- [ ] All dependencies listed in `requirements.txt` and `pyproject.toml`

### Environment Variables
- [ ] `CUSTOMER_API_KEYS` - Set with valid customer:key pairs
- [ ] `OPENAI_API_KEY` - Set with valid OpenAI key
- [ ] `LLM_PROVIDER` - Set to "openai" or "anthropic"
- [ ] Optional: `REDIS_URL` - Set if using Redis cache
- [ ] Optional: `ALLOWED_ORIGINS` - Set for CORS

### Configuration
- [ ] `.example.env` is up to date with all required variables
- [ ] `README.md` documents all configuration options
- [ ] `render.yaml` has correct configuration

### Application
- [ ] FastAPI app imports without errors
- [ ] StateMachine can be instantiated
- [ ] All API endpoints are registered
- [ ] Health check endpoint works (`/health`)
- [ ] Rate limiting is configured
- [ ] CORS is configured
- [ ] API key authentication works

### Testing
- [ ] Can generate API key using `python scripts/generate_api_key.py`
- [ ] API key authentication works
- [ ] Usage tracking works
- [ ] Cost controller is functioning
- [ ] Input sanitization works
- [ ] Security monitoring is active

## 🚀 Deployment Steps

### 1. Pre-Deployment
```bash
# Run all tests
python -m pytest tests/ -v

# Run linting
python -m ruff check .

# Check for import errors
python -m pytest tests/test_imports.py -v
```

### 2. Generate Production API Keys
```bash
python scripts/generate_api_key.py customer_production
```

### 3. Configure Render.com
1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `CUSTOMER_API_KEYS` (from step 2)
   - `OPENAI_API_KEY`
   - `LLM_PROVIDER=openai`
   - Other required variables

### 4. Deploy
1. Push to main branch
2. Render automatically deploys
3. Check logs for errors

### 5. Post-Deployment Verification
```bash
# Test health endpoint
curl https://your-app.onrender.com/health

# Test API key authentication
curl -H "X-API-Key: your_key" https://your-app.onrender.com/api/bulk/status/test
```

## 🔍 Common Deployment Issues

### Issue: App won't start
**Symptom:** "Application failed to respond" on Render
**Solution:** 
- Check `test_imports.py` passes
- Verify all imports work locally
- Check logs for import errors

### Issue: Import errors in logs
**Symptom:** `ModuleNotFoundError` in Render logs
**Solution:**
- Ensure all modules are in correct directories
- Check for deleted files still being imported
- Run import test: `python -m pytest tests/test_imports.py -v`

### Issue: Environment variables not set
**Symptom:** "API key required" errors
**Solution:**
- Verify `CUSTOMER_API_KEYS` is set in Render dashboard
- Check `.env` file is not committed to git
- Use Render's environment variable settings

### Issue: Redis connection failed
**Symptom:** Cache errors in logs
**Solution:**
- Redis is optional - app falls back to in-memory
- Set `REDIS_URL` if you have Redis instance
- Or ignore cache errors (they're non-critical)

## 📊 Health Check

Test these endpoints after deployment:

### Health Endpoint (No auth required)
```bash
curl https://your-app.onrender.com/health
```
**Expected:** Returns 200 with status "healthy"

### API Endpoint (Auth required)
```bash
curl -H "X-API-Key: your_key" https://your-app.onrender.com/api/bulk/status/test
```
**Expected:** Returns 200 or 404 (not 401)

## 🎯 Success Criteria

Your deployment is successful if:
- ✅ All tests pass locally
- ✅ Import test passes
- ✅ App starts on Render without errors
- ✅ Health endpoint responds
- ✅ API authentication works
- ✅ No critical errors in logs

## 📝 Notes

- The integration test (`tests/integration/test_full_workflow.py`) is optional and requires OpenAI API access
- The main test suite (`test_imports.py`, `test_api`, `test_security`) should all pass before deployment
- Import tests are the most critical - they catch deployment-killing issues early

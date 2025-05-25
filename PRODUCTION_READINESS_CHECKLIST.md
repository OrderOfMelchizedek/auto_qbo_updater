# Production Readiness Checklist

This checklist combines security analysis findings and must be completed before deploying the FOM to QuickBooks automation app to production.

## 🚨 **IMMEDIATE CRITICAL FIXES**

### 1. ✅ Delete Hardcoded Credentials File
- [x] Verify and delete `qbo api client ID and secret.md` file (if it exists) - **DELETED**
- [x] Scan entire codebase for any hardcoded credentials - **COMPLETED**
- [x] Ensure all sensitive files are in `.gitignore` - **VERIFIED**
- [x] **CRITICAL: REVOKE COMPROMISED CREDENTIALS IN QUICKBOOKS DEVELOPER PORTAL** - **COMPLETED**
- [x] **Remove credentials from Git history (see instructions below)** - **COMPLETED**

#### Instructions to Remove Credentials from Git History:
**WARNING**: This will rewrite Git history. Coordinate with any collaborators first.

```bash
# Option 1: If repository is not critical and can be recreated
# 1. Delete the GitHub repository
# 2. Remove .git folder locally: rm -rf .git
# 3. Re-initialize: git init
# 4. Add all files: git add .
# 5. Commit: git commit -m "Initial commit - cleaned history"
# 6. Create new GitHub repo and push

# Option 2: Use BFG Repo-Cleaner (recommended for preserving history)
# 1. Install BFG: brew install bfg (on Mac)
# 2. Clone a fresh copy: git clone --mirror git@github.com:OrderOfMelchizedek/auto_qbo_updater.git
# 3. Run BFG: bfg --delete-files "qbo api client ID and secret.md" auto_qbo_updater.git
# 4. Clean up: cd auto_qbo_updater.git && git reflog expire --expire=now --all && git gc --prune=now --aggressive
# 5. Push changes: git push --force

# Option 3: Use git filter-branch (built-in but slower)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch "qbo api client ID and secret.md"' \
  --prune-empty --tag-name-filter cat -- --all
```

### 2. ✅ Fix Flask Secret Key Persistence
- [x] Replace dynamic secret key generation with environment variable - **COMPLETED**
```python
# In src/app.py line 284, replaced:
app.secret_key = os.urandom(24)
# With:
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable is required. Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'")
```
- [x] Generate a strong secret key for production - **COMPLETED** (64-character hex key)
- [x] Add `FLASK_SECRET_KEY` to `.env.example` - **COMPLETED** (with generation instructions)

### 3. ❌ Consolidate OAuth Implementation
- [ ] Review both `QBOOAuthService` (using intuitlib) and `QBOService` (custom implementation)
- [ ] Choose one approach and remove the redundant code
- [ ] Update all references to use the chosen implementation
- [ ] Test OAuth flow thoroughly

### 4. ❌ Add Environment Variable Validation
- [ ] Add startup validation for all required environment variables
```python
# Add to src/app.py after imports:
required_env_vars = [
    'FLASK_SECRET_KEY',
    'GEMINI_API_KEY', 
    'QBO_CLIENT_ID',
    'QBO_CLIENT_SECRET',
    'QBO_REDIRECT_URI'
]
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
```

## ⚠️ **HIGH PRIORITY SECURITY FIXES**

### 5. ❌ Implement Server-Side Session Storage
- [ ] Install Flask-Session: `pip install Flask-Session redis`
- [ ] Configure Redis or database backend for sessions
- [ ] Update `requirements.txt`
- [ ] Test with large donation datasets

### 6. ❌ Add Duplicate Sales Receipt Prevention
- [ ] Check for existing `qboSalesReceiptId` before creating new receipts
- [ ] Add logic to prevent duplicate submissions
- [ ] Handle edge cases (network timeouts, retries)

### 7. ❌ Fix SQL Injection Vulnerability
- [ ] Replace string concatenation in QBO queries (qbo_service.py:175)
- [ ] Use proper parameterized queries or QuickBooks API query builder
- [ ] Test with various special characters in search

### 8. ❌ Add CSRF Protection
- [ ] Install Flask-WTF: `pip install Flask-WTF`
- [ ] Add CSRF tokens to all forms
- [ ] Update `requirements.txt`
- [ ] Test all POST endpoints

### 9. ❌ Secure File Upload Handling
- [ ] Generate unique filenames instead of using user-provided names
- [ ] Validate file content, not just extensions
- [ ] Add file size validation per file (not just total)
- [ ] Implement virus scanning if possible
- [ ] Clean up uploaded files after processing

## 📊 **MEDIUM PRIORITY IMPROVEMENTS**

### 10. ❌ Update Date Validation
- [ ] Remove hardcoded "2024-06-01" check in gemini_service.py
- [ ] Implement dynamic date validation relative to current date
- [ ] Add configurable date range limits

### 11. ❌ Enhance Error Handling
- [ ] Wrap all external API calls in proper try-except blocks
- [ ] Create custom exception classes
- [ ] Log errors internally, show generic messages to users
- [ ] Add retry logic for transient failures

### 12. ❌ Add Rate Limiting
- [ ] Install Flask-Limiter: `pip install Flask-Limiter`
- [ ] Configure rate limits for API endpoints
- [ ] Add specific limits for Gemini API calls
- [ ] Update `requirements.txt`

### 13. ❌ Implement Proper Logging
- [ ] Set up Python logging configuration
- [ ] Add log rotation
- [ ] Configure different log levels for development/production
- [ ] Ensure no sensitive data is logged

### 14. ❌ Add Health Check Endpoints
- [ ] Create `/health` endpoint for basic health check
- [ ] Create `/ready` endpoint to check external service connectivity
- [ ] Add monitoring for QBO token expiration

## 💡 **GOOD PRACTICES & DOCUMENTATION**

### 15. ❌ Create Configuration Templates
- [ ] Create `.env.example` with all required variables (without values)
- [ ] Document each environment variable's purpose
- [ ] Add setup instructions to README

### 16. ❌ Document Production Deployment
- [ ] Create `DEPLOYMENT.md` with step-by-step instructions
- [ ] Document Heroku-specific configurations
- [ ] Include troubleshooting guide
- [ ] Add backup and recovery procedures

### 17. ❌ Add Monitoring and Alerting
- [ ] Set up application performance monitoring (APM)
- [ ] Configure error tracking (e.g., Sentry)
- [ ] Set up uptime monitoring
- [ ] Create alert rules for critical errors

### 18. ❌ Increase Test Coverage
- [ ] Add tests for OAuth flow
- [ ] Add tests for QBO API integration
- [ ] Add tests for file upload security
- [ ] Add tests for data validation
- [ ] Aim for >70% coverage on critical paths

## 📝 **OPTIONAL ENHANCEMENTS**

### 19. ⭕ Performance Optimizations
- [ ] Implement caching for QBO customer list
- [ ] Add pagination for large datasets
- [ ] Optimize Gemini API calls
- [ ] Consider background job processing for large batches

### 20. ⭕ User Experience Improvements
- [ ] Add detailed progress indicators for batch operations
- [ ] Implement auto-save for user edits
- [ ] Add export functionality for processed data
- [ ] Improve error messages with suggested actions

## 🚀 **DEPLOYMENT CHECKLIST**

Before deploying to production, ensure:
- [ ] All CRITICAL fixes are completed
- [ ] All HIGH PRIORITY fixes are completed
- [ ] Environment variables are properly configured
- [ ] SSL/HTTPS is enabled
- [ ] Backups are configured
- [ ] Monitoring is active
- [ ] Test deployment in staging environment
- [ ] Load testing completed
- [ ] Security scan completed
- [ ] Rollback plan documented

---

**Status Legend:**
- ❌ Not Started
- 🔄 In Progress
- ✅ Completed
- ⭕ Optional/Future Enhancement

**Last Updated:** [Current Date]
**Target Production Date:** [To Be Determined]

## Notes
- Update status symbols as tasks are completed
- Add any new issues discovered during implementation
- Document any decisions or trade-offs made
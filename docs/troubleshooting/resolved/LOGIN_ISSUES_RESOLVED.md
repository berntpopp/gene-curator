# Login Issues Troubleshooting Guide

## Issue: Login Buttons Fail Silently (No Backend Requests)

### Symptoms
- Clicking login buttons does nothing
- No error messages displayed
- No login attempts appear in backend logs
- Frontend console shows no network requests to `/api/v1/auth/login`

### Root Cause
**Missing or incorrect `frontend/.env.local` configuration**

The frontend was using the default API URL `http://localhost:8001` (from `client.js` line 5), but Gene Curator's backend API runs on **port 8051** (non-standard port to avoid conflicts).

### Solution

1. **Create `frontend/.env.local` file** with the correct API URL:

```bash
# Local development environment configuration
# This file overrides defaults and is NOT committed to git

# Backend API URL (Gene Curator uses non-standard port 8051)
VITE_API_BASE_URL=http://localhost:8051

# Application title
VITE_APP_TITLE=Gene Curator (Dev)

# Environment
VITE_ENVIRONMENT=development

# Enable development features
VITE_ENABLE_DEV_LOGIN=true
```

2. **Vite will automatically restart** when it detects the new `.env.local` file

3. **Refresh your browser** to pick up the new configuration

### Verification

After creating the `.env.local` file, verify the login works:

1. **Check Vite logs** for restart message:
   ```
   [vite] .env.local changed, restarting server...
   [vite] server restarted.
   ```

2. **Refresh browser** (Ctrl+R or Cmd+R)

3. **Try logging in** with any dev account:
   - Admin: `admin@genecurator.org` / `admin123`
   - Curator: `dev@example.com` / `admin123`
   - Reviewer: `reviewer@example.org` / `admin123`
   - Viewer: `test@example.com` / `admin123`

4. **Check backend logs** for login attempts:
   ```bash
   # Should see logs like:
   app.api.v1.endpoints.auth - INFO - Login attempt | email=admin@genecurator.org
   app.crud.user - INFO - User authenticated successfully
   app.api.v1.endpoints.auth - INFO - Login successful
   ```

### Prevention

Always run `make hybrid-up` or `make dev` which should create the `.env.local` file automatically. If it doesn't exist, create it manually following the template above.

### Related Files
- `frontend/.env.local` - Local environment configuration (NOT committed to git)
- `frontend/src/api/client.js` - API client with default URL fallback
- `.env.dev` - Root-level development environment (committed to git)
- `CLAUDE.md` - Project instructions mentioning non-standard ports

### Why Non-Standard Ports?

Gene Curator uses non-standard ports to avoid conflicts with other applications:
- Backend API: **8051** (instead of 8000/8001)
- Frontend Docker: **3051** (instead of 3000/3001)
- Frontend Vite: **5193** (instead of 5173)
- PostgreSQL: **5454** (instead of 5432/5433)
- Redis: **6399** (instead of 6379)

This allows running Gene Curator alongside other projects without port conflicts.

---

## Issue: Login Returns 401 Unauthorized

### Symptoms
- Login button works (request sent to backend)
- Backend logs show authentication attempt
- Response is `401 Unauthorized` with "Incorrect email or password"
- Correct credentials are being used

### Root Cause
**Incorrect password hash in database seed data**

The bcrypt hash stored in `database/sql/004_seed_data.sql` does not verify against the password "admin123".

### Solution

1. **Verify the password hash** is correct:
   ```bash
   cd backend
   uv run python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.verify('admin123', '\$2b\$12\$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6'))"
   # Should output: True
   ```

2. **If hash is wrong**, update `database/sql/004_seed_data.sql` with correct hash:
   ```sql
   '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6' -- password: admin123
   ```

3. **Re-initialize database**:
   ```bash
   make db-reset
   # Or manually:
   docker exec -i gene_curator_postgres psql -U dev_user -d gene_curator_dev -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   cat database/sql/*.sql | docker exec -i gene_curator_postgres psql -U dev_user -d gene_curator_dev
   ```

4. **Test login** with `admin123` password

### Related Issues
- See `LOGIN_FIX_SUMMARY.md` for detailed password hash investigation
- See `backend/app/tests/unit/test_auth.py` for automated password verification tests

---

## Issue: Login Succeeds But Redirects to Login Again

### Symptoms
- Login returns 200 OK with tokens
- Tokens stored in localStorage
- Page redirects back to login immediately

### Possible Causes

1. **JWT secret mismatch** between backend instances
2. **Token validation failing** in `/auth/me` endpoint
3. **localStorage not persisting** (browser privacy settings)
4. **Router guards rejecting** authenticated user

### Solution

1. **Check JWT tokens are stored**:
   ```javascript
   // In browser console:
   localStorage.getItem('access_token')
   localStorage.getItem('refresh_token')
   ```

2. **Verify token is valid**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://localhost:8051/api/v1/auth/me
   ```

3. **Check backend SECRET_KEY** is consistent:
   ```bash
   grep SECRET_KEY backend/.env
   # Should match in .env.dev and backend/.env
   ```

4. **Clear localStorage and retry**:
   ```javascript
   localStorage.clear()
   // Then try logging in again
   ```

---

## Additional Debugging

### Enable Debug Logging

**Backend**:
```bash
# In backend/.env
LOG_LEVEL=DEBUG
```

**Frontend**:
```javascript
// In browser console:
logService.setMinLogLevel('DEBUG')
logService.setConsoleEcho(true)
```

### Check Network Requests

1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by "login"
4. Check request/response details

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Wrong credentials or bad password hash | Check password hash in database |
| `CORS error` | Frontend/backend on different origins | Check ALLOWED_ORIGINS in backend config |
| `Network error` | Backend not running or wrong port | Check backend is running on port 8051 |
| `timeout` | Backend taking too long | Check database connection, increase timeout |

---

## Quick Reference

### Development Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@genecurator.org | admin123 |
| Curator | dev@example.com | admin123 |
| Reviewer | reviewer@example.org | admin123 |
| Viewer | test@example.com | admin123 |

### API Endpoints

- Login: `POST /api/v1/auth/login`
- Me: `GET /api/v1/auth/me`
- Refresh: `POST /api/v1/auth/refresh`
- Logout: `POST /api/v1/auth/logout`

### Ports

- Backend API: `http://localhost:8051`
- Frontend (Vite): `http://localhost:5193`
- Frontend (Docker): `http://localhost:3051`
- Database: `localhost:5454`

---

**Last Updated**: 2025-10-13
**Related Documentation**:
- `CLAUDE.md` - Project instructions
- `LOGIN_FIX_SUMMARY.md` - Detailed password hash fix
- `backend/app/tests/unit/test_auth.py` - Authentication tests

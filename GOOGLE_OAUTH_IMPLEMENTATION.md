# Google OAuth Implementation Guide

## Overview
This document describes the Google OAuth 2.0 integration for signup and login functionality in the Salona API.

The implementation uses a **unified endpoint** that automatically handles both signup and login:
- If the user exists, they are logged in
- If the user doesn't exist, a new account is created with a random password

## Setup

### 1. Environment Variables
Add the following environment variables to your `.env` file:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/users/auth/google/callback
```

To get these credentials:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URIs:
   - For development: `http://localhost:8000/api/v1/users/auth/google/callback`
   - For production: `https://your-domain.com/api/v1/users/auth/google/callback`

### 2. Dependencies
The following packages have been added to `requirements.txt`:
- `google-auth==2.25.2`
- `google-auth-httplib2==0.2.0`
- `google-auth-oauthlib==1.2.0`

Install them:
```bash
pip install -r requirements.txt
```

## API Endpoints

### 1. Initiate Google OAuth Flow

**Endpoint:** `POST /api/v1/users/auth/google/authorize`

**Description:** Initiates the Google OAuth flow by generating an authorization URL and state token for CSRF protection.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/users/auth/google/authorize
```

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "secure_random_token"
}
```

**Usage:**
1. Call this endpoint to get the authorization URL
2. Redirect the user to the `authorization_url`
3. The state token is stored in an httpOnly cookie for CSRF protection

---

### 2. Google OAuth Callback (Unified)

**Endpoint:** `POST /api/v1/users/auth/google/callback`

**Description:** Unified endpoint that handles both signup and login:
- **If user exists:** Authenticates and returns tokens (login)
- **If user doesn't exist:** Creates new account with random password and returns tokens (signup)

**Request:**
```json
{
  "code": "authorization_code_from_google",
  "state": "state_token_from_cookie",
  "redirect_uri": "http://localhost:8000/api/v1/users/auth/google/callback"
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/users/auth/google/callback \
  -H "Content-Type: application/json" \
  -d '{
    "code": "4/0AY0e-g...",
    "state": "secure_random_token"
  }' \
  -b "google_oauth_state=secure_random_token"
```

**Response (New User - Account Created):**
```json
{
  "status": "success",
  "message": "Account created and logged in successfully via Google",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user_email": "newuser@example.com",
    "user_name": "John Doe"
  }
}
```

**Response (Existing User - Login):**
```json
{
  "status": "success",
  "message": "Logged in successfully via Google",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user_email": "existinguser@example.com",
    "user_name": "Jane Doe"
  }
}
```

**How It Works:**

```
1. User clicks "Login/Signup with Google"
   ↓
2. Frontend calls /auth/google/authorize
   ↓
3. User is redirected to Google login/consent screen
   ↓
4. Google redirects back with authorization code
   ↓
5. Frontend sends code to /auth/google/callback
   ↓
6. Backend checks if user exists
   ├─ If YES: Authenticate user (login flow)
   └─ If NO: Create new user (signup flow)
   ↓
7. Return tokens and set secure cookies
   ↓
8. User is authenticated and can access protected endpoints
```

---

## Frontend Integration Example

### React/JavaScript Implementation

```javascript
// 1. Initiate Google OAuth flow (same for signup and login)
async function initiateGoogleAuth() {
  const response = await fetch('/api/v1/users/auth/google/authorize', {
    method: 'POST',
    credentials: 'include' // Important: include cookies
  });
  
  const data = await response.json();
  // Redirect user to Google
  window.location.href = data.authorization_url;
}

// 2. Handle callback (same endpoint for both signup and login)
async function handleGoogleCallback(code, state) {
  // Single unified endpoint for both signup and login
  const response = await fetch('/api/v1/users/auth/google/callback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      code,
      state,
      redirect_uri: window.location.origin + '/auth/callback'
    }),
    credentials: 'include' // Important: include cookies for auth
  });
  
  const data = await response.json();
  
  if (data.status === 'success') {
    console.log('User authenticated:', data.data.user_email);
    console.log('Message:', data.message); // Shows if account was created or logged in
    // Redirect to dashboard
    window.location.href = '/dashboard';
  } else {
    console.error('Authentication failed:', data.message);
  }
}

// 3. Extract code and state from URL after Google redirect
const params = new URLSearchParams(window.location.search);
const code = params.get('code');
const state = params.get('state');

if (code && state) {
  // No need to differentiate between signup/login - same endpoint handles both
  handleGoogleCallback(code, state);
}
```

### HTML Integration Example

```html
<!-- Single button for both signup and login -->
<button onclick="initiateGoogleAuth()">
  Continue with Google
</button>

<script>
function initiateGoogleAuth() {
  initiateGoogleAuth();
}
</script>
```

---

## Security Features

### 1. CSRF Protection
- State token is generated and stored in an httpOnly cookie
- State token is validated on callback
- Prevents cross-site request forgery attacks

### 2. Secure Tokens
- Access tokens: 30 minutes expiration
- Refresh tokens: 7 days expiration
- Both stored in httpOnly, Secure cookies (can't be accessed by JavaScript)

### 3. Random Passwords
- OAuth users get random 16-character passwords
- Includes uppercase, lowercase, digits, and special characters
- Users can reset password if needed

### 4. Email Verification
- Emails from Google are automatically marked as verified
- Email verification token is created and marked as used

---

## Error Handling

### Common Errors

1. **Invalid State Token**
   - Status: 400
   - Message: "Invalid state token - CSRF protection failed"
   - Cause: State mismatch or expired state cookie

2. **Failed to Exchange Code**
   - Status: 400
   - Message: "Failed to exchange authorization code for tokens"
   - Cause: Invalid authorization code or expired code

3. **No Email in Google Account**
   - Status: 400
   - Message: "Google account does not have an email"
   - Cause: User's Google account has no email attached

4. **OAuth Authentication Failed**
   - Status: 500
   - Message: "Google OAuth authentication failed: {error details}"
   - Cause: General OAuth process failure

---

## Testing with cURL

### Full OAuth Flow Test

```bash
# Step 1: Get authorization URL
curl -X POST http://localhost:8000/api/v1/users/auth/google/authorize \
  -H "Content-Type: application/json" \
  -c cookies.txt

# Step 2: Extract authorization code from Google (manual step)
# Visit the authorization_url and authorize the app
# Google will redirect with ?code=...&state=...

# Step 3: Use the code and state for unified callback (works for both signup and login)
curl -X POST http://localhost:8000/api/v1/users/auth/google/callback \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "code": "YOUR_GOOGLE_AUTH_CODE",
    "state": "YOUR_STATE_TOKEN"
  }'
```

---

## Database Changes

No database schema changes are required. The implementation uses existing `Users` table:
- Email verified status is automatically set to true for OAuth users
- Random password is generated and hashed
- User verification record is created and marked as used

---

## Configuration

### File: `app/core/config.py`
Added three new settings:
- `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret
- `GOOGLE_REDIRECT_URI`: Redirect URI for OAuth callback

### File: `app/services/google_oauth.py`
New service class with methods:
- `get_authorization_url()`: Generates Google authorization URL
- `exchange_code_for_token()`: Exchanges code for access token
- `get_user_info()`: Retrieves user information from Google
- `generate_random_password()`: Generates secure random password
- `generate_state_token()`: Generates CSRF protection token

### File: `app/schemas/auth.py`
Added new Pydantic schemas:
- `GoogleAuthorizationResponse`: Authorization URL response
- `GoogleCallbackRequest`: Callback request data
- `GoogleOAuthResponse`: Successful OAuth response

### File: `app/api/api_v1/endpoints/users.py`
Added two endpoints:
- `POST /auth/google/authorize`: Initiate OAuth flow
- `POST /auth/google/callback`: **Unified** callback for both signup and login

---

## Migration from Separate Endpoints

If you were previously using separate `/callback/signup` and `/callback/login` endpoints:

**Before (Two Endpoints):**
```
POST /auth/google/callback/signup  (for signup only)
POST /auth/google/callback/login   (for login only)
```

**Now (Unified):**
```
POST /auth/google/callback  (works for both signup and login)
```

The unified endpoint automatically determines whether to:
- **Create a new user** if the email doesn't exist
- **Authenticate existing user** if the email exists

No frontend changes needed beyond removing the conditional logic!

---

## Troubleshooting

### "Client ID and secret not found"
- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in environment variables
- Verify they match the values from Google Cloud Console

### "Invalid redirect URI"
- Ensure `GOOGLE_REDIRECT_URI` matches exactly with the authorized redirect URI in Google Cloud Console
- Include the full URI path (e.g., `http://localhost:8000/api/v1/users/auth/google/callback`)

### State token validation fails
- Ensure cookies are being sent with requests (`credentials: 'include'` in fetch)
- Check that the state cookie hasn't expired (10-minute TTL)
- Verify the state in the callback request matches the state in the cookie

### "Account created and logged in" vs "Logged in successfully"
- **"Account created and logged in successfully via Google"**: New user was created
- **"Logged in successfully via Google"**: Existing user was authenticated
- Both return the same response format with tokens

---

## Next Steps

1. Add Google OAuth configuration to your deployment environment
2. Update your frontend to use the unified callback endpoint
3. Test the full flow in development
4. Deploy to production with production Google OAuth credentials

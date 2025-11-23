# Handling Expired Tokens in UI

## Overview

When the access token expires, the API returns a `401 Unauthorized` status with the message:
```json
{
  "detail": "Access token has expired"
}
```

Your UI should automatically handle this by refreshing the token without requiring the user to log in again.

## Token Architecture

- **Access Token**: Short-lived (18 seconds = 0.3 minutes), stored in HTTP-only cookie
- **Refresh Token**: Long-lived (7 days), stored in HTTP-only cookie
- Both tokens are automatically sent with each request via cookies

## API Endpoints

### Refresh Token Endpoint
```
POST /users/api/v1/auth/refresh-token
```

**Request**: No body needed (refresh token is automatically sent via HTTP-only cookie)

**Response** (Success):
```json
{
  "status": "success",
  "message": "",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "at_expires_in": 18,
    "rt_expires_in": 604800
  }
}
```

**Response** (Error - Refresh token also expired):
```json
{
  "detail": "Access token has expired"
}
```

## UI Implementation Strategies

### Strategy 1: Axios Interceptor (Recommended)

This approach automatically intercepts 401 errors and retries failed requests after refreshing the token.

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://your-api.salona.me',
  withCredentials: true, // Important: sends cookies with requests
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and has "expired" in the message
    if (
      error.response?.status === 401 &&
      error.response?.data?.detail?.includes('expired') &&
      !originalRequest._retry
    ) {
      if (isRefreshing) {
        // Queue the request while refreshing
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Call refresh token endpoint
        await api.post('/users/api/v1/auth/refresh-token');
        
        processQueue(null);
        isRefreshing = false;
        
        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh token also expired - redirect to login
        processQueue(refreshError, null);
        isRefreshing = false;
        
        // Clear any local state
        localStorage.clear();
        
        // Redirect to login page
        window.location.href = '/login';
        
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

**Usage**:
```javascript
import api from './api';

// Just make normal API calls - expired tokens are handled automatically
async function fetchBookings() {
  try {
    const response = await api.get('/users/api/v1/bookings?start_date=2025-11-20&end_date=2025-11-26');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch bookings:', error);
  }
}
```

### Strategy 2: Fetch API with Wrapper Function

If you're using native fetch instead of axios:

```javascript
const API_BASE_URL = 'https://your-api.salona.me';
let isRefreshing = false;
let refreshPromise = null;

async function refreshAccessToken() {
  const response = await fetch(`${API_BASE_URL}/users/api/v1/auth/refresh-token`, {
    method: 'POST',
    credentials: 'include', // Important: sends cookies
  });

  if (!response.ok) {
    throw new Error('Refresh token expired');
  }

  return response.json();
}

async function apiFetch(url, options = {}) {
  // Ensure credentials are included
  options.credentials = 'include';

  let response = await fetch(`${API_BASE_URL}${url}`, options);

  // Check if access token expired
  if (response.status === 401) {
    const error = await response.json();
    
    if (error.detail?.includes('expired')) {
      // Prevent multiple simultaneous refresh calls
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshAccessToken()
          .then(() => {
            isRefreshing = false;
            refreshPromise = null;
          })
          .catch((err) => {
            isRefreshing = false;
            refreshPromise = null;
            // Redirect to login
            window.location.href = '/login';
            throw err;
          });
      }

      // Wait for refresh to complete
      await refreshPromise;

      // Retry original request
      response = await fetch(`${API_BASE_URL}${url}`, options);
    }
  }

  return response;
}

export default apiFetch;
```

**Usage**:
```javascript
import apiFetch from './apiFetch';

async function fetchBookings() {
  try {
    const response = await apiFetch('/users/api/v1/bookings?start_date=2025-11-20&end_date=2025-11-26');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to fetch bookings:', error);
  }
}
```

### Strategy 3: React Hook (with React Query)

For React applications using React Query:

```javascript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './api'; // Axios instance with interceptor from Strategy 1

export function useBookings(startDate, endDate) {
  return useQuery({
    queryKey: ['bookings', startDate, endDate],
    queryFn: async () => {
      const response = await api.get('/users/api/v1/bookings', {
        params: { start_date: startDate, end_date: endDate }
      });
      return response.data;
    },
    retry: (failureCount, error) => {
      // Don't retry if it's an auth error (already handled by interceptor)
      if (error.response?.status === 401) {
        return false;
      }
      return failureCount < 3;
    }
  });
}

// Usage in component
function BookingsPage() {
  const { data, isLoading, error } = useBookings('2025-11-20', '2025-11-26');

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data.data.map(booking => (
        <div key={booking.id}>{booking.customer_name}</div>
      ))}
    </div>
  );
}
```

## Important Configuration

### CORS Settings
Ensure your API allows credentials in CORS configuration:

```python
# In your FastAPI app setup
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.salona.me"],
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Cookie Configuration
Your cookies are already configured correctly with:
- `httponly=True` - Prevents JavaScript access (security)
- `secure=True` - Only sent over HTTPS in production
- `samesite="lax"` - Prevents CSRF attacks
- `domain=".salona.me"` - Shared across subdomains

## User Experience Flow

```
1. User makes API request
   ↓
2. Access token expired (18 seconds)
   ↓
3. API returns 401 with "Access token has expired"
   ↓
4. UI automatically calls /auth/refresh-token
   ↓
5a. Success: New tokens set in cookies → Retry original request
   ↓
   User sees data (seamless experience)

5b. Failure: Refresh token also expired (7 days)
   ↓
   Redirect user to login page
   ↓
   User logs in again
```

## Testing

### Test Expired Token Handling

```javascript
// Manually test by waiting for token to expire (18 seconds)
async function testTokenRefresh() {
  console.log('Making initial request...');
  const response1 = await api.get('/users/api/v1/me');
  console.log('Success:', response1.data);

  console.log('Waiting 20 seconds for token to expire...');
  await new Promise(resolve => setTimeout(resolve, 20000));

  console.log('Making request with expired token...');
  const response2 = await api.get('/users/api/v1/me');
  console.log('Success (token auto-refreshed):', response2.data);
}
```

## Best Practices

1. **Always use `withCredentials: true`** (axios) or `credentials: 'include'` (fetch)
2. **Queue failed requests** during token refresh to avoid multiple refresh calls
3. **Clear local storage** and redirect to login when refresh token expires
4. **Show loading indicator** during token refresh (optional, usually < 200ms)
5. **Handle edge cases**: Network errors, concurrent requests, etc.
6. **Don't manually manage tokens** - let HTTP-only cookies handle it

## Common Pitfalls

❌ **Don't do this:**
```javascript
// Manually storing tokens in localStorage
localStorage.setItem('access_token', token); // Security risk!
```

✅ **Do this:**
```javascript
// Let cookies handle it automatically
await api.get('/endpoint'); // Cookies sent automatically
```

❌ **Don't do this:**
```javascript
// Making refresh call for every 401 error
if (error.response.status === 401) {
  await refreshToken(); // Could cause multiple refresh calls
}
```

✅ **Do this:**
```javascript
// Use a flag to prevent concurrent refresh calls
if (!isRefreshing) {
  isRefreshing = true;
  await refreshToken();
}
```

## Summary

Your backend is already set up correctly with:
- ✅ 401 status code for expired tokens
- ✅ Clear error message: "Access token has expired"
- ✅ Refresh token endpoint
- ✅ HTTP-only cookies for security

Your UI just needs to:
1. Intercept 401 errors with "expired" message
2. Call `/auth/refresh-token` endpoint
3. Retry the original request
4. Redirect to login if refresh token also expired

Use **Strategy 1 (Axios Interceptor)** for the easiest implementation!


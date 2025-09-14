# Customer Authentication API (v1)

## Overview

This document covers authentication for the **Customers** in Salona.

All authentication endpoints are versioned under:

/api/v1/auth/customers

---

## TL;DR
- **Auth type:** JWT (access + refresh). Access token short-lived, refresh token long-lived (httpOnly cookie or secure storage).
- **Actors:** `worker`, `client`
- **Audience/Scope:** tokens include `actor` claim and optional `company_id` context for worker actions.
- **Versioning:** Path-based (`/api/v1/...`) + deprecation headers when needed.
- **Multitenancy header:** `X-Company-Id: <uuid>` required for worker endpoints that act in a company context (when worker belongs to >1 company).

---

## Token Structure

**Access Token (JWT)**
- `sub`: user id (UUID)
- `actor`: `"worker"` or `"client"`
- `exp`: short TTL (e.g., 15m)
- `scopes`: array of permissions (e.g., `["availability:read", "bookings:write"]`)
- `ver`: token schema version (e.g., `1`)
- `iat`: token issued at, `iss`: token issued by, `aud`: token intended for

**Refresh Token**
- Long TTL (e.g., 30–90 days), rotation on use.
- Stored server-side (token family) to allow revocation.
- Delivered as httpOnly, Secure cookie for browsers; as opaque token for native/mobile.

**Auth Header**

Authorization: Bearer <access_token>

---

---
 
---

# Endpoints

## Customer Registration 

Registers a new customer account.

```
POST /api/v1/customers/auth/signup
```

**Request Body**
```json
{
  "email": "stylist@salona.com",
  "password": "********",
  "first_name": "Ava",
  "last_name": "M.",
  "phone": "+15555550123"
}
```

201 Created

**Response**

```json
{
  "id": "uuid",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "status": "pending_verification",
  "created_at": "2025-09-08T10:00:00Z"
}
```

--- 

#### - Email verification

Confirms customer’s email after signup.

```
POST /api/v1/auth/users/verify-email
```

**Request Body**
```json
{
  "token": "verification-token"
}
```
200 OK

```json
{
  "message": "Email verified successfully",
  "status": "active"
}
```

--- 

## Login

Authenticates customer with email/phone + password.

Endpoint:
```
POST /api/v1/customers/auth/login
```

Request Body:
```json
{
  "email": "john@example.com",
  "password": "StrongPassword123!"
}
```

Response (200 OK):
```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Refresh Token

Generates a new access token using a refresh token.

Endpoint:
```
POST /api/v1/customers/auth/refresh
```

Request Body:
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

Response (200 OK):
```json
{
  "access_token": "new-jwt-access-token",
  "refresh_token": "new-jwt-refresh-token",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Logout

Revokes the refresh token and invalidates session.

Endpoint:
```
POST /api/v1/customers/auth/logout
```

Headers:
```
Authorization: Bearer <access_token>
```

Request Body:
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

Response (200 OK):
```json
{
  "message": "Successfully logged out"
}
```

## Forgot Password

Request a reset link.

Endpoint:
```
POST /api/v1/customers/auth/forgot-password
```

Request Body:
```json
{
  "email": "john@example.com"
}
```

Response (200 OK):
```json
{
  "message": "Password reset link sent to email"
}
```

## Reset Password

Resets customer’s password using reset token.

Endpoint:
```
POST /api/v1/customers/auth/reset-password
```

Request Body:
```json
{
  "token": "reset-token",
  "new_password": "NewStrongPassword456!"
}
```

Response (200 OK):
```json
{
  "message": "Password updated successfully"
}
```

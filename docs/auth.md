# Authentication – Salona Booking System API (v1)

## Overview

This document covers authentication for the **two actor types** in Salona:
- **Users**: staff who operate inside companies and manage availability, services, and bookings.
- **Clients**: end customers who create reservations.

- Companies are created by workers and can have many workers. A worker can belong to multiple companies.

All authentication endpoints are versioned under:

/api/v1

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
- `company_id` (optional): when the worker explicitly selects a company context
- `ver`: token schema version (e.g., `1`)
- `iat`: token issued at, `iss`: token issued by, `aud`: token intended for

**Refresh Token**
- Long TTL (e.g., 30–90 days), rotation on use.
- Stored server-side (token family) to allow revocation.
- Delivered as httpOnly, Secure cookie for browsers; as opaque token for native/mobile.

**Auth Header**

Authorization: Bearer <access_token>

---

## Endpoints

### Users

#### Sign up

POST /api/v1/auth/users/signup

**Body**
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

Response Example
```json
{
  "id": "uuid",
  "email": "stylist@salona.com",
  "role": "user",
  "status": "pending_verification"
}
```

--- 

#### Email verification

POST /api/v1/auth/users/verify-email

**Body**
```json
{
  "token": "verification-token"
}
```
200 OK

--- 

#### Login

POST /api/v1/auth/users/signin

**Body**

```json
{
  "email": "stylist@salona.com",
  "password": "********"
}
```

200 OK

Response Example
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque-or-jwt>",
  "role": "user",
  "user": {
    "id": "uuid",
    "email": "stylist@salona.com",
    "companies": [
      { "id": "uuid-company-1", "name": "Glow Studio", "role": "owner" },
      { "id": "uuid-company-2", "name": "Urban Cuts", "role": "member" }
    ]
  }
}
```
---

#### Refresh token

POST /api/v1/auth/refresh

**Body**

```json
{ "refresh_token": "<token>" }
```

200 OK
```json
{
  "access_token": "<new-jwt-access-token>",
  "refresh_token": "<new-refresh-token>",
  "token_type": "Bearer",
  "expires_in": 900
}
```
---
#### Sign out

POST /api/v1/auth/signout

Revokes refresh token family.

---

#### Password reset (request + confirm)
POST /api/v1/auth/users/password-reset/request
POST /api/v1/auth/users/password-reset/confirm

---
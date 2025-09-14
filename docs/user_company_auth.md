# Authentication – Salona Booking System API (v1)

## Overview

This document covers authentication for the **two actor types** in Salona:
- **Users**: staff who operate inside companies and manage availability, services, and bookings.
- **Companies**: Companies.

- Companies are created by workers and can have many workers. A worker can belong to multiple companies.

All authentication endpoints are versioned under:

/api/v1/users/auth

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

---
 
---

# Endpoints

## User Registration & Company Membership

Users can join the Salona Booking System in two ways:

### 1. Self-Registration + Company Creation

- A new user signs up through /users/auth/signup.

- After verifying email, the user creates a Company Profile (POST /companies).

- This user automatically becomes the admin/owner of that company.

#### - Signup
POST /api/v1/users/auth/signup

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

#### - Email verification

POST /api/v1/users/auth/verify-email

**Body**
```json
{
  "token": "verification-token"
}
```
200 OK

--- 

#### - Company creation

```
POST /api/v1/companies
Authorization: Bearer <access_token>
```

```json
{
  "name": "Glow Studio",
  "address": "123 Main St",
  "timezone": "Europe/Tallinn"
}
```

Response

```json
{
  "id": "uuid-company",
  "name": "Glow Studio",
  "owner": { "user_id": "uuid-user", "role": "owner" }
}
```

---

### 2. Invitation by Company Admin

A company admin sends an invite to an email address.

The invite generates a unique invitation URL (containing a token).

The recipient accepts the invitation:

- If already registered, the system just links their user to the company.

- If not registered yet, they sign up first, and then the invite binds them to the company.

#### - Invite user

```
POST /api/v1/companies/{company_id}/members/invite
Authorization: Bearer <access_token>
```

```json
{ "email": "stylist@salona.com", "role": "member" }
```

Response

```json
{
  "invitation_id": "uuid-invite",
  "company_id": "uuid-company",
  "email": "stylist@salona.com",
  "role": "member",
  "status": "pending",
  "invitation_url": "https://app.salona.com/invite/uuid-invite-token"
}
```

Accept invitation
```
POST /api/v1/users/auth/accept-invite
```

```json
{
  "invitation_token": "uuid-invite-token",
  "password": "********"   // if not registered
}
```

Response

```json
{
  "user": {
    "id": "uuid-user",
    "email": "stylist@salona.com"
  },
  "company": {
    "id": "uuid-company",
    "name": "Glow Studio",
    "role": "member"
  }
}
```


**Key Notes**

- A user can belong to multiple companies.

- Roles are stored in the company_members table (owner, admin, member).

- Invitation tokens should expire (e.g., 7 days) and be single-use.

- If an invite is re-sent, the old token should be invalidated.

- Admins can revoke pending invitations.

---

#### Login

POST /api/v1/users/auth/signin

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
POST /api/v1/users/auth/password-reset/request
POST /api/v1/users/auth/password-reset/confirm

---
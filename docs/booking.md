# Booking Architecture

## 1. Use the /availability endpoint

Your backend already provides available time slots via:
```
GET /api/v1/bookings/availability
```

Each slot has:

- start_at (UTC datetime)

- end_at (UTC datetime)

- user_id (worker for the slot)

The frontend will consume these slots to populate the calendar.

## 2. Frontend Calendar Integration

#### 1. Choose a Calendar Component

Examples:

```
React: react-big-calendar, FullCalendar

Vue: vue-cal

Angular: angular-calendar
```

#### 2. Convert API Response to Calendar Events

- Each availability object becomes a calendar event block:

```javascript
{
  id: "uuid-slot",
  title: "Available", // optionally include worker name
  start: "2025-09-14T10:00:00Z",
  end: "2025-09-14T11:30:00Z",
  workerId: "uuid-worker-1",
  available: true
}
```

#### 3. Display Only Available Slots

- Use color coding (e.g., green = available, gray = booked).

- Optionally, filter by worker or service.

#### 4. Handle Multi-Service Bookings

- Calculate total duration of selected services.

- Only show slots where a contiguous block exists that can fit all selected services.

---

## 3. Daily / Weekly Views

- Daily View: show all available slots for a selected day.

- Weekly View: show summary of worker availability by day; slots can be expanded on click.

- API call per day:
```
GET /api/v1/bookings/availability?company_id=xxx&date=2025-09-14&service_ids=[a,b]
```

- The frontend can pre-fetch multiple days to render a full week or month view.

## 4. Handling Time Zones

- Store all backend times in UTC.

- Convert times to customer’s local timezone on the frontend.

- Keep slots aligned with worker availability.

## 5. Selecting a Slot

- Customer clicks an available slot.

- Frontend records start_at, end_at, and optionally user_id (worker).

- Send selection to Create Booking endpoint:

```json
{
  "company_id": "uuid-company",
  "start_at": "2025-09-14T10:00:00Z",
  "services": [
    { "company_service_id": "uuid-haircut", "user_id": "uuid-worker-1" },
    { "company_service_id": "uuid-massage", "user_id": "uuid-worker-1" }
  ],
  "notes": "Customer note"
}
```

## 6. Optional Enhancements

- Slot Blocking: temporarily mark slots as “reserved” while customer is completing booking.

- Worker Filtering: allow customer to choose a preferred worker.

- Service-specific durations: recalculate available slots dynamically if the customer changes services.

- Visual cues: use colors/icons for booked vs available vs partially available times.


---

---

# Booking API

Base URL:  

```
/api/v1/bookings
```

---

## 1. Create Booking

Create a new booking session for a customer with one or more services.

**Endpoint:**  
```
POST /api/v1/bookings
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "company_id": "uuid-company",
  "start_at": "2025-09-14T14:00:00Z",
  "services": [
    {
      "company_service_id": "uuid-haircut",
      "user_id": "uuid-worker-1",
      "notes": "Include hair wash"
    },
    {
      "company_service_id": "uuid-massage",
      "user_id": "uuid-worker-2",
      "notes": ""
    }
  ],
  "notes": "Customer requested quiet room"
}
```

**Server Behavior**:

- Decode access_token to get customer_id.
- Validate requested company_id and services.
- Create a booking session and associated booking_services.
- Calculate total_price and end_at based on service durations.

Response (201 Created):

```json
{
  "id": "uuid-booking",
  "customer_id": "uuid-customer",   // extracted from access token
  "company_id": "uuid-company",
  "status": "pending",
  "start_at": "2025-09-14T14:00:00Z",
  "end_at": "2025-09-14T15:30:00Z",
  "total_price": 120.0,
  "notes": "Customer requested quiet room",
  "services": [
    {
      "id": "uuid-booking-service-1",
      "company_service_id": "uuid-haircut",
      "user_id": "uuid-worker-1",
      "duration": 30,
      "price": 50.0,
      "notes": "Include hair wash",
      "start_at": "2025-09-14T14:00:00Z",
      "end_at": "2025-09-14T14:30:00Z"
    },
    {
      "id": "uuid-booking-service-2",
      "company_service_id": "uuid-massage",
      "user_id": "uuid-worker-2",
      "duration": 60,
      "price": 70.0,
      "notes": "",
      "start_at": "2025-09-14T14:30:00Z",
      "end_at": "2025-09-14T15:30:00Z"
    }
  ]
}
```

Notes:

- customer_id is automatically determined from the access token; clients do not need to provide it in the request.

- Ensures bookings can only be created for the authenticated customer.

- Supports multi-service bookings with different workers assigned per service.

---

## 2. Get Booking by ID

Retrieve detailed information for a specific booking for the authenticated customer.

**Endpoint:**  
```
GET /api/v1/bookings/{booking_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "uuid-booking",
  "customer_id": "uuid-customer",  // from access token
  "company_id": "uuid-company",
  "status": "confirmed",
  "start_at": "2025-09-14T14:00:00Z",
  "end_at": "2025-09-14T15:30:00Z",
  "total_price": 120.0,
  "notes": "Customer requested quiet room",
  "services": [
    {
      "id": "uuid-booking-service-1",
      "company_service_id": "uuid-haircut",
      "user_id": "uuid-worker-1",
      "duration": 30,
      "price": 50.0,
      "notes": "Include hair wash",
      "start_at": "2025-09-14T14:00:00Z",
      "end_at": "2025-09-14T14:30:00Z"
    }
  ]
}
```

---

### 3. List Bookings

Retrieve multiple bookings for the authenticated customer (or filter by company/worker if admin).

Endpoint:
```
GET /api/v1/bookings
```

Headers:
```
Authorization: Bearer <access_token>
```

Query Parameters (optional):

```
company_id
user_id
status
start_date
end_date
```

Response (200 OK):

```json
[
  {
    "id": "uuid-booking",
    "customer_id": "uuid-customer",
    "company_id": "uuid-company",
    "status": "confirmed",
    "start_at": "2025-09-14T14:00:00Z",
    "end_at": "2025-09-14T15:30:00Z",
    "total_price": 120.0
  },
  ...
]
```

---

### 4. Update Booking

Update booking status, notes, or assigned workers for services. Only allowed for customer or company admin depending on permissions.

Endpoint:
```
PATCH /api/v1/bookings/{booking_id}
```

Headers:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request Body (example):

```json
{
  "status": "confirmed",
  "notes": "Updated note",
  "services": [
    {
      "booking_service_id": "uuid-booking-service-1",
      "user_id": "uuid-new-worker",
      "notes": "Updated notes"
    }
  ]
}
```

Response (200 OK):

```json
{
  "id": "uuid-booking",
  "status": "confirmed",
  "notes": "Updated note",
  "services": [
    {
      "id": "uuid-booking-service-1",
      "company_service_id": "uuid-haircut",
      "user_id": "uuid-new-worker",
      "duration": 30,
      "price": 50.0,
      "notes": "Updated notes",
      "start_at": "2025-09-14T14:00:00Z",
      "end_at": "2025-09-14T14:30:00Z"
    }
  ]
}
```

---

### 5. Cancel Booking

Cancel a booking (soft delete or update status). Only allowed for customer or company admin.

Endpoint:
```
POST /api/v1/bookings/{booking_id}/cancel
```

Headers:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request Body (optional):

```json
{
  "reason": "Customer requested cancellation"
}
```

Response (200 OK):

```json
{
  "id": "uuid-booking",
  "status": "cancelled",
  "notes": "Customer requested cancellation"
}
```

### 6. Check Available Time Slots

Retrieve available booking slots for a company or specific worker.

#### How It Works (Backend Logic)

- Get all workers for the company (or specific worker if user_id is provided).

- Retrieve weekly availability for each worker (user_availability).

- Remove time-off periods (user_time_off).

- Remove slots already booked (bookings + booking_services).

- Slice remaining time into slots matching total duration of requested service_ids.

- Return the available slots with start_at and end_at.

Endpoint:
```
GET /api/v1/bookings/availability
```

Headers:
```
Authorization: Bearer <access_token>
```

Query Parameters:
```
company_id (required)
user_id (optional)
service_ids (array, required)
date (required, YYYY-MM-DD)
```

Response (200 OK):

```json
[
  {
    "start_at": "2025-09-14T10:00:00Z",
    "end_at": "2025-09-14T11:30:00Z"
  },
  {
    "start_at": "2025-09-14T12:00:00Z",
    "end_at": "2025-09-14T13:30:00Z"
  }
]
```

Notes:

- Calculates available slots based on user_availability, user_time_off, and existing bookings.

- Returns slots suitable for the requested services’ total duration.

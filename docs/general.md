# Salona Booking System – REST API Documentation

## Overview

The Salona Booking System API provides endpoints to manage salon services, appointments, and customer interactions.


**Base URL**:

http://www.salona.app/api


## Endpoints

### Root Endpoint

**Request**

GET /

**Description**  
Checks if the Salona Booking System application is running.

**Response**  
- **200 OK** – Returns the application name and status.

**Example Response**
```json
{
  "application": "Salona Booking System",
  "status": "running"
}

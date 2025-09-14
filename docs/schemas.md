# Database Schemas – Salona Booking System (Initial Draft)


### Users
- `id`:	UUID	Unique identifier for the user
- `email`:	String(255)	Unique email, used for login
- `password_hash`:	String	Hashed password (bcrypt/argon2id)
- `first_name`:	String(100)	User’s first name
- `last_name`:	String(100)	User’s last name
- `status`:	Enum	active, pending_verification, disabled
- `email_verified`:	Boolean	Whether email is confirmed
- `created_at`:	DateTime	Timestamp of creation
- `updated_at`:	DateTime	Timestamp of last update

### User Emails
- `id`:	UUID	Unique ID for the email record
- `user_id`:	UUID	FK to users.id
- `email`:	String(255)	Email
- `status`:	Enum	primary, secondary, unverified
- `created_at`:	Datetime    Added timestamp

### User Phones
- `id`:	UUID	Unique ID for the phone record
- `user_id`:	UUID	FK to users.id
- `phone`:	String(20)	Phone number
- `status`:	Enum	primary, secondary, unverified
- `created_at`:	Datetime    Added timestamp

### User Addresses
- `id`:	UUID	Unique ID for the adress record
- `user_id`:	UUID	FK to users.id
- `address`:	String	Street address
- `city`:	String	City
- `country`:	String	Country
- `zip`:	String(20)	Postal code
- `created_at`:	Datetime    Added timestamp



### Companies

- `id`:	UUID	Unique identifier for the company
- `name`:	String(255)	Company name
- `type`:	String(255)	Type of company business
- `logo_url`:	String	Company logo url
- `website`:	String(255)	Company website
- `description`:	String(4000)	Description for company
- `team-size`: Number   Team size of company
- `status`: Enum    active, suspended
- `created_at`:	DateTime	Timestamp of creation
- `updated_at`:	DateTime	Timestamp of last update

### Company Emails
- `id`:	UUID	Unique ID for the email record
- `company_id`:	UUID	FK to companies.id
- `email`:	String(255)	Email
- `status`:	Enum	primary, secondary, unverified, billing
- `created_at`:	Datetime    Added timestamp

### Company Phones
- `id`:	UUID	Unique ID for the phone record
- `company_id`:	UUID	FK to companies.id
- `phone`:	String(20)	Phone number
- `status`:	Enum	primary, secondary, unverified, billing
- `created_at`:	Datetime    Added timestamp

### Company Addresses
- `id`:	UUID	Unique ID for the adress record
- `company_id`:	UUID	FK to companies.id
- `address`:	String	Street address
- `city`:	String	City
- `country`:	String	Country
- `zip`:	String(20)	Postal code
- `created_at`:	Datetime    Added timestamp

---

---

### Customers
- `id`:	UUID	Unique identifier for the user
- `email`:	String(255)	Unique email, used for login
- `password_hash`:	String	Hashed password (bcrypt/argon2id)
- `first_name`:	String(100)	User’s first name
- `last_name`:	String(100)	User’s last name
- `status`:	Enum	active, pending_verification, disabled
- `email_verified`:	Boolean	Whether email is confirmed
- `created_at`:	DateTime	Timestamp of creation
- `updated_at`:	DateTime	Timestamp of last update

### Customer Emails
- `id`:	UUID	Unique ID for the email record
- `customer_id`:	UUID	FK to customers.id
- `email`:	String(255)	Email
- `status`:	Enum	primary, secondary, unverified, billing
- `created_at`:	Datetime    Added timestamp

### Customer Phones
- `id`:	UUID	Unique ID for the phone record
- `customer_id`:	UUID	FK to customers.id
- `phone`:	String(20)	Phone number
- `status`:	Enum	primary, secondary, unverified, billing
- `created_at`:	Datetime    Added timestamp

### Customer Addresses
- `id`:	UUID	Unique ID for the adress record
- `customer_id`:	UUID	FK to customers.id
- `address`:	String	Street address
- `city`:	String	City
- `country`:	String	Country
- `zip`:	String(20)	Postal code
- `created_at`:	Datetime    Added timestamp


---

---

---

## Booking / Appointment Schema (Multi-Service)

### Bookings

Represents a customer appointment session at a company. A single booking can include multiple services.

| Field         | Type     | Description                                                 |
| ------------- | -------- | ----------------------------------------------------------- |
| `id`          | UUID     | Unique booking ID                                           |
| `customer_id` | UUID     | FK → `customers.id`                                         |
| `company_id`  | UUID     | FK → `companies.id`                                         |
| `status`      | Enum     | `pending`, `confirmed`, `cancelled`, `completed`, `no_show` |
| `start_at`    | DateTime | Start timestamp of first service (UTC)                      |
| `end_at`      | DateTime | End timestamp of last service (UTC)                         |
| `total_price` | Decimal  | Sum of all service prices                                   |
| `notes`       | Text     | Optional global notes                                       |
| `created_at`  | DateTime | Timestamp of booking creation                               |
| `updated_at`  | DateTime | Timestamp of last update                                    |


### Booking Services

Links a booking to one or more company services.

| Field                | Type     | Description                                                           |
| -------------------- | -------- | --------------------------------------------------------------------- |
| `id`                 | UUID     | Unique booking-service ID                                             |
| `booking_id`         | UUID     | FK → `bookings.id`                                                    |
| `company_service_id` | UUID     | FK → `company_services.id`                                            |
| `user_id`            | UUID     | FK → `users.id` (worker assigned, optional)                           |
| `duration`           | Integer  | Duration of this service in minutes (optional override)               |
| `price`              | Decimal  | Price of this service (optional override)                             |
| `notes`              | Text     | Optional note specific to this service                                |
| `start_at`           | DateTime | Optional start timestamp for this service (if scheduled sequentially) |
| `end_at`             | DateTime | Optional end timestamp for this service                               |




### Global Services

All services available in the system (predefined).

| Field              | Type        | Description                                  |
| ------------------ | ----------- | -------------------------------------------- |
| `id`               | UUID        | Unique service ID                            |
| `name`             | String(255) | Name of the service (e.g., Haircut, Massage) |
| `default_duration` | Integer     | Default duration in minutes                  |
| `default_price`    | Decimal     | Base price                                   |
| `description`      | Text        | Optional description                         |
| `created_at`       | DateTime    | Timestamp                                    |
| `updated_at`       | DateTime    | Timestamp                                    |


### Company Services

Defines services offered by a company.

| Field             | Type     | Description                                 |
| ----------------- | -------- | ------------------------------------------- |
| `id`              | UUID     | Unique ID                                   |
| `company_id`      | UUID     | FK → `companies.id`                         |
| `service_id`      | UUID     | FK → `services.id`                          |
| `custom_duration` | Integer  | Optional override duration for this company |
| `custom_price`    | Decimal  | Optional override price for this company    |
| `created_at`      | DateTime | Timestamp                                   |
| `updated_at`      | DateTime | Timestamp                                   |


### User Availability

Defines recurring weekly working hours for a user (worker).

| Field         | Type     | Description                         |
| ------------- | -------- | ----------------------------------- |
| `id`          | UUID     | Unique availability ID              |
| `user_id`     | UUID     | FK → `users.id`                     |
| `day_of_week` | Integer  | 0=Sunday, 1=Monday … 6=Saturday     |
| `start_time`  | Time     | Start time in user's local timezone |
| `end_time`    | Time     | End time in user's local timezone   |
| `created_at`  | DateTime | Timestamp                           |
| `updated_at`  | DateTime | Timestamp                           |


### User Time Off

Stores periods when a user is unavailable (vacation, sick leave, etc.)

| Field        | Type     | Description             |
| ------------ | -------- | ----------------------- |
| `id`         | UUID     | Unique time-off ID      |
| `user_id`    | UUID     | FK → `users.id`         |
| `start_at`   | DateTime | Start of time off (UTC) |
| `end_at`     | DateTime | End of time off (UTC)   |
| `reason`     | String   | Optional reason         |
| `created_at` | DateTime | Timestamp               |
| `updated_at` | DateTime | Timestamp               |

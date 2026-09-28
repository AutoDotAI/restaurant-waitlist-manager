# Restaurant Waitlist Manager

## 1. Product Goal

Build a same-day restaurant waitlist management platform for:

- Restaurant hosts/receptionists
- Restaurant managers
- Customers

The product should replace paper lists, spreadsheets, or ad-hoc messaging with a simple digital queue.

The system is **not a reservation platform**.

The core experience is:

1. A guest joins the restaurant's waitlist.
2. The system estimates their wait time.
3. Restaurant staff manage and reorder the queue.
4. The guest receives SMS updates.
5. When the restaurant is ready for them, the guest confirms that they are coming.
6. Staff seat or remove the guest.

---

# 2. User Types

## 2.1 Host / Restaurant Staff

Primary operational user.

Can:

- Add walk-in guests.
- View the current waitlist.
- Reorder guests.
- Edit guest information.
- Change estimated wait times.
- Notify guests.
- Mark guests as seated, cancelled, no-show, etc.
- Override system recommendations.
- Open or close remote waitlist joining.

## 2.2 Restaurant Manager

Has all host capabilities plus administrative access.

Can:

- Configure restaurant settings.
- Configure wait-time rules.
- Manage staff accounts.
- View basic historical statistics.
- Configure SMS settings.
- Configure remote waitlist behavior.

For MVP, manager and host interfaces may share the same dashboard with role-based permissions.

## 2.3 Customer

Can:

- Join the waitlist remotely.
- See their estimated wait.
- Receive SMS updates.
- Confirm they are coming when called.
- Cancel their place in the waitlist.

Customers do not need an account.

---

# 3. Joining the Waitlist

There are two supported entry methods.

## 3.1 Host-Added Walk-In

Restaurant staff create an entry from the host dashboard.

Required fields:

- Customer name
- Phone number
- Party size

Optional internal field:

- Staff notes

Example:

```text
Name: Sarah
Phone: +33 6 12 34 56 78
Party size: 4
```

The guest immediately enters the active waitlist.

---

## 3.2 Remote Join

Customers access a restaurant-specific web page such as:

```text
app.example.com/r/big-mamma
```

Required information:

- Name
- Phone number
- Party size

Before submitting, the customer sees:

- Current estimated wait range
- Restaurant status
- Whether remote joining is currently open

The restaurant controls whether remote joining is enabled.

Possible states:

```text
Remote waitlist: OPEN
Remote waitlist: CLOSED
```

If closed, customers cannot join remotely.

---

# 4. Remote Guest Priority

Remote guests operate under a hybrid model.

Joining remotely places them into the waitlist, but they are expected to arrive within a configurable arrival window.

Default MVP setting:

```text
Arrival window: 30 minutes
```

Staff may manually override this.

Example:

A customer joins remotely at 19:00.

Expected arrival:

```text
Before 19:30
```

If the customer has not arrived when they are close to being seated, the host may:

- Delay them
- Move them down the queue
- Keep their position
- Remove them

No automatic GPS tracking is required.

No customer geolocation is required.

---

# 5. Waitlist Queue

The host dashboard displays the active queue.

Example:

| Order | Guest | Party | Source | Wait | Status |
|---|---|---:|---|---:|---|
| 1 | Sarah | 2 | Walk-in | 10 min | Waiting |
| 2 | Julien | 4 | Remote | 15 min | Arrived |
| 3 | Emma | 3 | Remote | 25 min | En route |
| 4 | David | 2 | Walk-in | 30 min | Waiting |

The queue order is controlled by restaurant staff.

Staff can freely reorder guests using drag-and-drop.

The system does not enforce strict FIFO ordering.

This is intentional because restaurants may need to prioritize based on operational circumstances.

---

# 6. Guest Statuses

Each waitlist entry has one current status.

MVP statuses:

```text
WAITING
ARRIVED
NOTIFIED
CONFIRMED
SEATED
CANCELLED
NO_SHOW
REMOVED
```

Typical lifecycle:

```text
WAITING
   ↓
NOTIFIED
   ↓
CONFIRMED
   ↓
SEATED
```

Remote customer example:

```text
WAITING
   ↓
ARRIVED
   ↓
NOTIFIED
   ↓
CONFIRMED
   ↓
SEATED
```

Terminal states:

```text
SEATED
CANCELLED
NO_SHOW
REMOVED
```

Terminal guests disappear from the active queue but remain in history.

---

# 7. Estimated Wait Time

Wait times use a **rule-based system**.

No AI/ML prediction is required for MVP.

The system calculates a baseline estimate using:

- Number of parties ahead
- Party sizes
- Restaurant-configured average turnover assumptions
- Manual restaurant configuration

Example configuration:

```text
Base wait per queue group: 7 minutes

Party-size modifier:
1–2 guests: 1.0x
3–4 guests: 1.2x
5–6 guests: 1.5x
7+ guests: 2.0x
```

Example:

```text
3 parties ahead
Base queue time = 7 minutes

Estimated wait ≈ 21 minutes
```

The exact algorithm should remain configurable.

Hosts can always override the displayed wait.

Example:

```text
System estimate: 28 min
Host override: 40 min
```

Customer sees:

```text
Estimated wait: about 40 minutes
```

Customers never see their exact numerical queue position.

---

# 8. Customer Waitlist Page

After joining remotely, the customer receives a private status page.

Example:

```text
You're on the waitlist

Party: 3 people
Estimated wait: ~25 minutes

We'll text you when your table is nearly ready.
```

The page can update periodically.

Customers may:

- View estimated wait
- Confirm arrival
- Cancel their place

They cannot:

- See other guests
- See their exact queue position
- Modify party size after joining

Party-size changes require staff intervention for MVP.

---

# 9. SMS Notifications

SMS is the only required notification channel for MVP.

No:

- Email
- WhatsApp
- Push notifications

required initially.

## SMS 1 — Waitlist Confirmation

Example:

```text
You're on the waitlist at Restaurant ABC.

Estimated wait: ~30 minutes.

Track your wait:
[link]
```

## SMS 2 — Table Nearly Ready

Example:

```text
Your table at Restaurant ABC is nearly ready.

Please confirm that you're coming:
[Confirm]

Can't make it?
[Cancel]
```

## SMS 3 — Confirmation Received

Example:

```text
Thanks — we've confirmed you're coming.

Please head to the restaurant.
```

SMS links should use secure random tokens.

Customers should not be required to log in.

---

# 10. Guest Confirmation

When staff notify a customer, the guest receives an SMS link.

The customer can select:

```text
I'm coming
Cancel
```

If they select **I'm coming**:

```text
Status → CONFIRMED
```

The host dashboard updates immediately.

If they select **Cancel**:

```text
Status → CANCELLED
```

Restaurant staff retain full override control.

---

# 11. Grace Period

Once a customer is notified that the restaurant is ready for them, a grace period begins.

Default:

```text
10 minutes
```

The host dashboard should show:

```text
Notified 6 min ago
```

or:

```text
Grace period expired
```

The system does not automatically remove the guest.

Staff decide whether to:

- Keep them
- Move them down
- Mark no-show
- Remove them

---

# 12. Host Dashboard

The host dashboard is the core application screen.

It should provide:

### Queue Overview

Large, easy-to-scan waitlist.

### Fast Add Guest

Prominent button:

```text
+ Add Guest
```

The host should be able to add a guest in approximately 10 seconds.

### Queue Actions

For each guest:

- Notify
- Mark arrived
- Edit
- Move
- Seat
- Cancel
- Mark no-show
- Remove

### Drag-and-Drop Queue

Guests can be manually reordered.

### Remote Waitlist Toggle

Prominent control:

```text
Remote Join

[ OPEN / CLOSED ]
```

This needs to be accessible without going into settings.

---

# 13. Table Assignment

The system does **not** manage a restaurant floor plan.

It does not track:

- Exact tables
- Table occupancy
- Server sections
- Table combinations
- Floor layouts

For MVP, table assignment is outside the application's scope.

However, the architecture should allow future support for:

```text
Suggested table
Automatic table assignment
Floor management
```

without requiring a major rewrite.

---

# 14. Restaurant Configuration

Each restaurant has configurable settings.

MVP settings:

```text
Restaurant name
Timezone
Phone country code
Remote waitlist enabled/disabled
Default remote arrival window
Default grace period
Wait-time calculation settings
Maximum accepted party size
SMS sender configuration
```

Suggested defaults:

```text
Arrival window: 30 min
Grace period: 10 min
Max party size: 12
```

---

# 15. Remote Waitlist Opening

Remote joining is manually controlled by restaurant staff.

Example:

```text
11:00 — CLOSED
18:30 — Host switches OPEN
21:45 — Host switches CLOSED
```

If closed, existing waitlist guests remain active.

Closing only prevents new remote joins.

Hosts can always add walk-in guests.

---

# 16. Basic Manager Analytics

Keep analytics minimal for MVP.

Manager should be able to see:

```text
Guests served today
Average estimated wait
Average actual wait
Number of cancellations
Number of no-shows
Walk-in vs remote joins
Average party size
```

Historical views:

```text
Today
Last 7 days
Last 30 days
```

Advanced BI is out of scope.

---

# 17. Staff Accounts

Restaurant managers can create staff users.

Suggested roles:

```text
Manager
Host
```

### Host

Can manage the active waitlist.

### Manager

Can additionally:

- Manage users
- Modify restaurant configuration
- View analytics

---

# 18. Multi-Restaurant Architecture

MVP UI may initially focus on one restaurant/location per workspace.

However, the backend should be tenant-aware from day one.

Data model:

```text
Organization
    ↓
Restaurant
    ↓
Staff / Waitlist / Settings
```

This makes future support for restaurant groups straightforward.

Example:

```text
Big Mamma Group
├── Ober Mamma
├── Pink Mamma
└── East Mamma
```

Multi-location management does not need to be exposed in the first MVP UI.

---

# 19. Core Data Model

## Restaurant

```text
id
name
timezone
remote_join_enabled
arrival_window_minutes
grace_period_minutes
created_at
```

## StaffUser

```text
id
restaurant_id
name
email
role
created_at
```

## WaitlistEntry

```text
id
restaurant_id

customer_name
phone_number
party_size

source:
- WALK_IN
- REMOTE

status

estimated_wait_minutes
manual_wait_override

queue_position

joined_at
expected_arrival_at
arrived_at

notified_at
confirmed_at
seated_at
cancelled_at

staff_notes

created_at
updated_at
```

## SMSMessage

```text
id
waitlist_entry_id
phone_number
message_type
provider_message_id
status
sent_at
```

---

# 20. Security / Privacy

Customer data should be minimal.

Store only what is operationally necessary:

```text
Name
Phone
Party size
Waitlist activity
```

Important controls:

- Staff authentication
- Tenant isolation
- Role-based permissions
- Rate limiting on public join endpoint
- Phone-number validation
- CSRF/XSS protections
- Secure random customer links
- Audit trail for important staff actions

Public waitlist tokens must not expose sequential database IDs.

Example:

```text
/r/status/hK8nQ2Lz9A
```

rather than:

```text
/waitlist/12345
```

---

# 21. Abuse Protection

Remote joining introduces abuse risks.

MVP should include:

- Rate limiting
- Duplicate phone-number detection
- CAPTCHA after suspicious activity
- Maximum active entry per phone number per restaurant
- Maximum configurable party size

Suggested rule:

```text
One active waitlist entry per phone number per restaurant.
```

---

# 22. Out of Scope for MVP

Explicitly exclude:

- Reservations
- Customer accounts
- Loyalty programs
- Payment
- Deposits
- Menu ordering
- POS integration
- Floor plans
- Table occupancy management
- Server assignments
- AI wait predictions
- GPS tracking
- WhatsApp
- Email notifications
- Push notifications
- Native mobile apps
- Dynamic pricing
- Review collection
- CRM / marketing campaigns

These may become later modules.

---

# 23. Primary User Flow

## Walk-In

```text
Guest arrives
      ↓
Host clicks Add Guest
      ↓
Name + phone + party size
      ↓
Wait estimate generated
      ↓
Guest enters queue
      ↓
Host presses Notify
      ↓
Guest receives SMS
      ↓
Guest confirms
      ↓
Host seats guest
```

## Remote Guest

```text
Customer opens restaurant page
      ↓
Enters name + phone + party size
      ↓
System shows estimated wait
      ↓
Customer joins
      ↓
Customer travels to restaurant
      ↓
Customer checks in / host marks arrived
      ↓
Wait estimate continues updating
      ↓
Host presses Notify
      ↓
SMS sent
      ↓
Customer confirms
      ↓
Host seats guest
```

---

# 24. MVP Screens

The first version requires approximately six core interfaces.

### 1. Staff Login

### 2. Host Waitlist Dashboard

The main operational screen.

### 3. Add/Edit Guest Modal

### 4. Restaurant Settings

### 5. Public Remote Join Page

### 6. Customer Wait Status / Confirmation Page

Manager analytics can either be a seventh screen or a tab inside the dashboard.

---

# 25. MVP Success Criteria

The MVP is successful if a restaurant can run an entire evening waitlist using the product without needing paper or another queue-management tool.

Specifically:

- Staff can add a guest in seconds.
- Remote customers can join without an account.
- Staff can understand the queue instantly.
- Staff retain full operational control.
- Customers receive reliable SMS notifications.
- Customers can confirm or cancel easily.
- Wait estimates are understandable and editable.
- No reservation or floor-management complexity is introduced.

---

# 26. Product Philosophy

The key design principle should be:

> **The system assists the host; it does not try to run the restaurant for them.**

Restaurants are operationally messy.

Party sizes change, customers disappear, tables become unexpectedly available, VIPs arrive, and hosts constantly make judgment calls.

Therefore:

```text
System = estimation + communication + organization

Host = final authority
```

This should guide the MVP architecture and UX.
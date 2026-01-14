# Registration Specification

Language-agnostic spec for creating event registrations. The frontend is implemented as a React SPA.

## Data Models

### Player
```
Player {
  id: int (primary key)
  first_name: string (max 30)
  last_name: string (max 30)
  email: string (unique, max 200)
  phone_number: string? (max 20)
  ghin: string? (unique, max 8)       // Golf Handicap ID
  tee: string (default "Club")
  birth_date: date?
  is_member: bool (default false)
  last_season: int?
  stripe_customer_id: string?
}
```

### Registration
```
Registration {
  id: int (primary key)
  event_id: int (FK -> Event)
  course_id: int? (FK -> Course)
  user_id: int? (FK -> User)
  signed_up_by: string? (max 40)      // name of person who registered
  expires: datetime?                   // when pending registration expires
  notes: string?
  created_date: datetime (auto)
}
```

### RegistrationSlot
```
RegistrationSlot {
  id: int (primary key)
  event_id: int (FK -> Event)
  hole_id: int? (FK -> Hole)
  registration_id: int? (FK -> Registration)
  player_id: int? (FK -> Player)
  starting_order: int (default 0)     // tee time index or A/B group (0/1)
  slot: int (default 0)               // position within group (0-3 typically)
  status: enum ["A","P","X","R","U"]
}

Constraints:
  - UNIQUE(event_id, player_id) - one slot per player per event
```

### RegistrationFee
```
RegistrationFee {
  id: int (primary key)
  event_fee_id: int (FK -> EventFee)
  registration_slot_id: int? (FK -> RegistrationSlot)
  payment_id: int? (FK -> Payment)
  is_paid: bool (default false)
  amount: decimal (max 5 digits, 2 decimals)
}
```

## Slot Status State Machine

```
States:
  A = Available       (slot open for selection)
  P = Pending         (reserved, awaiting payment)
  X = Payment Processing (payment in progress)
  R = Reserved        (confirmed/paid)
  U = Unavailable     (blocked, e.g., starter interval)

Transitions:
  A -> P : create_and_reserve()
  P -> X : payment_processing()
  X -> R : payment_confirmed()
  P -> A : expiry cleanup or user cancel (choosable events)
  P -> DELETE : expiry cleanup or user cancel (non-choosable events)
  X -> A : cancel_registration() (choosable)
  X -> DELETE : cancel_registration() (non-choosable)
  R -> A : drop with refund (choosable)
  R -> DELETE : drop with refund (non-choosable)
```

## Event Configuration Properties

Events have configuration that determines registration behavior:

```
Event {
  can_choose: bool           // true = player selects slots; false = slots created on demand
  start_type: enum ["TT","SG","NA"]  // TT=Tee Times, SG=Shotgun
  group_size: int?           // slots per group (for choosable events)
  maximum_signup_group_size: int?  // max players per registration
  minimum_signup_group_size: int?  // min players per registration
  total_groups: int?         // number of tee time groups (for choosable events)
  registration_maximum: int? // total event capacity (for non-choosable events)
  signup_start: datetime?
  signup_end: datetime?
  priority_signup_start: datetime?
  signup_waves: int?         // number of waves for priority signup
  registration_type: enum ["M","G","O","R","N"]  // M=Member, N=None
  starter_time_interval: int (default 0)  // every Nth slot is unavailable
}
```

### Event Types by `can_choose`

**Choosable Events** (`can_choose=true`):
- Slots pre-created when event is set up
- Player selects specific slot(s) to reserve
- Slot status managed: A -> P -> X -> R
- Expired slots return to Available status

**Non-Choosable Events** (`can_choose=false`):
- Slots created on-demand during registration
- System assigns slots automatically
- `maximum_signup_group_size` slots created per registration
- Expired/cancelled slots are deleted

## Registration Window

Computed property based on current time vs event dates:

```
registration_window(event):
  if event.registration_type == "N": return "n/a"
  now = current_time()
  if event.priority_signup_start && event.priority_signup_start < now < event.signup_start:
    return "priority"
  if event.signup_start < now < event.signup_end:
    return "registration"
  if now > event.signup_end:
    return "past"
  return "future"
```

## API: Create Registration

### Request

```
POST /api/registration/

Headers:
  Authorization: Token <user_token>
  Content-Type: application/json

Body (choosable event):
{
  "event": <event_id>,
  "course": <course_id>,           // required for choosable events
  "slots": [
    {"id": <slot_id>},
    {"id": <slot_id>}              // additional slots in same group
  ]
}

Body (non-choosable event):
{
  "event": <event_id>,
  "course": null,
  "slots": []
}
```

### Response

```
Success (201 Created):
{
  "id": <registration_id>,
  "event": <event_id>,
  "course": <course_id>,
  "signed_up_by": "John Doe",
  "notes": null,
  "expires": "2024-01-15T14:35:00Z",
  "created_date": "2024-01-15T14:30:00Z",
  "slots": [
    {
      "id": <slot_id>,
      "event": <event_id>,
      "hole": <hole_id>,
      "registration": <registration_id>,
      "starting_order": 0,
      "slot": 0,
      "status": "P",
      "player": {
        "id": <player_id>,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        ...
      }
    }
  ]
}
```

## Validation Rules

### Pre-Conditions (checked in order)

1. **Registration Window Open** 
   ```
   if event.registration_window not in ["registration", "priority"]:
     ERROR 400: "The event is not currently open for registration"
   ```

2. **Wave Availability** (priority window, choosable events with waves)
   ```
   if event.registration_window == "priority" && event.can_choose && event.signup_waves:
     requested_wave = get_starting_wave(event, starting_order, hole_number)
     current_wave = get_current_wave(event)
     if requested_wave > current_wave:
       ERROR 400: "Wave {requested_wave} times are not yet open for registration"
   ```

3. **Event Capacity**
   ```
   if event.registration_maximum > 0:
     reserved_count = count slots where event=event AND status="R"
     if reserved_count >= event.registration_maximum:
       ERROR 400: "The event field is full"
   ```

4. **No Duplicate Registration**
   ```
   existing = find registration where user=current_user AND event=event
   if existing has slots with status in ["R", "X"]:
     ERROR 400: "You already have a completed registration for this event"
   ```

5. **Slots Exist** (choosable events)
   ```
   requested_ids = [slot.id for slot in request.slots]
   found_slots = query slots where id in requested_ids (with row lock)
   if found_slots is empty:
     ERROR 409: "One or more of the slots you requested are not available"
   if len(found_slots) != len(requested_ids):
     ERROR 409: "One or more of the slots you requested have already been reserved"
   ```

6. **Slots Available** (choosable events)
   ```
   for slot in found_slots:
     if slot.status != "A":
       ERROR 409: "One or more of the slots you requested have already been reserved"
   ```

7. **Course Required** (choosable events)
   ```
   if event.can_choose && course_id is null:
     ERROR 400: "A course must be included when registering for this event"
   ```

## Business Logic: create_and_reserve()

Atomic transaction that creates registration and reserves slots.

```
function create_and_reserve(user, player, event, course, slots, signed_up_by):
  BEGIN TRANSACTION

  if event.can_choose:
    // Lock and validate slots
    slot_ids = [s.id for s in slots]
    db_slots = SELECT * FROM registration_slots
               WHERE id IN slot_ids
               FOR UPDATE  // row-level lock

    if db_slots is empty:
      RAISE MissingSlotsError
    if len(db_slots) != len(slot_ids):
      RAISE SlotConflictError
    for slot in db_slots:
      if slot.status != "A":
        RAISE SlotConflictError

    // Create or reuse registration
    reg = create_or_update_registration(event, user, course, signed_up_by)

    // Reserve slots
    for i, slot in enumerate(db_slots):
      if i == 0:
        slot.player = player  // first slot gets registering player
      slot.status = "P"
      slot.registration = reg
      slot.save()

  else:  // non-choosable event
    reg = create_or_update_registration(event, user, course, signed_up_by)

    // Create new slots
    for s in range(event.maximum_signup_group_size):
      slot = create RegistrationSlot(
        event=event,
        registration=reg,
        status="P",
        starting_order=0,
        slot=s
      )
      if s == 0:
        slot.player = player
      slot.save()

  COMMIT
  return reg
```

## Business Logic: create_or_update_registration()

Handles existing pending registrations for same user/event.

```
function create_or_update_registration(event, user, course, signed_up_by):
  existing = find registration where user=user AND event=event

  if existing:
    // Check for duplicate confirmed registration
    has_confirmed = existing.slots.any(status in ["R", "X"])
    if has_confirmed:
      RAISE AlreadyRegisteredError

    // Reset pending slots
    existing.slots.filter(status="P").update(
      status="A", player=null, registration=null
    )
    existing.course = course
    existing.signed_up_by = signed_up_by
    reg = existing
  else:
    reg = create Registration(
      event=event,
      course=course,
      user=user,
      signed_up_by=signed_up_by
    )

  // Set expiration
  if event.can_choose:
    reg.expires = now() + 5 minutes
  else:
    reg.expires = now() + 15 minutes

  reg.save()
  return reg
```

## Wave Calculation

For events with priority signup waves:

```
function get_current_wave(event):
  if no waves configured: return 999
  now = current_time()
  if now < event.priority_signup_start: return 0
  if now >= event.signup_start: return event.signup_waves + 1

  priority_duration = (event.signup_start - event.priority_signup_start) in minutes
  wave_duration = priority_duration / event.signup_waves
  elapsed = (now - event.priority_signup_start) in minutes
  return min(floor(elapsed / wave_duration) + 1, event.signup_waves)

function get_starting_wave(event, starting_order, hole_number):
  if no waves configured: return 1

  // For shotgun: combine hole and starting_order
  if event.start_type == "SG" && hole_number:
    effective_order = (hole_number - 1) * 2 + starting_order
  else:
    effective_order = starting_order

  // Distribute groups evenly across waves
  base = event.total_groups / event.signup_waves (integer division)
  remainder = event.total_groups % event.signup_waves
  cutoff = remainder * (base + 1)

  if effective_order < cutoff:
    return floor(effective_order / (base + 1)) + 1
  else:
    return remainder + floor((effective_order - cutoff) / base) + 1
```

## Expiry Cleanup

Scheduled task to clean up expired pending registrations:

```
function clean_up_expired():
  now = current_time()
  expired = SELECT registrations WHERE expires < now AND has slots with status="P"

  for reg in expired:
    // Choosable: return slots to available
    UPDATE registration_slots
    SET status="A", registration=null, player=null
    WHERE registration=reg AND status="P" AND event.can_choose=true

    // Non-choosable: delete slots
    DELETE FROM registration_slots
    WHERE registration=reg AND status="P" AND event.can_choose=false

    // Delete empty registrations
    if reg.slots.count() == 0:
      DELETE reg
```

## Error Codes

| Error | HTTP | Message |
|-------|------|---------|
| SlotConflictError | 409 | "One or more of the slots you requested have already been reserved" |
| MissingSlotsError | 409 | "One or more of the slots you requested are not available" |
| PlayerConflictError | 409 | "The player selected has already signed up or is in the process of signing up" |
| AlreadyRegisteredError | 400 | "You already have a completed registration for this event" |
| EventFullError | 400 | "The event field is full" |
| EventRegistrationNotOpenError | 400 | "The event is not currently open for registration" |
| EventRegistrationWaveError | 400 | "Wave {N} times are not yet open for registration" |
| CourseRequiredError | 400 | "A course must be included when registering for this event" |

## Concurrency Handling

- Use `SELECT ... FOR UPDATE` (row-level locking) when checking slot availability
- Wrap slot reservation in atomic transaction
- Lock slots before checking status to prevent race conditions

---

## Payment Flow

After registration creation, payment must be collected before slots are confirmed.

### Payment Model
```
Payment {
  id: int (primary key)
  payment_code: string (max 40)        // Stripe PaymentIntent ID (e.g., "pi_xxx")
  payment_key: string? (max 100)       // Stripe client secret
  payment_amount: decimal (5,2)        // amount paid
  transaction_fee: decimal (4,2)       // processing fees
  event_id: int (FK -> Event)
  user_id: int (FK -> User)
  notification_type: enum? ["A","N","R","C","M","U"]
  confirmed: bool (default false)
  payment_date: datetime (auto)
  confirm_date: datetime?
}
```

### Refund Model
```
Refund {
  id: int (primary key)
  payment_id: int (FK -> Payment)
  refund_code: string (unique, max 40)  // Stripe Refund ID
  refund_amount: decimal (5,2)
  issuer_id: int (FK -> User)
  notes: string?
  confirmed: bool (default false)
  refund_date: datetime (auto)
}
```

### Payment Lifecycle

```
1. Registration Created (slots in "P" status)
   |
   v
2. Client requests PaymentIntent
   POST /api/payment/{payment_id}/payment_intent/
   -> Creates Stripe PaymentIntent
   -> Stores payment_code (pi_xxx) and payment_key
   -> Transitions slots: P -> X (payment_processing)
   |
   v
3. Client submits payment to Stripe (frontend)
   |
   v
4. Stripe sends webhook on success
   POST /stripe/webhook/clover/
   event.type = "payment_intent.succeeded"
   |
   v
5. handle_payment_complete() task
   -> Updates Payment: confirmed=true, confirm_date=now
   -> Updates RegistrationFees: is_paid=true
   -> Transitions slots: X -> R (payment_confirmed)
   -> Updates membership if event_type="R"
   -> Sends confirmation email
```

### API: Create PaymentIntent

```
POST /api/payment/{payment_id}/payment_intent/

Headers:
  Authorization: Token <user_token>

Body:
{
  "event_id": <event_id>,
  "registration_id": <registration_id>
}

Response (200):
{
  "id": "pi_xxx",
  "client_secret": "pi_xxx_secret_yyy",
  "status": "requires_payment_method",
  ...
}
```

### Business Logic: payment_processing()

Transitions pending slots to processing status.

```
function payment_processing(registration_id):
  reg = get_registration(registration_id)

  // Transition slots with players to processing
  UPDATE registration_slots
  SET status="X"
  WHERE registration=reg AND status="P" AND player IS NOT NULL

  // Handle empty slots
  if reg.event.can_choose:
    // Return to available
    UPDATE registration_slots
    SET status="A", player=null, registration=null
    WHERE registration=reg AND status="P" AND player IS NULL
  else:
    // Delete unused slots
    DELETE FROM registration_slots
    WHERE registration=reg AND status="P" AND player IS NULL
```

### Business Logic: payment_confirmed()

Called via Stripe webhook when payment succeeds.

```
function payment_confirmed(registration_id):
  reg = get_registration(registration_id)

  // Finalize reservation
  UPDATE registration_slots
  SET status="R"
  WHERE registration=reg AND status="X"

  return reg
```

### Fee Calculation

Before creating PaymentIntent, calculate total with processing fees:

```
function calculate_payment_amount(amount_due):
  // Stripe fee structure: 2.9% + $0.30
  stripe_percentage = 0.029
  stripe_fixed = 0.30

  // Calculate amount that after fees equals amount_due
  total = (amount_due + stripe_fixed) / (1 - stripe_percentage)
  fee = total - amount_due

  return (total, fee)
```

### Refund Flow

```
function create_refund(user, payment, amount, notes):
  // Create Stripe refund
  stripe_refund = stripe.Refund.create(
    payment_intent=payment.payment_code,
    amount=int(amount * 100)  // cents
  )

  // Create local record
  refund = create Refund(
    payment=payment,
    refund_code=stripe_refund.id,
    refund_amount=amount,
    issuer=user,
    notes=notes,
    confirmed=false
  )

  return refund
```

Refund confirmation comes via webhook when Stripe completes processing.

### Cancel Registration

Cancel a registration if possible:

```
function cancel_registration(registration_id, payment_id, reason):
  BEGIN TRANSACTION

  reg = get_registration(registration_id)

  // Clear or delete slots
  if reg.event.can_choose:
    UPDATE registration_slots
    SET status="A", player=null, registration=null
    WHERE registration=reg AND status IN ("P", "X")
  else:
    DELETE FROM registration_slots
    WHERE registration=reg AND status IN ("P", "X")

  DELETE reg

  // Cancel Stripe payment if exists
  if payment_id:
    payment = get_payment(payment_id)
    DELETE payment.payment_details
    if payment.payment_code starts with "pi_":
      stripe.PaymentIntent.cancel(payment.payment_code)
    DELETE payment

  COMMIT
```

---

## Complete Registration + Payment Sequence

```
+----------+     +----------+     +-----------+     +---------+
| Client   |     |   API    |     | Database  |     | Stripe  |
+----+-----+     +----+-----+     +-----+-----+     +----+----+
     |               |                 |                |
     | POST /registration              |                |
     |-------------->|                 |                |
     |               | validate        |                |
     |               | create_and_reserve()             |
     |               |---------------->|                |
     |               |                 | slots: A->P    |
     |               |<----------------|                |
     | {registration, slots, expires}  |                |
     |<--------------|                 |                |
     |               |                 |                |
     | POST /payment (create Payment record)            |
     |-------------->|                 |                |
     |               |---------------->|                |
     | {payment_id}  |<----------------|                |
     |<--------------|                 |                |
     |               |                 |                |
     | POST /payment/{id}/payment_intent                |
     |-------------->|                 |                |
     |               | payment_processing()             |
     |               |---------------->|                |
     |               |                 | slots: P->X    |
     |               |                 |                |
     |               |------------------------------->  |
     |               |                 |  PaymentIntent |
     |               |<-------------------------------- |
     | {client_secret}                 |                |
     |<--------------|                 |                |
     |               |                 |                |
     | confirmPayment(client_secret)   |                |
     |-------------------------------------------->     |
     |               |                 |                |
     |               | webhook: payment_intent.succeeded|
     |               |<---------------------------------|
     |               | payment_confirmed()              |
     |               |---------------->|                |
     |               |                 | slots: X->R    |
     |               |                 | payment.confirmed=true
     |               |                 | fees.is_paid=true
     |               |<----------------|                |
     |               | 200 OK          |                |
     |               |--------------------------------->|
     |               |                 |                |
```

---

## Current Python Implementation

### Registration Manager

```python
class RegistrationManager(models.Manager):

    def clean_up_expired(self):
        current_time = tz.localtime(tz.now(), timezone=ZoneInfo("America/Chicago"))

        registrations = self \
            .filter(expires__lt=current_time) \
            .filter(slots__status="P")
        count = len(registrations)

        for reg in registrations:
            logger.info("Cleaning up expired registration", currentTime=current_time, expiry=reg.expires,
                        registrationId=reg.id, user=reg.signed_up_by)

            # Make can_choose slots available
            reg.slots \
                .filter(status="P") \
                .filter(event__can_choose=True) \
                .update(**{"status": "A", "registration": None, "player": None})

            # Delete other slots
            reg.slots \
                .filter(status="P") \
                .exclude(event__can_choose=True) \
                .delete()

            if len(reg.slots.all()) == 0:
                reg.delete()

        return count

    @transaction.atomic()
    def create_and_reserve(self, user, player, event, course, registration_slots, signed_up_by):

        """
        Reserve one or more signup slots for a user’s registration on an event.
        
        Parameters:
        	user: The Django User who owns the registration.
        	player: The Player to assign to the first reserved slot (or slot 0 for non-choosable events).
        	event: The Event for which slots are being reserved.
        	course: The Course instance associated with the reservation.
        	registration_slots (list[dict] | iterable): For choosable events, an iterable of slot descriptors containing at least an "id" key identifying slots to reserve.
        	signed_up_by: The user performing the signup action (may differ from `user`).
        
        Returns:
        	registration: The created or updated Registration instance linked to the reserved slots.
        
        Raises:
        	MissingSlotsError: If none of the requested slot IDs exist.
        	SlotConflictError: If some requested slots are missing or any requested slot is not available ("A").
        """
        if event.can_choose:
            slot_ids = [slot["id"] for slot in registration_slots]
            logger.info("Checking slots", eventId=event.id, course=course.name, user=signed_up_by, slots=slot_ids)

            slots = list(event.registrations.select_for_update().filter(pk__in=slot_ids))

            if slots is None or len(slots) == 0:
                raise MissingSlotsError()

            if len(slots) != len(slot_ids):
                raise SlotConflictError()

            for s in slots:
                if s.status != "A":
                    raise SlotConflictError()

            reg = self.create_or_update_registration(event, user, course, signed_up_by)

            logger.info("Reserving slots", eventId=event.id, course=course.name, user=signed_up_by, slots=slot_ids)
            for i, slot in enumerate(slots):
                if i == 0:  # TODO: bug?
                    slot.player = player
                slot.status = "P"
                slot.registration = reg
                slot.save()
        else:
            reg = self.create_or_update_registration(event, user, course, signed_up_by)
            for s in range(0, event.maximum_signup_group_size):
                slot = event.registrations.create(event=event, registration=reg, status="P", starting_order=0, slot=s)
                if slot.slot == 0:
                    slot.player = player
                slot.save()

        return reg

    def create_or_update_registration(self, event, user, course, signed_up_by):
        registration = self.filter(user=user, event=event).first()
        if registration is not None:
            is_duplicate = registration.slots.filter(Q(status="R") | Q(status="X")).exists()
            if is_duplicate:
                raise AlreadyRegisteredError()
            registration.course = course
            registration.signed_up_by = signed_up_by
            registration.slots.filter(status="P").update(**{"status": "A", "player": None, "registration": None})
        else:
            registration = self.create(event=event, course=course, user=user, signed_up_by=signed_up_by)

        if event.can_choose:
            registration.expires = tz.now() + timedelta(minutes=5)
        else:
            registration.expires = tz.now() + timedelta(minutes=15)

        registration.save()

        return registration

    def payment_processing(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()
            reg.slots.filter(status="P").filter(player__isnull=False).update(**{"status": "X"})
            # free up or remove slots without players
            if reg.event.can_choose:
                reg.slots\
                    .filter(status="P")\
                    .filter(player__isnull=True)\
                    .update(**{"status": "A", "player": None, "registration": None})
            else:
                reg.slots\
                    .filter(status="P")\
                    .filter(player__isnull=True)\
                    .delete()
        except ObjectDoesNotExist:
            pass

    def payment_confirmed(self, registration_id):
        """
        Mark a registration's payment as confirmed by updating its pending slots to confirmed and return the registration.
        
        Parameters:
            registration_id (int): Primary key of the registration to confirm.
        
        Returns:
            Registration or None: The Registration instance whose slots with status `"X"` were updated to `"R"`, or `None` if no registration with the given id exists.
        """
        try:
            reg = self.filter(pk=registration_id).get()
            reg.slots.filter(status="X").update(**{"status": "R"})
            return reg
        except ObjectDoesNotExist:
            pass
        
    # Not currently used
    def undo_payment_processing(self, registration_id):
        try:
            reg = self.filter(pk=registration_id).get()
            logger.info("Undoing payment processing", registration=registration_id, user=reg.signed_up_by)
            reg.slots.filter(status="X").update(**{"status": "P"})
        except ObjectDoesNotExist:
            pass

    @transaction.atomic()
    def cancel_registration(self, registration_id, payment_id, reason):
        try:
            reg = self.filter(pk=registration_id).get()
            logger.info("Canceling registration", registration=registration_id, payment=payment_id,
                        user=reg.signed_up_by, reason=reason)

            if reg.event.can_choose:
                reg.slots.filter(status="P").update(**{"status": "A", "player": None, "registration": None})
                reg.slots.filter(status="X").update(**{"status": "A", "player": None, "registration": None})
            else:
                reg.slots.filter(status="P").delete() # remove pending slots
                reg.slots.filter(status="X").delete() # remove processing slots

            reg.delete()

            if payment_id is not None and payment_id > 0:
                payment = Payment.objects.get(pk=payment_id)
                payment.payment_details.all().delete()
                if payment.payment_code is not None and payment.payment_code.startswith("pi_"):
                    logger.info("Canceling stripe payment", payment=payment_id, code=payment.payment_code, user=reg.signed_up_by)
                    stripe.PaymentIntent.cancel(payment.payment_code)
                payment.delete()

        except ObjectDoesNotExist:
            pass

```

### Payment Endpoints

```python
  @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
  def stripe_amount(self, request, pk):
      try:
          payment = Payment.objects.get(pk=pk)
      except ObjectDoesNotExist:
          logger.warn("No payment found when calculating payment amount.", payment_id=pk)
          return Response("No payment found. Your registration may have timed out. Cancel your current registration and start again.", status=404)

      payment_details = list(payment.payment_details.all())

      amount_due = get_amount_due(None, payment_details)
      stripe_payment = calculate_payment_amount(amount_due)
      stripe_amount_due = int(round_half_up(stripe_payment[0] * 100))

      return Response(stripe_amount_due, status=200)

  @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
  def customer_session(self, request):
      email = request.user.email
      player = Player.objects.get(email=email)

      if player.stripe_customer_id is None:
          customer = stripe.Customer.create()
          player.stripe_customer_id = customer.id
          player.save()

      session = stripe.CustomerSession.create(
          customer=player.stripe_customer_id,
          components={
              "payment_element": {
                  "enabled": True,
                  "features": {
                      "payment_method_redisplay": "enabled",
                      "payment_method_save": "enabled",
                      "payment_method_save_usage": "on_session",
                      "payment_method_remove": "enabled",
                  }
              }
          }
      )
      return Response(session, status=200)

  @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
  def payment_intent(self, request, pk):
      try:
          event_id = request.data.get("event_id", 0)
          registration_id = request.data.get("registration_id", 0)
          user = request.user
          player = Player.objects.get(email=user.email)
          event = Event.objects.get(pk=event_id)
          payment = Payment.objects.get(pk=pk)
          payment_details = list(payment.payment_details.all())

          amount_due = get_amount_due(event, payment_details)
          stripe_payment = calculate_payment_amount(amount_due)
          stripe_amount_due = int(round_half_up(stripe_payment[0] * 100))  # total (with fees) in cents

          if amount_due > 0 and (player.stripe_customer_id is None or player.stripe_customer_id.strip() == ""):
              customer = stripe.Customer.create()
              player.stripe_customer_id = customer.id
              player.save()

          intent = stripe.PaymentIntent.create(
              amount=stripe_amount_due,
              currency="usd",
              automatic_payment_methods={"enabled": True},
              description="Online payment for {} ({}) by {}".format(
                  event.name,
                  event.start_date.strftime("%Y-%m-%d"),
                  user.get_full_name()),
              metadata={
                  "user_name": user.get_full_name(),
                  "user_email": user.email,
                  "event_id": event.id,
                  "event_name": event.name,
                  "event_date": event.start_date.strftime("%Y-%m-%d"),
                  "registration_id": registration_id,
              },
              customer=player.stripe_customer_id,
              receipt_email=user.email,
          )
          logger.info("Payment intent created", payment_id=pk, intent_id=intent.id, status=intent.status)

          payment.payment_code = intent.id
          payment.payment_key = intent.client_secret
          payment.save()

          # Updates the registration slots to processing and frees up any slots without players
          Registration.objects.payment_processing(registration_id)

          return Response(intent, status=200)

      except Exception as e:
          logger.error("Payment intent creation failed", payment_id=pk, message=str(e))
          return Response(str(e), status=400)
```

---

## Frontend (React) Registration Context

All registration context API activity will transition from calling the Django backend to 
the NestJs API.

```typescript
export function EventRegistrationProvider({ clubEvent, children }: PropsWithChildren<ClubEventProps>) {
	const queryClient = useQueryClient()
	const [state, dispatch] = useReducer(eventRegistrationReducer, defaultRegistrationState)

	const { user } = useAuth()
	const { data: player } = useMyPlayerRecord()

	useEffect(() => {
		const correlationId = getCorrelationId(clubEvent?.id)
		dispatch({
			type: "load-event",
			payload: { clubEvent: clubEvent, correlationId: correlationId },
		})
	}, [clubEvent])

	const { mutateAsync: _createPayment } = useMutation({
		mutationFn: (payment: Partial<Payment>) => {
			return httpClient(apiUrl("payments"), {
				body: JSON.stringify({
					event: state.clubEvent?.id,
					user: user.id,
					notification_type: payment.notificationType,
					payment_details: payment.details?.map((f) => {
						return {
							event_fee: f.eventFeeId,
							registration_slot: f.slotId,
							amount: f.amount,
						}
					}),
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onSuccess: (data) => {
			queryClient.setQueryData(["payment", state.clubEvent?.id], data)
			dispatch({ type: "update-payment", payload: { payment: new Payment(data) } })
		},
		onError: (error) => {
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const { mutateAsync: _updatePayment } = useMutation({
		mutationFn: (payment: Payment) => {
			return httpClient(apiUrl(`payments/${payment.id}`), {
				method: "PUT",
				body: JSON.stringify({
					event: state.clubEvent?.id,
					user: user.id,
					notification_type: payment.notificationType,
					payment_details: payment.details?.map((f) => {
						return {
							event_fee: f.eventFeeId,
							registration_slot: f.slotId,
							amount: f.amount,
						}
					}),
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onSuccess: (data) => {
			queryClient.setQueryData(["payment", state.clubEvent?.id], data)
			dispatch({ type: "update-payment", payload: { payment: new Payment(data) } })
		},
		onError: (error) => {
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const { mutateAsync: _createPaymentIntent } = useMutation({
		mutationFn: () => {
			return httpClient(apiUrl(`payments/${state.payment?.id}/payment_intent/`), {
				body: JSON.stringify({
					event_id: state.clubEvent?.id,
					registration_id: state.registration?.id,
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			}) as Promise<PaymentIntent>
		},
	})

	const { mutate: _updateRegistrationSlotPlayer } = useMutation({
		mutationFn: ({ slotId, playerId }: { slotId: number; playerId: number | null }) => {
			return httpClient(apiUrl(`registration-slots/${slotId}`), {
				method: "PATCH",
				body: JSON.stringify({
					player: playerId,
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["event-registration-slots", state.clubEvent?.id] })
		},
		onError: (error) => {
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const { mutateAsync: _cancelRegistration } = useMutation({
		mutationFn: ({ reason }: { reason: "user" | "timeout" | "navigation" | "violation" }) => {
			const regId = state.registration?.id ?? 0
			const pmtId = state.payment?.id ?? 0
			const endpoint = `registration/${regId}/cancel/?reason=${reason}&payment_id=${pmtId}`
			return httpClient(apiUrl(endpoint), {
				method: "PUT",
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onSuccess: () => {
			dispatch({ type: "cancel-registration", payload: null })
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: ["registration"] })
			queryClient.invalidateQueries({ queryKey: ["event-registrations", state.clubEvent?.id] })
			queryClient.invalidateQueries({ queryKey: ["event-registration-slots", state.clubEvent?.id] })
		},
		onError: (error) => {
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const { mutate: _updateRegistrationNotes } = useMutation({
		mutationFn: (notes: string) => {
			return httpClient(apiUrl(`registration/${state.registration?.id}`), {
				method: "PATCH",
				body: JSON.stringify({
					notes: notes,
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onError: (error) => {
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const { mutateAsync: _createRegistration } = useMutation({
		mutationFn: ({ courseId, slots }: { courseId?: number; slots?: RegistrationSlot[]; selectedStart?: string }) => {
			return httpClient(apiUrl("registration"), {
				body: JSON.stringify({
					event: state.clubEvent?.id,
					course: courseId,
					slots: slots?.map((s) => s.obj),
				}),
				headers: { "X-Correlation-ID": state.correlationId },
			})
		},
		onSuccess: (data, args) => {
			const registrationData = RegistrationApiSchema.parse(data)
			dispatch({
				type: "create-registration",
				payload: {
					registration: new Registration(registrationData, args.selectedStart),
					payment: _createInitialPaymentRecord(registrationData),
				},
			})
			queryClient.setQueryData(["registration", state.clubEvent?.id], registrationData)
		},
		onError: (error) => {
			// conflict - the slots have been taken
			if (error.message.startsWith("One or more of the slots")) {
				queryClient.invalidateQueries({
					queryKey: ["event-registration-slots", state.clubEvent?.id],
				})
			}
			dispatch({ type: "update-error", payload: { error } })
		},
	})

	const _createInitialPaymentRecord = (registration: RegistrationData) => {
		if (!state.clubEvent || !user.id) {
			throw new Error("Cannot create an initial payment record without a club event or user.")
		}
		if (!registration.slots?.length) {
			throw new Error("Cannot create an initial payment record without registration slots.")
		}
		const payment = Payment.createPlaceholder(state.clubEvent.id, user.id)
		state.clubEvent.fees
			.filter((f) => f.isRequired)
			.forEach((fee) => {
				payment.details.push(
					new PaymentDetail({
						id: 0,
						payment: 0,
						event_fee: fee.id,
						registration_slot: registration.slots[0].id,
						amount: fee.amountDue(player),
					}),
				)
			})
		return payment
	}

	/**
	 * Updates query state so the UI reflects the completed registration.
	 */
	const _invalidateQueries = useCallback(() => {
		if (state.clubEvent?.eventType === EventType.Membership) {
			queryClient.setQueryData(["player", user.email], {
				...player?.data,
				is_member: true,
				last_season: currentSeason - 1,
			})
		} else {
			queryClient.invalidateQueries({ queryKey: ["player", user.email] })
		}
		queryClient.invalidateQueries({ queryKey: ["my-cards"] })
		queryClient.invalidateQueries({ queryKey: ["my-events"] })
		queryClient.invalidateQueries({ queryKey: ["event-registrations", state.clubEvent?.id] })
		queryClient.invalidateQueries({ queryKey: ["event-registration-slots", state.clubEvent?.id] })
	}, [player?.data, queryClient, state.clubEvent?.eventType, state.clubEvent?.id, user.email])

	/**
	 * Changes the current step in the registration process.
	 */
	const updateStep = useCallback((step: IRegistrationStep) => {
		dispatch({ type: "update-step", payload: { step } })
	}, [])

	/**
	 * Loads an existing registration for a given player, if it exists.
	 */
	const loadRegistration = useCallback(
		async (player: Player) => {
			try {
				const registrationData = await getOne(
					`registration/?event_id=${state.clubEvent?.id}&player_id=${player.id}`,
					RegistrationApiSchema,
				)
				if (registrationData) {
					const registration = new Registration(registrationData)
					const feeData = await getMany(
						`registration-fees/?registration_id=${registration.id}&confirmed=true`,
						RegistrationFeeApiSchema,
					)
					const fees = feeData?.map((f) => new RegistrationFee(f))
					dispatch({
						type: "load-registration",
						payload: {
							registration,
							payment: Payment.createPlaceholder(state.clubEvent?.id ?? 0, user.id ?? 0),
							existingFees: fees,
						},
					})
					queryClient.setQueryData(["registration", state.clubEvent?.id], registrationData)
				}
			} catch (error) {
				dispatch({ type: "update-error", payload: { error: error as Error } })
			}
		},
		[state.clubEvent?.id, queryClient, user.id],
	)

	/**
	 * Adds one or more players to an existing registration.
	 */
	const editRegistration = useCallback(
		async (registrationId: number, playerIds: number[]) => {
			try {
				const registrationData = await httpClient(apiUrl(`registration/${registrationId}/add_players`), {
					method: "PUT",
					body: JSON.stringify({
						players: playerIds.map((id) => ({ id })),
					}),
				})
				if (registrationData) {
					const registration = new Registration(registrationData.registration)
					const payment = await getOne(`payments/${registrationData.payment_id}/`, PaymentApiSchema)
					if (!payment) {
						throw new Error("Failed to load payment data after editing registration.")
					}
					const feeData = await getMany(
						`registration-fees/?registration_id=${registration.id}`,
						RegistrationFeeApiSchema,
					)
					if (!feeData) {
						throw new Error("Failed to load registration fee data after editing registration.")
					}
					const fees = feeData.map((f) => new RegistrationFee(f))
					dispatch({
						type: "load-registration",
						payload: {
							registration,
							payment: new Payment(payment),
							existingFees: fees,
						},
					})
					queryClient.setQueryData(["registration", state.clubEvent?.id], registrationData)
					queryClient.invalidateQueries({ queryKey: ["event-registrations", state.clubEvent?.id] })
					queryClient.invalidateQueries({ queryKey: ["event-registration-slots", state.clubEvent?.id] })
				}
			} catch (error) {
				dispatch({ type: "update-error", payload: { error: error as Error } })
			}
		},
		[queryClient, state.clubEvent?.id],
	)

	/**
	 * Creates a new registration record for the current user.
	 */
	const createRegistration = useCallback(
		(course?: Course, slots?: RegistrationSlot[], selectedStart?: string) => {
			return _createRegistration({ courseId: course?.id, slots, selectedStart })
		},
		[_createRegistration],
	)

	/**
	 * Updates the current registration record with notes.
	 */
	const updateRegistrationNotes = useCallback(
		(notes: string) => {
			dispatch({ type: "update-registration-notes", payload: { notes } })
			_updateRegistrationNotes(notes)
		},
		[_updateRegistrationNotes],
	)

	/**
	 * Cancels the current registration and resets the registration process flow.
	 */
	const cancelRegistration = useCallback(
		(reason: "user" | "timeout" | "navigation" | "violation", mode: RegistrationMode) => {
			if (mode === "new") {
				return _cancelRegistration({ reason })
			} else {
				queryClient.invalidateQueries({ queryKey: ["registration"] })
				return Promise.resolve()
			}
		},
		[_cancelRegistration, queryClient],
	)

	/**
	 * Completes the registration process, clearing registration state and
	 * setting the mode to "idle", which enables the guard on the register routes.
	 */
	const completeRegistration = useCallback(() => {
		_invalidateQueries()
		dispatch({ type: "complete-registration", payload: null })
	}, [_invalidateQueries])

	/**
	 * Create and return a stripe customer session, which allows the user to
	 * save their payment information for future use.
	 */
	const initiateStripeSession = useCallback(() => {
		httpClient(apiUrl("payments/customer_session/"), {
			method: "POST",
			body: JSON.stringify({}),
			headers: { "X-Correlation-ID": state.correlationId },
		})
			.then((data) => {
				dispatch({
					type: "initiate-stripe-session",
					payload: { clientSessionKey: data.client_secret },
				})
			})
			.catch((error) => {
				dispatch({ type: "update-error", payload: { error } })
			})
	}, [state.correlationId])

	/**
	 * Create a payment intent for client-side processing.
	 */
	const createPaymentIntent = useCallback(() => {
		return _createPaymentIntent()
	}, [_createPaymentIntent])

	/**
	 * Saves the current payment record.
	 */
	const savePayment = useCallback(() => {
		if (state.payment?.id) {
			return _updatePayment(state.payment)
		} else {
			const payment = { ...state.payment }
			return _createPayment(payment)
		}
	}, [_createPayment, _updatePayment, state.payment])

	/**
	 * Add a player to a given registration slot.
	 */
	const addPlayer = useCallback(
		(slot: RegistrationSlot, player: Player) => {
			_updateRegistrationSlotPlayer(
				{ slotId: slot.id, playerId: player.id },
				{
					onSuccess: () => dispatch({ type: "add-player", payload: { slot, player } }),
				},
			)
		},
		[_updateRegistrationSlotPlayer],
	)

	/**
	 * Removes the player on a given registration slot.
	 */
	const removePlayer = useCallback(
		(slot: RegistrationSlot) => {
			_updateRegistrationSlotPlayer(
				{ slotId: slot.id, playerId: null },
				{
					onSuccess: () => dispatch({ type: "remove-player", payload: { slotId: slot.id } }),
				},
			)
		},
		[_updateRegistrationSlotPlayer],
	)

	/**
	 * Adds an event fee to a given registration slot.
	 */
	const addFee = useCallback((slot: RegistrationSlot, eventFee: EventFee, player: Player) => {
		dispatch({ type: "add-fee", payload: { slotId: slot.id, eventFee, player } })
	}, [])

	/**
	 * Removes an event fee from a given registration slot.
	 */
	const removeFee = useCallback((slot: RegistrationSlot, eventFee: EventFee) => {
		dispatch({ type: "remove-fee", payload: { eventFeeId: eventFee.id, slotId: slot.id } })
	}, [])

	const canRegister = useCallback(() => {
		const slots = state.registration?.slots ?? []
		if (state.clubEvent?.priorityRegistrationIsOpen()) {
			// During priority registration, the minimum signup group size is enforced.
			return slots.filter((s) => s.playerId).length >= (state.clubEvent?.minimumSignupGroupSize ?? 1)
		} else if (state.clubEvent?.registrationIsOpen()) {
			return slots.filter((s) => s.playerId).length >= 1
		}
		return false
	}, [state.clubEvent, state.registration])

	const setError = useCallback((error: Error | null) => {
		dispatch({ type: "update-error", payload: { error } })
	}, [])

	const value = {
		...state,
		addFee,
		addPlayer,
		cancelRegistration,
		canRegister,
		completeRegistration,
		createPaymentIntent,
		createRegistration,
		editRegistration,
		initiateStripeSession,
		loadRegistration,
		removeFee,
		removePlayer,
		savePayment,
		setError,
		updateRegistrationNotes,
		updateStep,
	}

	return <EventRegistrationContext.Provider value={value}>{children}</EventRegistrationContext.Provider>
}
```

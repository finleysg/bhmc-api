-- Candidates for payment record cleanup job
select p.*, f.*, s.id as slot_id, s.status
from register_registrationfee as f
left join register_registrationslot as s on f.registration_slot_id = s.id
left join payments_payment as p on f.payment_id = p.id
left join register_registration as r on s.registration_id = r.id
where (p.payment_code = '' or p.payment_code is null)
and r.id is null
and s.status = 'A'

-- Potentially expired registrations
select *
from register_registration r
left join register_registrationslot s on r.id = s.registration_id
where r.event_id = 610
and s.status <> 'R'
and r.expires > r.created_date -- plus 5 or 15 min

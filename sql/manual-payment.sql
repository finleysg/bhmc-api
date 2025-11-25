-- 38396 = registration id
-- 617 = event id
-- 1103 = user id

select *
from register_registrationslot
where registration_id = 38396

select *
from register_player
where id in (1187,
1197,
1179,
1072,
1384)

insert payments_payment (payment_code, confirmed, event_id, user_id, payment_amount, transaction_fee)
values ('paid by venmo', 1, 617, 1103, 67.00, 0.00)
-- 23897

select * 
from payments_payment
order by id desc

select *
from events_eventfee as f
join events_feetype as t on f.fee_type_id = t.id
where event_id = 617

insert into register_registrationfee (is_paid, event_fee_id, payment_id, registration_slot_id, amount)
values (1, 617, 23897, 115915, 5.00),
(1, 617, 23897, 115916, 5.00),
(1, 617, 23897, 115917, 5.00),
(1, 617, 23897, 115918, 5.00),
(1, 617, 23897, 115919, 5.00)


insert into register_registrationfee (is_paid, event_fee_id, payment_id, registration_slot_id, amount)
values (1, 784, 23897, 115915, 5.00),
    (1, 785, 23897, 115915, 23.00),
    (1, 786, 23897, 115915, 14.00)

update payments_payment
set payment_date = '2025-04-21 18:00:00.000000',
    confirm_date = '2025-04-21 18:00:00.000000'
where id = 23897

select r.signed_up_by, f.amount, ft.name
from register_registration r
left join register_registrationslot s on r.id = s.registration_id
left join register_registrationfee f on s.id = f.registration_slot_id
left join events_eventfee ef on f.event_fee_id = ef.id
left join events_feetype ft on ef.fee_type_id = ft.id
where r.id in (38065, 38140, 38089)

select last_name, ghin, cast(convert(ghin, signed) as char)
from register_player
where ghin like '0%'

update register_player
set ghin = cast(convert(ghin, signed) as char)
where ghin like '0%' and ghin != '0'

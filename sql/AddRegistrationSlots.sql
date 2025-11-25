SELECT *
FROM `mpgagolf$bhmc`.register_registrationslot rr 
WHERE event_id = 547
ORDER BY hole_id, starting_order 

INSERT INTO `mpgagolf$bhmc`.register_registrationslot (starting_order, slot, status, event_id, hole_id)
VALUES (21, 0, 'A', 547, 1), (21, 1, 'A', 547, 1), (21, 2, 'A', 547, 1), (21, 3, 'A', 547, 1), (21, 4, 'A', 547, 1)

INSERT INTO `mpgagolf$bhmc`.register_registrationslot (starting_order, slot, status, event_id, hole_id)
VALUES (21, 0, 'A', 547, 10), (21, 1, 'A', 547, 10), (21, 2, 'A', 547, 10), (21, 3, 'A', 547, 10), (21, 4, 'A', 547, 10)

INSERT INTO `mpgagolf$bhmc`.register_registrationslot (starting_order, slot, status, event_id, hole_id)
VALUES (21, 0, 'A', 547, 19), (21, 1, 'A', 547, 19), (21, 2, 'A', 547, 19), (21, 3, 'A', 547, 19), (21, 4, 'A', 547, 19)

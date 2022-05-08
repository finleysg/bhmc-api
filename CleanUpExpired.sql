-- Pending registrations that have expired
SELECT r.*, s.*, p.*
FROM `mpgagolf$bhmc`.register_registration r
JOIN `mpgagolf$bhmc`.register_registrationslot s ON r.id = s.registration_id 
JOIN `mpgagolf$bhmc`.events_event e ON r.event_id = e.id
LEFT JOIN `mpgagolf$bhmc`.payments_payment p ON e.id = p.event_id AND r.user_id = p.user_id 
WHERE r.expires < CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'America/Chicago') 
AND e.can_choose = 1
AND s.status = 'P'
AND IFNULL(p.confirmed, 0) = 0

-- Clear pending registrations
CREATE TEMPORARY TABLE `mpgagolf$bhmc`.expired_registrations
SELECT s.registration_id, s.id AS registration_slot_id 
FROM `mpgagolf$bhmc`.register_registration r
JOIN `mpgagolf$bhmc`.register_registrationslot s ON r.id = s.registration_id 
JOIN `mpgagolf$bhmc`.events_event e ON r.event_id = e.id
LEFT JOIN `mpgagolf$bhmc`.payments_payment p ON e.id = p.event_id AND r.user_id = p.user_id 
WHERE r.expires < CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'America/Chicago') 
AND e.can_choose = 1
AND s.status = 'P'
AND IFNULL(p.confirmed, 0) = 0;

SELECT registration_id FROM `mpgagolf$bhmc`.expired_registrations;

DROP TEMPORARY TABLE `mpgagolf$bhmc`.expired_registrations;


UPDATE `mpgagolf$bhmc`.register_registrationslot 
SET registration_id = NULL 
   ,player_id = NULL 
   ,status = 'A'
WHERE id IN (
	SELECT xp.id FROM (
		SELECT s.id
		FROM `mpgagolf$bhmc`.register_registration r
		JOIN `mpgagolf$bhmc`.register_registrationslot s ON r.id = s.registration_id 
		JOIN `mpgagolf$bhmc`.events_event e ON r.event_id = e.id
		LEFT JOIN `mpgagolf$bhmc`.payments_payment p ON e.id = p.event_id AND r.user_id = p.user_id 
		WHERE r.expires < CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'America/Chicago') 
		AND e.can_choose = 0
		AND s.status = 'P'
		AND IFNULL(p.confirmed, 0) = 0
	) AS xp
)

DELETE `mpgagolf$bhmc`.register_registration
WHERE id IN (
	SELECT xp.id FROM (
		SELECT r.id
		FROM `mpgagolf$bhmc`.register_registration r
		JOIN `mpgagolf$bhmc`.events_event e ON r.event_id = e.id
		LEFT JOIN `mpgagolf$bhmc`.payments_payment p ON e.id = p.event_id AND r.user_id = p.user_id 
		WHERE r.expires < CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'America/Chicago') 
		AND e.can_choose = 0
		AND s.status = 'P'
		AND IFNULL(p.confirmed, 0) = 0
	) AS xp
)


UPDATE `mpgagolf$bhmc`.register_registrationslot 
SET registration_id = NULL, player_id = NULL, status = 'A'
WHERE id IN (
	62119,
	62120,
	62121
)
AND event_id = 426



SELECT NOW() as now_result, LOCALTIME() as local_now_result

SELECT CONVERT_TZ(UTC_TIMESTAMP(), 'UTC', 'America/Chicago')

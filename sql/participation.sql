SELECT e.season, e.start_date, c.`name` as 'course', s.starting_order, COUNT(s.slot) as 'players'
FROM register_registrationslot s
JOIN events_event e on s.event_id = e.id
JOIN courses_hole h on s.hole_id = h.id
JOIN courses_course c on h.course_id = c.id
WHERE e.season > 2022
AND e.can_choose = 1
AND e.status = 'S'
AND e.start_type = 'TT'
AND s.status = 'R'
GROUP BY e.season, e.start_date, s.starting_order, c.`name`
ORDER BY e.season, e.start_date, s.starting_order, c.`name`

SELECT e.season, c.`name` as 'course', s.starting_order, COUNT(s.slot) as 'players'
FROM register_registrationslot s
JOIN events_event e on s.event_id = e.id
JOIN courses_hole h on s.hole_id = h.id
JOIN courses_course c on h.course_id = c.id
WHERE e.season > 2022
AND e.can_choose = 1
AND e.status = 'S'
AND e.start_type = 'TT'
AND s.status = 'R'
GROUP BY e.season, s.starting_order, c.`name`
ORDER BY e.season, s.starting_order, c.`name`


SELECT e.season, e.start_date, COUNT(s.slot) as 'players'
FROM register_registrationslot s
LEFT JOIN events_event e on s.event_id = e.id
WHERE e.can_choose = 1
AND e.status = 'S'
AND s.status = 'R'
GROUP BY e.season, e.start_date
ORDER BY e.start_date

SELECT e.season, e.name, e.start_date, COUNT(s.slot) as 'players'
FROM register_registrationslot s
JOIN events_event e on s.event_id = e.id
WHERE e.can_choose = 0
AND e.status = 'S'
AND e.event_type = 'W'
AND s.status = 'R'
GROUP BY e.season, e.name, e.start_date
ORDER BY e.start_date

SELECT e.season, COUNT(s.slot) as 'players'
FROM register_registrationslot s
JOIN events_event e on s.event_id = e.id
WHERE e.event_type = 'R'
AND s.status = 'R'
GROUP BY e.season
ORDER BY e.season

SELECT season, is_new, COUNT(*) as members
FROM (
SELECT c.season, case when p.season is null then 1 else 0 end as is_new, c.ghin
FROM (
    SELECT e.season, p.ghin
    FROM register_registrationslot s
    JOIN events_event e on s.event_id = e.id
    JOIN register_player p on s.player_id = p.id
    WHERE e.event_type = 'R'
    AND s.status = 'R'
) as c
LEFT JOIN (
    SELECT e.season, p.ghin
    FROM register_registrationslot s
    JOIN events_event e on s.event_id = e.id
    JOIN register_player p on s.player_id = p.id
    WHERE e.event_type = 'R'
    AND s.status = 'R'
) as p ON c.season = p.season+1 AND c.ghin = p.ghin
) as sub
GROUP BY season, is_new

SELECT e.season, p.tee, COUNT(*)
FROM register_registrationslot s
JOIN events_event e on s.event_id = e.id
JOIN register_player p on s.player_id = p.id
WHERE e.event_type = 'R'
AND s.status = 'R'
GROUP BY e.season, p.tee
ORDER BY e.season

/* PRIORITY REGISTRATION STATS */
CREATE TEMPORARY TABLE starting_order (num INT NOT NULL, PRIMARY KEY (num));
INSERT INTO starting_order (num) VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9), (10), (11), (12), (13), (14), (15), (16), (17), (18), (19), (20), (21), (22), (23), (24), (25);

SELECT t1.start_date, t1.course, t1.num, t2.reg_time, IFNULL(t2.players, 0) AS players
FROM (
    SELECT e.id, e.start_date, c.`name` AS course, o.num
    FROM events_event e
    JOIN events_event_courses ec ON e.id = ec.event_id
    JOIN courses_course c ON ec.course_id = c.id
    JOIN courses_hole h ON c.id = h.course_id AND h.hole_number = 1
    CROSS JOIN starting_order o
    WHERE e.season = 2024
    AND e.can_choose = 1
    AND e.status = 'S'
    AND e.start_type = 'TT'
    -- ORDER BY e.start_date, o.num, c.`name`;
) AS t1
LEFT JOIN (
    SELECT e.id, TIME(r.created_date) AS reg_time, e.start_date, c.`name` AS course, s.starting_order, COUNT(*) as players 
    FROM register_registration AS r
    JOIN events_event e ON r.event_id = e.id
    JOIN register_registrationslot s ON r.id = s.registration_id
    JOIN courses_hole h on s.hole_id = h.id
    JOIN courses_course c on h.course_id = c.id
    WHERE e.season = 2024
    AND e.can_choose = 1
    AND e.status = 'S'
    AND e.start_type = 'TT'
    AND DAYOFWEEK(r.created_date) = 2 -- Monday
    AND HOUR(r.created_date) = 17 -- 5 PM
    AND MINUTE(r.created_date) <= 15 -- First 15 minutes
    GROUP BY e.id, r.id, e.start_date, c.`name`, s.starting_order
    --ORDER BY e.id, s.starting_order, c.`name`
) AS t2 ON t1.id = t2.id AND t1.course = t2.course AND t1.num = t2.starting_order
ORDER BY t1.id, t1.num, t1.course;

DROP TEMPORARY TABLE starting_order;


SELECT season, is_new, created_date
FROM (
    SELECT c.season, case when p.season is null then 1 else 0 end as is_new, c.ghin, c.created_date
    FROM (
        SELECT e.season, p.ghin, r.created_date
        FROM register_registrationslot s
        JOIN events_event e on s.event_id = e.id
        JOIN register_player p on s.player_id = p.id
        JOIN register_registration r on s.registration_id = r.id
        WHERE e.event_type = 'R'
        AND s.status = 'R'
    ) as c
    LEFT JOIN (
        SELECT e.season, p.ghin
        FROM register_registrationslot s
        JOIN events_event e on s.event_id = e.id
        JOIN register_player p on s.player_id = p.id
        JOIN register_registration r on s.registration_id = r.id
        WHERE e.event_type = 'R'
        AND s.status = 'R'
    ) as p ON c.season = p.season+1 AND c.ghin = p.ghin
    WHERE c.season = 2024
) as sub
WHERE is_new = 1
ORDER BY created_date

SELECT *
FROM `bhmc-2023`.auth_user au 

UPDATE `bhmc-2023`.auth_user 
SET password = 'pbkdf2_sha256$216000$ehPFYtEsHtRM$DuP0OtP/0eW/hcDWEga/SYgdUidrHnYnGVBTVeVDldI='
WHERE id > 1

UPDATE `bhmc-2023`.register_player 
SET profile_picture_id = NULL
   ,stripe_customer_id = NULL
WHERE profile_picture_id  IS NOT NULL 
OR stripe_customer_id  IS NOT NULL 


CREATE PROCEDURE `bhmc-2023`.`GetFriends`(IN playerId INT, IN eventId INT, IN seasonEventId INT, IN previousSeasonEventId INT)
BEGIN
	SELECT
		 p.id 
		,p.first_name 
		,p.last_name 
		,p.email 
		,p.ghin 
		,p.tee 
		,p.birth_date 
		,p.phone_number 
		,r1.status AS event_status
		,r2.status AS member_status
		,r3.status AS returning_member_status
	FROM `bhmc-2023`.register_player p
	JOIN `bhmc-2023`.register_player_favorites f ON p.id = f.to_player_id 
	LEFT JOIN `bhmc-2023`.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId 
	LEFT JOIN `bhmc-2023`.register_registrationslot r2 ON p.id = r2.player_id AND r2.event_id = seasonEventId 
	LEFT JOIN `bhmc-2023`.register_registrationslot r3 ON p.id = r3.player_id AND r3.event_id = previousSeasonEventId
	WHERE f.from_player_id = playerId;
END

CREATE PROCEDURE `bhmc-2023`.`GetPlayerScores`(IN season INT)
BEGIN
	SELECT 
		 player_id
		,p.first_name
		,p.last_name
		,c.name
		,h.hole_number
		,s.is_net
		,MIN(score) as low_score
		,AVG(score) as average_score
		,MAX(score) as high_score
		,COUNT(*) as scores
	FROM scores_eventscore s
	JOIN events_event e ON s.event_id = e.id 
	JOIN courses_hole h ON s.hole_id = h.id
	JOIN courses_course c ON h.course_id = c.id
	JOIN register_player p ON s.player_id = p.id
	WHERE e.season = season
	GROUP BY player_id, p.first_name, p.last_name, c.name, h.hole_number, s.is_net 
	ORDER BY player_id, c.name, h.hole_number;
END

CREATE PROCEDURE `bhmc-2023`.`GetRegistrationFeesByEvent`(IN eventId INT)
BEGIN
	SELECT 
		 rs.player_id 
		,rf.event_fee_id 
		,rf.is_paid 
	FROM register_registrationfee rf 
	JOIN register_registrationslot rs ON rf.registration_slot_id = rs.id
	WHERE rs.event_id = eventId
	AND rs.status = 'R';
END

CREATE PROCEDURE `bhmc-2023`.`GetRegistrationsByEvent`(IN eventId INT)
BEGIN
	SELECT 
		 rs.registration_id 
		,cc.name AS course_name
		,h.hole_number
		,rs.starting_order 
		,rp.id AS player_id
		,rp.ghin 
		,rp.tee 
		,rp.last_name 
		,rp.first_name 
		,rp.birth_date 
		,rp.email 
		,rr.signed_up_by 
		,rr.created_date AS signup_date
	FROM events_event ee 
	JOIN register_registration rr ON ee.id = rr.event_id 
	JOIN register_registrationslot rs ON rr.id = rs.registration_id 
	JOIN register_player rp ON rs.player_id = rp.id 
	LEFT JOIN courses_hole h ON rs.hole_id = h.id
	LEFT JOIN courses_course cc ON h.course_id = cc.id
	WHERE ee.id = eventId
	AND rs.status = 'R'
	ORDER BY rs.id;
END

CREATE PROCEDURE `bhmc-2023`.`GetRegistrationSlots`(IN eventId INT, IN playerId INT)
BEGIN
	SELECT register_registrationslot.id,
	       register_registrationslot.event_id,
	       register_registrationslot.hole_id,
	       register_registrationslot.registration_id,
	       register_registrationslot.player_id,
	       register_registrationslot.starting_order,
	       register_registrationslot.slot,
	       register_registrationslot.status,
	       register_player.id,
	       register_player.first_name,
	       register_player.last_name,
	       register_player.email,
	       register_player.phone_number,
	       register_player.ghin,
	       register_player.tee,
	       register_player.birth_date,
	       register_player.save_last_card,
	       register_player.stripe_customer_id,
	       register_player.profile_picture_id
	  FROM register_registrationslot
	  INNER JOIN events_event
	    ON (register_registrationslot.event_id = events_event.id)
	  LEFT OUTER JOIN register_player
	    ON (register_registrationslot.player_id = register_player.id)
	 WHERE (events_event.id = eventId OR eventId = 0)
	 AND (register_player.id = playerId OR playerId = 0)
	 ORDER BY register_registrationslot.hole_id ASC, register_registrationslot.slot ASC;
END

CREATE PROCEDURE `bhmc-2023`.`GetSkinsByEvent`(IN eventId INT)
BEGIN
	SELECT 
		 rs.registration_id 
		,cc.name AS course_name
		,h.hole_number 
		,rs.starting_order 
		,rs.player_id 
		,rp.first_name 
		,rp.last_name 
		,ft.name AS skins_type
		,rf.is_paid 
		,pp.payment_date 
	FROM register_registrationfee rf 
	JOIN register_registrationslot rs ON rf.registration_slot_id = rs.id
	JOIN register_registration r ON rs.registration_id = r.id
	JOIN register_player rp ON rs.player_id = rp.id
	JOIN payments_payment pp ON rf.payment_id = pp.id
	JOIN events_eventfee ef ON rf.event_fee_id = ef.id 
	JOIN events_feetype ft ON ef.fee_type_id = ft.id
	LEFT JOIN courses_hole h ON rs.hole_id = h.id
	LEFT JOIN courses_course cc ON h.course_id = cc.id
	WHERE rs.event_id = eventId
	AND ft.name LIKE '%skin%'
	AND rs.status = 'R'
	AND pp.confirmed = 1
	ORDER BY cc.name, ft.name, h.hole_number, rs.starting_order;
END

CREATE PROCEDURE `bhmc-2023`.`MembershipReport`(IN currentEventId INT, IN previousEventId INT)
BEGIN
	SELECT 
		 rs.registration_id 
		,rp.id AS player_id
		,rp.ghin 
		,rp.tee 
		,rp.last_name 
		,rp.first_name 
		,rp.birth_date 
		,rp.email 
		,rr.signed_up_by 
		,rr.created_date AS signup_date
		,last_year.registration_id AS previous_registration_id
		,IFNULL(past_years.previous_registrations, 0) AS previous_registrations  
	FROM register_registration rr  
	JOIN register_registrationslot rs ON rr.id = rs.registration_id 
	JOIN register_player rp ON rs.player_id = rp.id 
	LEFT JOIN (
		SELECT rsub.id AS registration_id, psub.id AS player_id 
		FROM register_registration rsub 
		JOIN register_registrationslot ssub ON rsub.id = ssub.registration_id 
		JOIN register_player psub ON ssub.player_id = psub.id 
		WHERE rsub.event_id = previousEventId 
		AND ssub.status = 'R'
	) AS last_year ON last_year.player_id = rp.id
	LEFT JOIN (
		SELECT psub.id as player_id, COUNT(*) AS previous_registrations 
		FROM register_registration rsub 
		JOIN register_registrationslot ssub ON rsub.id = ssub.registration_id 
		JOIN register_player psub ON ssub.player_id = psub.id 
		JOIN core_seasonsettings ss ON rsub.event_id = ss.member_event_id
		WHERE ss.is_active = 0
		AND ss.member_event_id <> currentEventId
		AND ssub.status = 'R'
		GROUP BY psub.id
	) AS past_years ON past_years.player_id = rp.id
	WHERE rr.event_id = currentEventId
	AND rs.status = 'R'
	ORDER BY rs.id;
END

CREATE PROCEDURE `bhmc-2023`.`SearchPlayers`(IN pattern VARCHAR(20), IN playerId INT, IN eventId INT, IN seasonEventId INT, IN previousSeasonEventId INT)
BEGIN
	SELECT
		 p.id 
		,p.first_name 
		,p.last_name 
		,p.email 
		,p.ghin 
		,p.tee 
		,p.birth_date 
		,p.phone_number 
		,r1.status AS event_status
		,r2.status AS member_status
		,r3.status AS returning_member_status
	FROM `bhmc-2023`.register_player p
	LEFT JOIN `bhmc-2023`.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId 
	LEFT JOIN `bhmc-2023`.register_registrationslot r2 ON p.id = r2.player_id AND r2.event_id = seasonEventId 
	LEFT JOIN `bhmc-2023`.register_registrationslot r3 ON p.id = r3.player_id AND r3.event_id = previousSeasonEventId 
	WHERE (p.id = playerId OR playerId = 0) 
	AND (LOWER(email) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(first_name) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(last_name) LIKE CONCAT('%', LOWER(pattern), '%'));
END

CREATE PROCEDURE `bhmc-2023`.`TopGrossPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.gross_points) AS total_points 
	FROM `bhmc-2023`.damcup_seasonlongpoints slp 
	JOIN `bhmc-2023`.register_player p ON slp.player_id = p.id 
	JOIN `bhmc-2023`.events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.gross_points) DESC
	LIMIT topN;
END

CREATE PROCEDURE `bhmc-2023`.`TopNetPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.net_points) AS total_points 
	FROM `bhmc-2023`.damcup_seasonlongpoints slp 
	JOIN `bhmc-2023`.register_player p ON slp.player_id = p.id 
	JOIN `bhmc-2023`.events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.net_points) DESC
	LIMIT topN;
END


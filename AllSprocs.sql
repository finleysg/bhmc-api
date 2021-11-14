CREATE PROCEDURE `bhmc-2021`.`GetFriends`(IN playerId INT, IN eventId INT, IN seasonEventId INT, IN previousSeasonEventId INT)
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
	FROM `bhmc-2021`.register_player p
	JOIN `bhmc-2021`.register_player_favorites f ON p.id = f.to_player_id 
	LEFT JOIN `bhmc-2021`.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId 
	LEFT JOIN `bhmc-2021`.register_registrationslot r2 ON p.id = r2.player_id AND r2.event_id = seasonEventId 
	LEFT JOIN `bhmc-2021`.register_registrationslot r3 ON p.id = r3.player_id AND r3.event_id = previousSeasonEventId
	WHERE f.from_player_id = playerId;
END

CREATE PROCEDURE `bhmc-2021`.`GetRegistrationFeesByEvent`(IN eventId INT)
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

CREATE PROCEDURE `bhmc-2021`.`GetRegistrationsByEvent`(IN eventId INT)
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

CREATE PROCEDURE `bhmc-2021`.`GetRegistrationSlots`(IN eventId INT, IN playerId INT)
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

CREATE PROCEDURE `bhmc-2021`.`SearchPlayers`(IN pattern VARCHAR(20), IN playerId INT, IN eventId INT, IN seasonEventId INT, IN previousSeasonEventId INT)
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
	FROM `bhmc-2021`.register_player p
	LEFT JOIN `bhmc-2021`.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId 
	LEFT JOIN `bhmc-2021`.register_registrationslot r2 ON p.id = r2.player_id AND r2.event_id = seasonEventId 
	LEFT JOIN `bhmc-2021`.register_registrationslot r3 ON p.id = r3.player_id AND r3.event_id = previousSeasonEventId 
	WHERE (p.id = playerId OR playerId = 0) 
	AND (LOWER(email) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(first_name) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(last_name) LIKE CONCAT('%', LOWER(pattern), '%'));
END

CREATE PROCEDURE `bhmc-2021`.`TopGrossPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.gross_points) AS total_points 
	FROM `bhmc-2021`.damcup_seasonlongpoints slp 
	JOIN `bhmc-2021`.register_player p ON slp.player_id = p.id 
	JOIN `bhmc-2021`.events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.gross_points) DESC
	LIMIT topN;
END

CREATE PROCEDURE `bhmc-2021`.`TopNetPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.net_points) AS total_points 
	FROM `bhmc-2021`.damcup_seasonlongpoints slp 
	JOIN `bhmc-2021`.register_player p ON slp.player_id = p.id 
	JOIN `bhmc-2021`.events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.net_points) DESC
	LIMIT topN;
END

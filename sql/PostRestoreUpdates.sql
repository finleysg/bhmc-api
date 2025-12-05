SELECT *
FROM auth_user au 

SELECT *
FROM register_player
WHERE is_member = 1

UPDATE auth_user 
SET password = 'pbkdf2_sha256$216000$ehPFYtEsHtRM$DuP0OtP/0eW/hcDWEga/SYgdUidrHnYnGVBTVeVDldI='
WHERE id > 1

UPDATE register_player 
SET profile_picture_id = NULL
   ,stripe_customer_id = NULL
WHERE profile_picture_id  IS NOT NULL 
OR stripe_customer_id  IS NOT NULL 


CREATE PROCEDURE `bhmc`.`GetFriends`(IN playerId INT)
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
		,p.is_member 
		,p.last_season 
	FROM `bhmc`.register_player p
	JOIN `bhmc`.register_player_favorites f ON p.id = f.to_player_id 
	WHERE f.from_player_id = playerId;
END

CREATE PROCEDURE `bhmc`.`GetPlayerScores`(IN season INT)
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

CREATE PROCEDURE `bhmc`.`GetRegistrationFeesByEvent`(IN eventId INT)
BEGIN
	SELECT 
		 rs.player_id 
		,rf.event_fee_id 
		,ft.name AS fee_name
		,ef.amount 
		,ef.override_amount 
		,ef.override_restriction 
		,rf.payment_id 
		,rf.amount AS amount_paid
		,rf.is_paid 
	FROM register_registrationfee rf 
	JOIN register_registrationslot rs ON rf.registration_slot_id = rs.id
	JOIN events_eventfee ef ON rf.event_fee_id = ef.id
	JOIN events_feetype ft ON ef.fee_type_id = ft.id
	WHERE rs.event_id = eventId
	AND rs.status = 'R';
END

CREATE PROCEDURE `bhmc`.`GetRegistrationsByEvent`(IN eventId INT)
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

CREATE PROCEDURE `bhmc`.`GetRegistrationSlots`(IN eventId INT, IN playerId INT)
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

CREATE PROCEDURE `bhmc`.`GetSkinsByEvent`(IN eventId INT)
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

CREATE PROCEDURE `bhmc`.`MembershipReport`(IN season INT)
BEGIN
	SELECT 
		 rr.id AS registration_id 
		,rp.id AS player_id
		,rp.ghin 
		,rp.tee 
		,rp.last_name 
		,rp.first_name 
		,rp.birth_date 
		,rp.email 
		,rp.last_season 
		,rr.signed_up_by 
		,rr.created_date AS signup_date
		,e.id AS registration_event_id
		,e.name AS registration_event_name
	FROM register_player rp
	JOIN register_registrationslot rs ON rp.id = rs.player_id 
	JOIN register_registration rr ON rs.registration_id = rr.id
	JOIN events_event e ON rr.event_id = e.id 
	WHERE e.season = season
	AND e.event_type = 'R'
	AND rp.is_member = 1
	AND rs.status = 'R'
	ORDER BY rs.id;
END

CREATE PROCEDURE `bhmc`.`SearchPlayers`(IN pattern VARCHAR(20), IN playerId INT, IN eventId INT)
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
		,p.is_member 
		,p.last_season 
	FROM register_player p
	WHERE (p.id = playerId OR playerId = 0) 
	AND (LOWER(email) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(first_name) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(last_name) LIKE CONCAT('%', LOWER(pattern), '%'));
END

CREATE PROCEDURE `bhmc`.`TopGrossPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.gross_points) AS total_points 
	FROM damcup_seasonlongpoints slp 
	JOIN register_player p ON slp.player_id = p.id 
	JOIN events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.gross_points) DESC
	LIMIT topN;
END

CREATE PROCEDURE `bhmc`.`TopNetPoints`(IN season INT, IN topN INT)
BEGIN
	SELECT 
		 p.first_name
		,p.last_name 
		,p.id 
		,SUM(slp.net_points) AS total_points 
	FROM damcup_seasonlongpoints slp 
	JOIN egister_player p ON slp.player_id = p.id 
	JOIN events_event e ON slp.event_id = e.id
	WHERE e.season = season
	GROUP BY 
		 p.first_name
		,p.last_name 
		,p.id 
	ORDER BY SUM(slp.net_points) DESC
	LIMIT topN;
END

CREATE PROCEDURE `bhmc`.`PaymentDetails`(IN payment_id INT)
BEGIN
	SELECT 
		 t.name AS event_fee 
		,fee.amount AS event_fee_amount
		,fee.override_amount
		,fee.override_restriction 
		,f.amount AS amount_paid
		,f.is_paid
		,p.first_name
		,p.last_name
		,s.player_id 
	FROM register_registrationfee f
	JOIN register_registrationslot s ON f.registration_slot_id = s.id
	JOIN register_player p ON s.player_id = p.id 
	JOIN events_eventfee fee ON f.event_fee_id = fee.id 
	JOIN events_feetype t ON fee.fee_type_id = t.id
	WHERE f.payment_id = payment_id
	ORDER BY p.last_name, p.first_name;
END

CREATE PROCEDURE `bhmc`.`RefundDetails`(IN payment_id INT)
BEGIN
	SELECT 
		 pr.refund_code  
		,pr.refund_amount 
		,pr.refund_date 
		,pr.issuer_id 
		,pr.notes 
		,pr.confirmed 
		,u.first_name AS issuer_first_name
		,u.last_name AS issuer_last_name
	FROM payments_refund pr 
	LEFT JOIN auth_user u ON pr.issuer_id = u.id
	WHERE pr.payment_id = payment_id
	ORDER BY pr.refund_date;
END 

CREATE PROCEDURE `bhmc`.`GetPaymentsByEvent`(IN eventId INT)
BEGIN
	SELECT 
		 u.first_name 
		,u.last_name 
		,u.email 
		,pp.id 
		,pp.payment_code 
		,pp.payment_amount 
		,pp.transaction_fee 
		,pp.payment_date 
		,pp.confirm_date 
		,COALESCE(sub.refund_amount, 0) AS refund_amount
	FROM payments_payment pp 
	JOIN auth_user u ON pp.user_id = u.id 
	LEFT JOIN (
		SELECT r.payment_id, SUM(r.refund_amount) AS refund_amount
		FROM payments_refund r
		JOIN payments_payment p ON r.payment_id = p.id
		WHERE p.event_id = eventId
		GROUP BY r.payment_id
	) AS sub ON pp.id = sub.payment_id
	WHERE pp.event_id = eventId
	AND pp.confirmed = 1
	ORDER BY u.last_name, u.first_name, pp.payment_date;
END


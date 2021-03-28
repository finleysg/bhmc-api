CREATE PROCEDURE bhmc.GetRegistrationsByEvent(IN eventId INT)
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
END;

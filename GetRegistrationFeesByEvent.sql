CREATE PROCEDURE bhmc.GetRegistrationFeesByEvent(IN eventId INT)
BEGIN
	SELECT 
		 rs.player_id 
		,rf.event_fee_id 
		,rf.is_paid 
	FROM register_registrationfee rf 
	JOIN register_registrationslot rs ON rf.registration_slot_id = rs.id
	WHERE rs.event_id = eventId
	AND rs.status = 'R';
END;

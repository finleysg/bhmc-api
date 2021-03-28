CREATE PROCEDURE bhmc.GetFriends(IN playerId INT, IN eventId INT, IN seasonEventId INT, IN previousSeasonEventId INT)
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
	FROM bhmc.register_player p
	JOIN bhmc.register_player_favorites f ON p.id = f.to_player_id 
	LEFT JOIN bhmc.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId 
	LEFT JOIN bhmc.register_registrationslot r2 ON p.id = r2.player_id AND r2.event_id = seasonEventId 
	LEFT JOIN bhmc.register_registrationslot r3 ON p.id = r3.player_id AND r3.event_id = previousSeasonEventId
	WHERE f.from_player_id = playerId;
END;

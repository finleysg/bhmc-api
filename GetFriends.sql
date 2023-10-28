CREATE PROCEDURE bhmc.GetFriends(IN playerId INT, IN eventId INT)
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
		,r1.status AS event_status
	FROM bhmc.register_player p
	JOIN bhmc.register_player_favorites f ON p.id = f.to_player_id 
	LEFT JOIN bhmc.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId
	WHERE f.from_player_id = playerId;
END;

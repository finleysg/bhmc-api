CREATE PROCEDURE bhmc.SearchPlayers(IN pattern VARCHAR(20), IN playerId INT, IN eventId INT)
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
	LEFT JOIN bhmc.register_registrationslot r1 ON p.id = r1.player_id AND r1.event_id = eventId
	WHERE (p.id = playerId OR playerId = 0) 
	AND (LOWER(email) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(first_name) LIKE CONCAT('%', LOWER(pattern), '%')
	OR LOWER(last_name) LIKE CONCAT('%', LOWER(pattern), '%'));
END;

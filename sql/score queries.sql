
select * from `bhmc-apr19`.register_playerhandicap where season = 2021 order by handicap


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
	FROM `bhmc-apr19`.register_player p
	JOIN `bhmc-apr19`.register_player_favorites f ON p.id = f.to_player_id 
	LEFT JOIN `bhmc-apr19`.register_registrationslot r1 ON f.to_player_id = r1.player_id AND r1.event_id = 400 
	LEFT JOIN `bhmc-apr19`.register_registrationslot r2 ON f.to_player_id = r2.player_id AND r2.event_id = 332 
	LEFT JOIN `bhmc-apr19`.register_registrationslot r3 ON f.to_player_id = r3.player_id AND r3.event_id = 264
	WHERE f.from_player_id = 201;
	
-- select count(*) / 9 from `bhmc-apr19`.damcup_scores s

select 
	 c.name
	,h.hole_number
	,h.par
	,AVG(s.score) as average_score
	,AVG(s.score) - h.par as over_par
	,MIN(s.score) as low_score
	,MAX(s.score) as high_score
	,RANK() OVER (PARTITION BY c.name ORDER BY AVG(s.score) - h.par DESC) hole_rank 
	,COUNT(1) as scores 
from `bhmc-apr19`.damcup_scores s
join `bhmc-apr19`.courses_hole h on s.hole_id = h.id 
join `bhmc-apr19`.courses_course c on h.course_id = c.id 
join `bhmc-apr19`.register_player p on s.player_id = p.id 
join `bhmc-apr19`.register_playerhandicap i on i.player_id = p.id
where p.tee = 'Club'
and i.handicap between 14 and 22
group by c.name, h.hole_number, h.par, p.tee

select 
	 c.name
	,AVG(s.score) - h.par as over_par
	,COUNT(1) as scores 
from `bhmc-apr19`.damcup_scores s
join `bhmc-apr19`.courses_hole h on s.hole_id = h.id 
join `bhmc-apr19`.courses_course c on h.course_id = c.id 
join `bhmc-apr19`.register_player p on s.player_id = p.id 
join `bhmc-apr19`.register_playerhandicap i on i.player_id = p.id
where p.tee = 'Gold'
-- and i.handicap >= 10
group by c.name

select 
	 e.name as event_name
	,e.start_date as event_date
	,p.first_name
	,p.last_name
	,p.ghin
	,i.handicap as oct_15_index
	,c.name as course
	,h.hole_number
	,h.par
	,s.score
from `bhmc-apr19`.damcup_scores s
join `bhmc-apr19`.courses_hole h on s.hole_id = h.id 
join `bhmc-apr19`.courses_course c on h.course_id = c.id 
join `bhmc-apr19`.events_event e on s.event_id = e.id
join `bhmc-apr19`.register_player p on s.player_id = p.id 
join `bhmc-apr19`.register_playerhandicap i on i.player_id = p.id
order by e.start_date, c.name, p.last_name, p.first_name, h.hole_number 

select event_id, count(*) from `bhmc-apr19`.damcup_scores group by event_id 

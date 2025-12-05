select 
   s.event_id
  ,s.player_id
  ,sum(score) as total_score
from scores_eventscore s
join events_event e on s.event_id = e.id
where e.season = 2025
and s.is_net = 0
group by s.event_id, s.player_id
having count(*) = 9
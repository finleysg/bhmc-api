WITH ordered AS (
  SELECT
    season,
    event_handicap,
    ROW_NUMBER() OVER (PARTITION BY season ORDER BY event_handicap) AS rn,
    COUNT(*)       OVER (PARTITION BY season) AS cnt
  FROM event_handicap
),
per_season AS (
  SELECT
    season,
    MIN(event_handicap)                AS min_handicap,
    MAX(event_handicap)                AS max_handicap,
    ROUND(AVG(event_handicap), 2)      AS mean_handicap,
    MAX(cnt)                           AS cnt
  FROM ordered
  GROUP BY season
),
median_vals AS (
  /* For odd count take middle value, for even take average of two middle values */
  SELECT
    p.season,
    CASE
      WHEN MOD(p.cnt, 2) = 1 THEN
        MAX(CASE WHEN o.rn = (p.cnt + 1) / 2 THEN o.event_handicap END)
      ELSE
        AVG(CASE WHEN o.rn IN (p.cnt / 2, p.cnt / 2 + 1) THEN o.event_handicap END)
    END AS median_handicap
  FROM per_season p
  JOIN ordered o ON o.season = p.season
  GROUP BY p.season
),
mode_vals AS (
  /* Most frequent event_handicap per season; ties broken by smallest handicap */
  SELECT season, event_handicap AS mode_handicap
  FROM (
    SELECT
      season,
      event_handicap,
      ROW_NUMBER() OVER (PARTITION BY season ORDER BY freq DESC, event_handicap ASC) AS rn
    FROM (
      SELECT season, event_handicap, COUNT(*) AS freq
      FROM event_handicap
      GROUP BY season, event_handicap
    ) t
  ) t2
  WHERE rn = 1
)

SELECT
  p.season,
  p.min_handicap,
  p.max_handicap,
  p.mean_handicap,
  ROUND(m.median_handicap, 2) AS median_handicap,
  mv.mode_handicap
FROM per_season p
JOIN median_vals m USING(season)
LEFT JOIN mode_vals mv USING(season)
ORDER BY p.season;
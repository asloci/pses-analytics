CREATE OR REPLACE TABLE yoy_changes AS
SELECT
    a.SUBINDICATORENG,
    a.INDICATORENG,
    a.SURVEYR AS year_from,
    b.SURVEYR AS year_to,
    a.mean_score AS score_from,
    b.mean_score AS score_to,
    b.mean_score - a.mean_score AS delta
FROM theme_scores a
JOIN theme_scores b
  ON a.SUBINDICATORID = b.SUBINDICATORID
  AND (
        (a.SURVEYR = 2019 AND b.SURVEYR = 2020)
     OR (a.SURVEYR = 2020 AND b.SURVEYR = 2022)
     OR (a.SURVEYR = 2022 AND b.SURVEYR = 2024)
      )
ORDER BY
    a.SUBINDICATORENG,
    a.SURVEYR

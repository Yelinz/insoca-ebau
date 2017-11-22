UPDATE "ANSWER_QUERY" SET
  "QUERY" = 'SELECT
  "LOCATION_ID", "NAME"
FROM
  "LOCATION"

WHERE
  "LOCATION_ID" IN (
    SELECT
      "LOCATION_ID"
    FROM
      "GROUP_LOCATION"
    WHERE
      "GROUP_ID" = [GROUP_ID]
    )
    OR
    [ROLE_ID] NOT IN (6, 7, 1105)
ORDER BY "NAME"'
WHERE "ANSWER_QUERY_ID" = 1;

UPDATE "ANSWER_QUERY" SET "QUERY" = 'SELECT DISTINCT
  "AUTHORITY"."AUTHORITY_ID",
  "AUTHORITY"."NAME"
FROM
  "AUTHORITY"
LEFT JOIN
  "GROUP_LOCATION" ON (
  "GROUP_ID" = [GROUP_ID]
)
LEFT JOIN
  "AUTHORITY_LOCATION" ON (
    "AUTHORITY"."AUTHORITY_ID" = "AUTHORITY_LOCATION"."AUTHORITY_ID"
  )
JOIN
  "AUTHORITY_AUTHORITY_TYPE" "AAT" ON (
    "AUTHORITY"."AUTHORITY_ID" = "AAT"."AUTHORITY_ID"
  )
JOIN
  "AUTHORITY_TYPE" "AT" ON (
    "AAT"."AUTHORITY_TYPE_ID" = "AT"."AUTHORITY_TYPE_ID"
  )
LEFT JOIN
  "FORM_GROUP_FORM" "FGF" ON (
    "FGF"."FORM_ID" = [URL_FORM_ID]
  )

WHERE (
  "GROUP_LOCATION"."LOCATION_ID" IS NULL
  OR
  (
    "GROUP_LOCATION"."LOCATION_ID" = "AUTHORITY_LOCATION"."LOCATION_ID"
    AND
    (
      ("FGF"."FORM_GROUP_ID" = 30 AND "AT"."TAG" = ''BG'')
      OR
      ("FGF"."FORM_GROUP_ID" = 141 AND "AT"."TAG" = ''NP'')
    )
  )
)
ORDER BY "AUTHORITY"."NAME"'
WHERE "ANSWER_QUERY_ID" = 41;

UPDATE "ANSWER_QUERY" SET "QUERY" = 'SELECT
 "ID", "DESCRIPTION"
FROM
 "MAP_ZONE2"'
WHERE "ANSWER_QUERY_ID" = 21;

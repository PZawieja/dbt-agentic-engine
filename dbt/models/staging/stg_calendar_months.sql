WITH source AS (

    SELECT month_date
    FROM {{ ref('calendar_months') }}

)

SELECT CAST(month_date AS DATE) AS month_date
FROM source

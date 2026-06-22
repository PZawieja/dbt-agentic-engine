WITH recognized AS (

    SELECT
        customer_id,
        month_date,
        recognized_revenue
    FROM {{ ref('int_revenue_recognized_monthly') }}

)

SELECT
    customer_id,
    month_date,
    recognized_revenue
FROM recognized

WITH line_items AS (

    SELECT
        customer_id,
        month_date,
        mrr_amount
    FROM {{ ref('stg_subscription_line_items') }}

)

SELECT
    customer_id,
    month_date,
    SUM(mrr_amount) AS mrr_amount
FROM line_items
GROUP BY
    customer_id,
    month_date

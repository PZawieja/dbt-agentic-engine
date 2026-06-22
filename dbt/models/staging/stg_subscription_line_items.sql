WITH source AS (

    SELECT
        line_item_id,
        subscription_id,
        customer_id,
        month_date,
        plan_name,
        mrr_amount
    FROM {{ ref('raw_subscription_line_items') }}

)

SELECT
    line_item_id,
    subscription_id,
    customer_id,
    CAST(month_date AS DATE) AS month_date,
    plan_name,
    CAST(mrr_amount AS DECIMAL(12, 2)) AS mrr_amount
FROM source

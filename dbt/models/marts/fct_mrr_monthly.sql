WITH mrr AS (

    SELECT
        customer_id,
        month_date,
        mrr_amount
    FROM {{ ref('int_customer_mrr_monthly') }}

)

SELECT
    customer_id,
    month_date,
    mrr_amount
FROM mrr

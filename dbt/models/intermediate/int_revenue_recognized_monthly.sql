WITH invoices AS (

    SELECT
        customer_id,
        recognized_month,
        amount
    FROM {{ ref('stg_invoices') }}

)

SELECT
    customer_id,
    recognized_month AS month_date,
    SUM(amount) AS recognized_revenue
FROM invoices
GROUP BY
    customer_id,
    recognized_month

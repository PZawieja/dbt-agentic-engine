WITH customers AS (

    SELECT
        customer_id,
        customer_name,
        segment,
        region,
        signup_date
    FROM {{ ref('stg_customers') }}

)

SELECT
    customer_id,
    customer_name,
    segment,
    region,
    signup_date
FROM customers

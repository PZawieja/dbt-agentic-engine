WITH source AS (

    SELECT
        subscription_id,
        original_customer_id,
        start_date,
        end_date,
        status
    FROM {{ ref('raw_subscriptions') }}

)

SELECT
    subscription_id,
    original_customer_id,
    CAST(start_date AS DATE) AS start_date,
    CAST(end_date AS DATE) AS end_date,
    status
FROM source

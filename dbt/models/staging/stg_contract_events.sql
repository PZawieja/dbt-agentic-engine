WITH source AS (

    SELECT
        event_id,
        event_date,
        event_type,
        subscription_id,
        old_customer_id,
        new_customer_id,
        old_plan,
        new_plan,
        mrr_delta,
        description
    FROM {{ ref('raw_contract_events') }}

)

SELECT
    event_id,
    CAST(event_date AS DATE) AS event_date,
    event_type,
    subscription_id,
    old_customer_id,
    new_customer_id,
    old_plan,
    new_plan,
    CAST(mrr_delta AS DECIMAL(12, 2)) AS mrr_delta,
    description
FROM source

WITH events AS (

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
    FROM {{ ref('stg_contract_events') }}

)

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
FROM events

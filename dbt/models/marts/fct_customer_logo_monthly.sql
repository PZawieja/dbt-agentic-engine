WITH bridge AS (

    SELECT
        customer_id
        , month_date
        , current_mrr
        , bridge_category
    FROM {{ ref('int_customer_mrr_bridge_monthly') }}

)

SELECT
    customer_id
    , month_date
    , current_mrr > 0 AS is_active
    , bridge_category = 'new' AS is_new_logo
    , bridge_category = 'churn' AS is_churned_logo
FROM bridge

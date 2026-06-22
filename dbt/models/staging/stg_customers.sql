WITH source AS (

    SELECT
        customer_id
        , customer_name
        , segment
        , region
        , signup_date
    FROM {{ ref('raw_customers') }}

)

SELECT
    customer_id
    , customer_name
    , segment
    , region
    , CAST(signup_date AS DATE) AS signup_date
FROM source

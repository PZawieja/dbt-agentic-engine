WITH source AS (

    SELECT
        invoice_id
        , subscription_id
        , customer_id
        , invoice_month
        , recognized_month
        , amount
    FROM {{ ref('raw_invoices') }}

)

SELECT
    invoice_id
    , subscription_id
    , customer_id
    , CAST(invoice_month AS DATE) AS invoice_month
    , CAST(recognized_month AS DATE) AS recognized_month
    , CAST(amount AS DECIMAL(12, 2)) AS amount
FROM source

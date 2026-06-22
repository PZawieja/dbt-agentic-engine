WITH bridge AS (

    SELECT
        month_date,
        current_mrr,
        prior_mrr,
        bridge_category
    FROM {{ ref('int_customer_mrr_bridge_monthly') }}

)

SELECT
    month_date,
    SUM(CASE WHEN bridge_category = 'new' THEN current_mrr ELSE 0 END)
        AS new_mrr,
    SUM(
        CASE
            WHEN
                bridge_category = 'expansion'
                THEN current_mrr - prior_mrr
            ELSE 0
        END
    ) AS expansion_mrr,
    SUM(
        CASE
            WHEN
                bridge_category = 'contraction'
                THEN current_mrr - prior_mrr
            ELSE 0
        END
    ) AS contraction_mrr,
    SUM(CASE WHEN bridge_category = 'churn' THEN prior_mrr * -1 ELSE 0 END)
        AS churned_mrr,
    SUM(current_mrr - prior_mrr) AS net_new_mrr
FROM bridge
GROUP BY month_date

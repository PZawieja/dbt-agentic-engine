WITH customer_mrr AS (

    SELECT
        customer_id,
        month_date,
        mrr_amount
    FROM {{ ref('int_customer_mrr_monthly') }}

),

customer_windows AS (

    SELECT
        customer_id,
        MIN(month_date) AS first_active_month,
        MAX(month_date) AS last_active_month
    FROM customer_mrr
    GROUP BY
        customer_id

),

calendar AS (

    SELECT month_date
    FROM {{ ref('stg_calendar_months') }}

),

customer_spine AS (

    -- spine runs one month past each customer's last active month so a drop to
    -- zero MRR shows up as a churn row instead of silently disappearing
    SELECT
        customer_windows.customer_id,
        calendar.month_date
    FROM customer_windows
    INNER JOIN calendar
        ON
            customer_windows.first_active_month <= calendar.month_date
            AND calendar.month_date
            <= CAST(
                customer_windows.last_active_month + INTERVAL '1 month' AS DATE
            )

),

spine_with_mrr AS (

    SELECT
        customer_spine.customer_id,
        customer_spine.month_date,
        COALESCE(customer_mrr.mrr_amount, 0) AS current_mrr
    FROM customer_spine
    LEFT JOIN customer_mrr
        ON
            customer_spine.customer_id = customer_mrr.customer_id
            AND customer_spine.month_date = customer_mrr.month_date

),

spine_with_prior AS (

    SELECT
        customer_id,
        month_date,
        current_mrr,
        COALESCE(
            LAG(current_mrr)
                OVER (PARTITION BY customer_id ORDER BY month_date),
            0
        ) AS prior_mrr
    FROM spine_with_mrr

)

SELECT
    customer_id,
    month_date,
    current_mrr,
    prior_mrr,
    current_mrr - prior_mrr AS mrr_delta,
    CASE
        WHEN prior_mrr = 0 AND current_mrr > 0 THEN 'new'
        WHEN prior_mrr > 0 AND current_mrr = 0 THEN 'churn'
        WHEN current_mrr > prior_mrr AND prior_mrr > 0 THEN 'expansion'
        WHEN current_mrr < prior_mrr AND current_mrr > 0 THEN 'contraction'
        ELSE 'no_change'
    END AS bridge_category
FROM spine_with_prior

CREATE OR REPLACE VIEW vw_invoice_status AS

WITH payments_agg AS (
    SELECT
        invoice_id,
        SUM(payment_amount) AS paid_amount,
        MAX(payment_date) AS final_payment_date
    FROM payments
    GROUP BY invoice_id
)

SELECT
    i.invoice_id,
    i.customer_id,
    i.invoice_date,
    i.due_date,
    i.invoice_amount,

    COALESCE(p.paid_amount, 0) AS paid_amount,

    i.invoice_amount
    - COALESCE(p.paid_amount, 0) AS outstanding_amount,

    p.final_payment_date,

    CASE
        WHEN COALESCE(p.paid_amount, 0) >= i.invoice_amount - 0.02
        THEN 'Paid'

        WHEN COALESCE(p.paid_amount, 0) = 0
        THEN 'Unpaid'

        ELSE 'Partially Paid'
    END AS payment_status,

    CASE
        WHEN p.final_payment_date IS NOT NULL
        THEN p.final_payment_date - i.due_date
    END AS payment_delay_days

FROM invoices i

LEFT JOIN payments_agg p
    ON i.invoice_id = p.invoice_id;
SELECT
    ROUND(SUM(invoice_amount), 2) AS total_invoiced,
    ROUND(SUM(paid_amount), 2) AS total_paid,
    ROUND(SUM(outstanding_amount), 2) AS outstanding_receivables,

    ROUND(
        100.0 * SUM(paid_amount)
        / SUM(invoice_amount),
        2
    ) AS collection_rate_pct

FROM vw_invoice_status;	
SELECT
    ROUND(
        SUM(outstanding_amount),
        2
    ) AS overdue_receivables

FROM vw_invoice_status

WHERE due_date < DATE '2026-03-31'
AND outstanding_amount > 0.01;
SELECT
    payment_status,
    COUNT(*) AS invoices,
    ROUND(SUM(invoice_amount), 2) AS invoice_value,
    ROUND(SUM(outstanding_amount), 2) AS outstanding_amount

FROM vw_invoice_status

GROUP BY payment_status

ORDER BY invoice_value DESC;
SELECT
    ROUND(
        AVG(payment_delay_days),
        2
    ) AS avg_payment_delay_days

FROM vw_invoice_status

WHERE payment_status = 'Paid';
SELECT
    c.customer_name,
    c.customer_segment,
    c.country,

    COUNT(v.invoice_id) AS invoices,

    ROUND(
        AVG(v.payment_delay_days),
        2
    ) AS avg_payment_delay_days,

    ROUND(
        SUM(v.outstanding_amount),
        2
    ) AS outstanding_amount

FROM vw_invoice_status v

JOIN customers c
    ON v.customer_id = c.customer_id

GROUP BY
    c.customer_id,
    c.customer_name,
    c.customer_segment,
    c.country

HAVING AVG(v.payment_delay_days) > 0

ORDER BY avg_payment_delay_days DESC

LIMIT 10;
WITH aging AS (
    SELECT
        invoice_id,
        outstanding_amount,

        CASE
            WHEN due_date >= DATE '2026-03-31'
                THEN 'Not Due'

            WHEN DATE '2026-03-31' - due_date BETWEEN 1 AND 30
                THEN '1-30 Days'

            WHEN DATE '2026-03-31' - due_date BETWEEN 31 AND 60
                THEN '31-60 Days'

            WHEN DATE '2026-03-31' - due_date BETWEEN 61 AND 90
                THEN '61-90 Days'

            ELSE '90+ Days'
        END AS aging_bucket

    FROM vw_invoice_status

    WHERE outstanding_amount > 0.01
)

SELECT
    aging_bucket,
    COUNT(*) AS invoices,
    ROUND(
        SUM(outstanding_amount),
        2
    ) AS outstanding_amount

FROM aging

GROUP BY aging_bucket

ORDER BY
    CASE aging_bucket
        WHEN 'Not Due' THEN 1
        WHEN '1-30 Days' THEN 2
        WHEN '31-60 Days' THEN 3
        WHEN '61-90 Days' THEN 4
        ELSE 5
    END;
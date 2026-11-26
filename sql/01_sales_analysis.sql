CREATE OR REPLACE VIEW vw_order_fulfillment AS

SELECT
    so.sales_order_id,
    so.customer_id,
    so.order_date,
    so.requested_delivery_date,
    so.order_status,

    MIN(d.delivery_date) AS first_delivery_date,
    MAX(d.delivery_date) AS final_delivery_date,

    COUNT(DISTINCT d.delivery_id) AS delivery_count,

    MAX(d.delivery_date) - so.order_date
        AS fulfillment_lead_time_days,

    MAX(d.delivery_date) - so.requested_delivery_date
        AS delay_days,

    CASE
        WHEN MAX(d.delivery_date) <= so.requested_delivery_date
        THEN 1
        ELSE 0
    END AS on_time_flag,

    CASE
        WHEN COUNT(DISTINCT d.delivery_id) > 1
        THEN 1
        ELSE 0
    END AS split_delivery_flag

FROM sales_orders so

LEFT JOIN deliveries d
    ON so.sales_order_id = d.sales_order_id

GROUP BY
    so.sales_order_id,
    so.customer_id,
    so.order_date,
    so.requested_delivery_date,
    so.order_status;
	SELECT
    COUNT(*) AS completed_orders,

    ROUND(
        AVG(fulfillment_lead_time_days),
        2
    ) AS avg_lead_time_days,

    ROUND(
        100.0 * AVG(on_time_flag),
        2
    ) AS on_time_delivery_pct,

    ROUND(
        100.0 * AVG(split_delivery_flag),
        2
    ) AS partial_delivery_pct

FROM vw_order_fulfillment

WHERE order_status = 'Completed'
AND final_delivery_date IS NOT NULL;
SELECT
    EXTRACT(YEAR FROM order_date) AS year,

    COUNT(*) AS completed_orders,

    ROUND(
        AVG(fulfillment_lead_time_days),
        2
    ) AS avg_lead_time_days,

    ROUND(
        100.0 * AVG(on_time_flag),
        2
    ) AS on_time_delivery_pct,

    ROUND(
        100.0 * AVG(split_delivery_flag),
        2
    ) AS split_delivery_pct

FROM vw_order_fulfillment

WHERE order_status = 'Completed'

GROUP BY year
ORDER BY year;
SELECT
    sales_order_id,
    order_date,
    requested_delivery_date,
    final_delivery_date,
    fulfillment_lead_time_days,
    delay_days,
    delivery_count

FROM vw_order_fulfillment

WHERE order_status = 'Completed'
AND delay_days > 0

ORDER BY delay_days DESC

LIMIT 10;
WITH ordered AS (

    SELECT
        sales_order_id,
        order_item,
        ordered_quantity

    FROM sales_order_items

),

delivered AS (

    SELECT
        sales_order_id,
        order_item,
        SUM(delivered_quantity)
            AS delivered_quantity

    FROM delivery_items

    GROUP BY
        sales_order_id,
        order_item
)

SELECT
    SUM(o.ordered_quantity)
        AS ordered_quantity,

    SUM(
        COALESCE(d.delivered_quantity, 0)
    ) AS delivered_quantity,

    ROUND(
        100.0
        * SUM(COALESCE(d.delivered_quantity, 0))
        / SUM(o.ordered_quantity),
        2
    ) AS fill_rate_pct,

    SUM(o.ordered_quantity)
    -
    SUM(COALESCE(d.delivered_quantity, 0))
        AS open_quantity

FROM ordered o

JOIN sales_orders so
    ON o.sales_order_id = so.sales_order_id

LEFT JOIN delivered d
    ON o.sales_order_id = d.sales_order_id
    AND o.order_item = d.order_item

WHERE so.order_status <> 'Cancelled';
WITH order_type AS (

    SELECT
        soi.sales_order_id,

        MAX(
            CASE
                WHEN p.product_category = 'IoT'
                THEN 1
                ELSE 0
            END
        ) AS contains_iot

    FROM sales_order_items soi

    JOIN products p
        ON soi.product_id = p.product_id

    GROUP BY soi.sales_order_id
)

SELECT
    CASE
        WHEN ot.contains_iot = 1
        THEN 'Contains IoT'
        ELSE 'No IoT'
    END AS order_type,

    COUNT(*) AS orders,

    ROUND(
        AVG(f.fulfillment_lead_time_days),
        2
    ) AS avg_lead_time_days,

    ROUND(
        100.0 * AVG(f.on_time_flag),
        2
    ) AS on_time_delivery_pct,

    ROUND(
        100.0 * AVG(f.split_delivery_flag),
        2
    ) AS split_delivery_pct

FROM vw_order_fulfillment f

JOIN order_type ot
    ON f.sales_order_id = ot.sales_order_id

WHERE f.order_status = 'Completed'

GROUP BY ot.contains_iot

ORDER BY ot.contains_iot DESC;
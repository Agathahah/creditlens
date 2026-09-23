-- Only exact approved statuses may produce a non-NULL retrospective label.
-- IS DISTINCT FROM also detects an incorrect NULL or an invented label for NULL status.
{% for model_name, key in [('lc_loans_clean', 'loan_id'), ('loan_features', 'id'), ('final_features', 'id')] %}
SELECT '{{ model_name }}' AS model_name, {{ key }} AS loan_id,
    loan_status, is_default AS actual_label
FROM {{ ref(model_name) }}
WHERE is_default IS DISTINCT FROM (
    CASE
        WHEN loan_status = 'Fully Paid' THEN 0
        WHEN loan_status IN ('Charged Off', 'Default') THEN 1
        ELSE NULL
    END
)
{% if not loop.last %}UNION ALL{% endif %}
{% endfor %}

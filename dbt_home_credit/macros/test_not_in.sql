{% test not_in(model, column_name, values) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} in (
    {% for value in values -%}
        '{{ value }}'{% if not loop.last %},{% endif %}
    {%- endfor %}
)

{% endtest %}

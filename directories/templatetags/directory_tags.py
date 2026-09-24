from decimal import Decimal
from django import template
register = template.Library()

@register.filter
def field_label(model_or_instance, name):
    return 'Код' if name == 'id' else model_or_instance._meta.get_field(name).verbose_name

@register.filter
def field_value(instance, name):
    value = getattr(instance, name)
    if isinstance(value, bool):
        if name == 'is_active':
            return 'Активен' if value else 'Неактивен'
        return 'Да' if value else 'Нет'
    if value is None or value == '':
        return '—'
    if isinstance(value, Decimal):
        return format(value, 'f').rstrip('0').rstrip('.').replace('.', ',')
    return str(value)

@register.filter
def form_field(form, name):
    return form[name]

from django import template
register = template.Library()

@register.filter
def permission_label(code):
    labels = {'company':'Предприятия','equipmenttype':'Типы техники','equipmentmodel':'Модели техники','equipmentattribute':'Признаки техники','warrantyattribute':'Признаки гарантийности','equipmentstatus':'Статусы техники','auditentry':'История изменений'}
    action, _, model = code.partition('_')
    return f"{labels.get(model, model)} — { {'view':'просмотр','add':'создание','change':'редактирование'}.get(action,action) }"

from django.db import migrations

ROLES = [
    ('SYS_ADMIN','Администратор системы','Управление пользователями, составом и правами ролей, согласование заявок и журнал доступа. Ведение всех справочников.'),
    ('NSI','Специалист НСИ','Создание, просмотр и редактирование нормативно-справочной информации.'),
    ('PLAN_SPEC','Специалист по планированию','Подготовка планирования обслуживания и ремонтов. Сейчас доступен просмотр справочников; рабочие процессы планирования будут добавлены позднее.'),
    ('SITE_HEAD','Начальник участка','Организация работ участка. Сейчас доступен просмотр справочников; управление работами участка будет добавлено позднее.'),
    ('REPAIR_ENG','Инженер по ремонту оборудования','Подготовка и сопровождение ремонта оборудования. Сейчас доступен просмотр справочников; ремонтные процессы будут добавлены позднее.'),
    ('SUPPLY_SPEC','Специалист по снабжению','Обеспечение работ материалами и запасными частями. Сейчас доступен просмотр справочников; снабжение будет добавлено позднее.'),
    ('FIN_SPEC','Специалист по финансам','Финансовое сопровождение сервиса. Сейчас доступен просмотр справочников; финансовые процессы будут добавлены позднее.'),
    ('PLAN_HEAD','Руководитель планирования','Контроль планирования работ. Сейчас доступен просмотр справочников; согласование планов будет добавлено позднее.'),
    ('SERVICE_HEAD','Руководитель сервиса','Контроль сервисной деятельности. Сейчас доступен просмотр справочников; управление сервисом будет добавлено позднее.'),
]

def seed(apps,schema_editor):
    Group = apps.get_model('auth','Group')
    Permission = apps.get_model('auth','Permission')
    ContentType = apps.get_model('contenttypes','ContentType')
    Role = apps.get_model('accounts','Role')
    all_ids, view_ids = [], []
    for model in ('company','equipmenttype','equipmentmodel','equipmentattribute','warrantyattribute','equipmentstatus'):
        ct,_ = ContentType.objects.get_or_create(app_label='directories',model=model)
        for action in ('view','add','change'):
            p,_ = Permission.objects.get_or_create(content_type=ct,codename=f'{action}_{model}',defaults={'name':f'Can {action} {model}'})
            all_ids.append(p.pk)
            if action == 'view': view_ids.append(p.pk)
    ct,_ = ContentType.objects.get_or_create(app_label='accounts',model='role')
    manage,_ = Permission.objects.get_or_create(content_type=ct,codename='manage_access',defaults={'name':'Управление ролями, пользователями и согласование заявок'})
    for code,name,scope in ROLES:
        group,_ = Group.objects.get_or_create(name=name)
        Role.objects.get_or_create(code=code,defaults={'name':name,'scope':scope,'group':group})
        group.permissions.add(*(all_ids if code in ('SYS_ADMIN','NSI') else view_ids))
        if code == 'SYS_ADMIN': group.permissions.add(manage)

class Migration(migrations.Migration):
    dependencies = [('accounts','0001_initial'),('directories','0001_initial')]
    operations = [migrations.RunPython(seed,migrations.RunPython.noop)]

import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import sharp from 'sharp';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root = path.resolve(import.meta.dirname, '../..');
const build = path.join(root, 'presentations/build');
const assets = path.join(root, 'presentations/assets');
const skill = 'C:/Users/i.petrikin/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const python = 'C:/Users/i.petrikin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const { resolvePresentationFont, finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const font = resolvePresentationFont({fontFamily:'Segoe UI'});
const p = Presentation.create({slideSize:{width:1600,height:900}});
const C = {blue:'#006cb5',dark:'#1c1e20',white:'#ffffff',gray:'#59636C',muted:'#B8C1C8',line:'#DCE3E8',pale:'#F2F6F9'};

const sources = {
 equipment:'exec-55d1f6e3-0db2-4938-83da-d830fa141e65.png',
 orders:'exec-0f2ba8b7-3c31-4909-8a32-2cef62743ea7.png',
 completion:'exec-e97f9275-d419-4755-87b7-909de18b56f1.png',
 analytics:'exec-2b70d6c3-e8bf-4ead-b5df-3e6727e942f6.png'
};
for (const [slug,name] of Object.entries(sources)) {
 await fs.copyFile(path.join('C:/Users/i.petrikin/.codex/generated_images/01a0669f-d81e-7843-ac97-0e93f35f3827',name),path.join(assets,slug+'.png'));
}
const brandedSources = JSON.parse(await fs.readFile(path.join(build,'renamed-assets.json'),'utf8'));
for (const [slug,source] of Object.entries(brandedSources)) {
 await fs.copyFile(source,path.join(assets,slug+'-branded.png'));
}
for (const variant of ['light','dark']) {
 await sharp(path.join(root,'static/branding/logo-'+variant+'.svg')).resize({width:1158}).png().toFile(path.join(assets,'logo-'+variant+'.png'));
}
const v3Assets=JSON.parse(await fs.readFile(path.join(build,'v3-assets.json'),'utf8'));
for(const [slug,source] of Object.entries(v3Assets)) await fs.copyFile(source,path.join(assets,slug+'-v3.png'));
await sharp(path.join(assets,'order-041-qr.svg')).flatten({background:'#ffffff'}).png().toFile(path.join(assets,'order-041-qr.png'));
function rect(s,x,y,w,h,fill,line='none') {
 return s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1}});
}
function text(s,value,x,y,w,h,size=26,color=C.dark,bold=false,name='') {
 const t=s.shapes.add({geometry:'textbox',name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=value;
 t.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'top'};
 return t;
}
async function img(s,file,x,y,w,h,alt,crop) {
 return s.images.add({blob:new Uint8Array(await fs.readFile(path.join(assets,file))),contentType:'image/png',position:{left:x,top:y,width:w,height:h},fit:crop?'cover':'contain',alt,...(crop?{crop}:{} )});
}
async function header(s,n,title,section='РАБОЧИЕ СЦЕНАРИИ') {
 text(s,section+'  /  '+String(n).padStart(2,'0'),56,27,1020,30,18,C.blue,true);
 text(s,title,56,76,1450,69,46,C.dark,true,'Slide title');
 await img(s,'logo-light.png',1194,22,350,57,'Фирменный логотип Ремонтный Центр — РЦ, Модуль');
}
function footer(s,n,note='Концепция интерфейса · демонстрационные данные',dark=false){
 text(s,note,56,854,1385,28,17,dark?C.muted:C.gray);
 text(s,String(n).padStart(2,'0')+' / 07',1465,854,90,28,17,dark?C.muted:C.gray);
}
function block(s,num,title,body,y){
 text(s,num,1160,y,62,40,23,C.blue,true);
 text(s,title,1160,y+42,385,76,28,C.dark,true);
 text(s,body,1160,y+116,385,118,24,C.gray);
}
function notes(s,body){
 s.speakerNotes.textFrame.setText(body+'\n\nИсточники: требования пользователя в текущем чате; analysis/implementation-proposal.md; analysis/requirements-source.md. Бренд: static/branding/logo-light.svg и logo-dark.svg, выбранная айдентика № 2 «Модуль», кириллица РЦ. Изображения экранов созданы с помощью OpenAI ImageGen для этой презентации 09.09.2026. Это концептуальные макеты будущего продукта, не снимки работающей системы. Все организации, номера и показатели на экранах — демонстрационные.');
}

// 1. Concept and process scope.
{
 const s=p.slides.add();s.background.fill=C.white;
 rect(s,0,0,610,900,C.dark);
 await img(s,'logo-dark.png',56,46,495,96,'Ремонтный Центр. Фирменный логотип');
 text(s,'Система\nуправления\nремонтами',56,232,515,230,60,C.white,true,'Slide title');
 text(s,'Единое рабочее место\nдля планирования, выполнения\nи контроля ТОиР.',56,519,498,145,30,C.white);
 text(s,'ПДМ 10 / 14 / 17 т\nШахтные самосвалы 30 / 45 т',56,737,500,85,25,C.muted);
 text(s,'КОНЦЕПЦИЯ  /  01',675,39,800,30,18,C.blue,true);
 text(s,'От карточки техники\nдо подтвержденного результата',675,92,850,116,42,C.dark,true);
 text(s,'Регламентное ТО-250, ТО-500 и далее,\nплановые и аварийные ремонты.',675,228,830,85,27,C.gray);
 const rows=[
  ['01','Оборудование и нормативы','Карточки машин, наработка, регламенты, техкарты.'],
  ['02','Заявка и планирование','Потребность заказчика, сроки и приоритет работ.'],
  ['03','Наряд-заказ и выполнение','Операции, ответственные, бригада и ресурсы.'],
  ['04','Подтверждение результата','Факт работ, материалы, проверка и история машины.'],
  ['05','Аналитика · следующий этап','Техническое состояние, отказы и простои.']
 ];
 rows.forEach((r,i)=>{
  const y=342+i*93;
  text(s,r[0],675,y,70,46,29,C.blue,true);
  text(s,r[1],755,y,780,40,28,C.dark,true);
  text(s,r[2],755,y+40,780,42,23,C.gray);
 });
 text(s,'Первый этап: веб-система без интеграций, отчетов и мобильного приложения.',675,831,825,48,19,C.gray);
 notes(s,'Назначение — связать данные по технике, нормативам, заявкам и фактическим работам в едином процессе. Система внедряется поэтапно с корректировкой под реальные бизнес-процессы компании. Аналитика показана как целевое развитие после MVP. Базовый технологический вариант: Django и веб-интерфейс, PostgreSQL, Ubuntu Server; точная архитектура уточняется перед реализацией.');
}

// 2–5. Large UI images with editable explanations.
const screens=[
 {n:2,slug:'equipment',title:'Единая база техники и нормативов',blocks:[
  ['01','Карточка оборудования','Тип машины, серийный номер, заказчик, участок и текущая наработка.'],
  ['02','Технологическая карта','Периодичность ТО, операции, нормы времени и специальности.'],
  ['03','Основа планирования','Техкарта связана с техникой и используется при подготовке наряда.']
 ],note:'Создание карточки оборудования и технологической карты показано двумя формами рядом. Нормы трудоемкости — условные для демонстрации интерфейса, не производственная инструкция. Версионность техкарт помогает сохранять норматив, по которому формировался конкретный наряд.'},
 {n:3,slug:'orders',title:'От обращения заказчика к заданию бригаде',blocks:[
  ['01','Входящая заявка','Сотрудник регистрирует обращение: техника, причина, вид работ и нужная дата.'],
  ['02','Внутренний наряд','Мастер задает состав работ, назначает бригаду и планирует сроки.'],
  ['03','Связь документов','Наряд сохраняет основание — заявку. Операции берутся из техкарты.']
 ],note:'В MVP заявку от заказчика вручную регистрирует сотрудник компании. Макет не подразумевает клиентский портал, электронную почту или интеграцию. Показан сценарий планового ТО; те же сущности могут использоваться для аварийного или планового ремонта после согласования процессов.'},
 {n:4,slug:'completion',title:'Выполненные работы проходят проверку',blocks:[
  ['01','Время каждого сотрудника','Начало и окончание работ, фактические часы каждого члена бригады и общий итог.'],
  ['02','QR-код наряда','Уникальный идентификатор связывает бумажный бланк и электронный наряд-заказ.'],
  ['03','Подписанный акт','К наряду прикрепляется скан или фото подписанного акта выполненных работ.']
 ],note:'Мастер проверяет факт работ и время каждого сотрудника, подтверждает результат либо возвращает на доработку. Пример без перерывов: Иванов 09:00–10:00 = 1,0 ч; Петров 09:00–09:42 = 0,7 ч; Сидоров 09:00–09:30 = 0,5 ч. Суммарные трудозатраты 2,2 чел·ч, а не длительность ремонта. Прикрепляется скан или фотография уже подписанного бумажного акта; юридически значимая электронная подпись не подразумевается. QR содержит RC:WO:835ea7cb-44d0-4758-a775-18014e533e4d, уникальный демонстрационный идентификатор НЗ-041. Это не URL работающего сервиса. В будущем приложение по этому идентификатору ищет наряд с учетом прав пользователя.'},
 {n:5,slug:'analytics',title:'Состояние и надежность парка — на одном экране',blocks:[
  ['01','Состояние парка','Какая техника готова к работе, находится на ТО или в ремонте.'],
  ['02','Показатели надежности','Наработка между отказами, время восстановления и причины простоев.'],
  ['03','Данные для решений','Выявление проблемных машин и узлов, уточнение планов обслуживания.']
 ],note:'Развитие после MVP: аналитика и отчеты не включаются автоматически в первый этап. Для расчетов нужны достоверные события отказов, интервалы простоев и показания наработки. Методики расчета, границы периода и трактовки показателей следует согласовать до реализации. Демонстрационная панель не является статистикой компании; графики и таблица не представляют единый реальный массив наблюдений.'}
];
for (const d of screens){
 const s=p.slides.add();s.background.fill=C.white;
 await header(s,d.n,d.title,d.n===5?'РАЗВИТИЕ ПОСЛЕ MVP':'РАБОЧИЕ СЦЕНАРИИ');
 rect(s,55,154,1022,682,C.white,C.line);
 await img(s,d.n===4?'completion-v3.png':d.slug+'-branded.png',56,155,1020,680,'Концептуальный экран с айдентикой РЦ: '+d.title);
 if(d.n===4) await img(s,'order-041-qr.png',56+1262*1020/1536,155+163*680/1024,205*1020/1536,205*680/1024,'QR НЗ-041: RC:WO:835ea7cb-44d0-4758-a775-18014e533e4d');
 d.blocks.forEach((b,i)=>block(s,...b,184+i*219));
 footer(s,d.n,d.n===5?'Следующий этап · демонстрационные показатели · методики расчета подлежат согласованию':undefined);
 notes(s,d.note);
}

// 6. Business value and incremental rollout.
{
 const s=p.slides.add();s.background.fill=C.dark;
 text(s,'ПРЕИМУЩЕСТВА  /  06',56,32,850,30,18,'#65B7EC',true);
 await img(s,'logo-dark.png',1194,22,350,57,'Фирменный логотип Ремонтный Центр');
 text(s,'Управляемый процесс ремонта\nи достоверная история техники',56,101,1440,146,54,C.white,true,'Slide title');
 const benefits=[
  ['01','Прозрачное выполнение','По каждой заявке видны статус, сроки,\nответственный и результат работ.'],
  ['02','Единые нормативы','Техкарты задают состав операций\nи основу для сравнения плана с фактом.'],
  ['03','История каждой машины','Работы, наработка и материалы собраны\nв одном месте и доступны специалистам.'],
  ['04','Развитие под ваши процессы','Функционал внедряется шагами:\nпроверяем на практике и корректируем.']
 ];
 benefits.forEach((b,i)=>{
  const x=56+(i%2)*772,y=323+Math.floor(i/2)*208;
  text(s,b[0],x,y,74,53,34,'#65B7EC',true);
  text(s,b[1],x+92,y+2,618,54,32,C.white,true);
  text(s,b[2],x+92,y+66,615,91,27,C.muted);
 });
 rect(s,56,765,1488,1,'#4C555B');
 text(s,'Начинаем с базовых процессов. Аналитику развиваем на накопленных данных.',56,790,1470,48,28,C.white);
 footer(s,6,'Ожидаемые преимущества · количественный эффект оценивается после пилота',true);
 notes(s,'Преимущества описывают ожидаемые возможности процесса, а не уже достигнутый эффект. Для оценки пилота можно согласовать измерение сроков обработки заявок, полноты истории и качества регистрации факта. Проценты экономии и сокращения простоев не заявляются: подтвержденных исходных данных нет. Развитие по шагам — прямое пожелание пользователя.');
}

// 7. Mobile crews: proposed stage after MVP.
{
 const s=p.slides.add();s.background.fill=C.white;
 await header(s,7,'Развитие','СЛЕДУЮЩИЙ ЭТАП ПОСЛЕ MVP');
 text(s,'Мобильные бригады',56,181,900,58,38,C.dark,true);
 text(s,'Специалист фиксирует выполнение и дефекты\nнепосредственно у машины.',56,250,900,89,29,C.gray);
 const mobileBlocks=[
  ['01','Работа по наряду','Открытие наряда по QR-коду, отметки в чек-листе ТО\nи учет собственного времени.'],
  ['02','Фото и видео дефектов','Снимок или видео с комментарием сохраняются\nв истории оборудования и передаются мастеру.'],
  ['03','Мобильная веб-версия','Интерфейс для телефона с установкой на главный экран.\nОбщий сервер Django и единая база PostgreSQL.']
 ];
 mobileBlocks.forEach((b,i)=>{
  const y=372+i*140;
  text(s,b[0],56,y,66,43,28,C.blue,true);
  text(s,b[1],142,y,815,49,30,C.dark,true);
  text(s,b[2],142,y+51,815,86,25,C.gray);
 });
 text(s,'При отсутствии связи: локальное сохранение и передача\nданных после подключения. Реализуется отдельным этапом.',142,792,855,62,22,C.gray);
 await img(s,'mobile-v3.png',1030,144,493,704,'Демонстрация мобильной версии: чек-лист ТО, прикрепленная фотография оборванного провода на ПДМ, передача мастеру');
 footer(s,7,'Концепция мобильной версии · демонстрационные данные и изображение дефекта');
 notes(s,'Предлагаемый следующий этап после MVP — мобильная веб-версия (PWA) для работы бригады у оборудования с общим сервером и базой данных. Специалист отмечает выполненные операции, указывает личное время, прикладывает фото или видео дефектов и передает результат мастеру. Мастер проверяет результат; отметки в чек-листе не означают разрешения на эксплуатацию машины с открытым дефектом. На макете показан оборванный провод ПДМ с состоянием «Требует устранения». Фотография сгенерирована и служит иллюстрацией. Автономная работа проектируется отдельно: локальное хранение очереди изменений и вложений, индикация синхронизации, повторная передача и разрешение конфликтов. Поддержку камеры, видео и локального хранения необходимо проверить на фактических устройствах. Мобильная версия еще не реализована.');
}

await fs.mkdir(path.join(build,'renders'),{recursive:true});
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('Candidate exported');
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,'renders',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log('Rendered slide '+(i+1));
}
if (process.argv.includes('--render-only')) process.exit(0);
const finalPath=path.join(root,'output/presentations/Remontny-Centr-concept-7-slides-v3.pptx');
const result=await finalizePresentation({
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'v3.validation.json')
});
console.log(JSON.stringify(result));

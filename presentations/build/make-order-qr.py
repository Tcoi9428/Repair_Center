from pathlib import Path
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderSVG
import json

assets = Path(__file__).resolve().parent.parent / 'assets'
payload = 'RC:WO:835ea7cb-44d0-4758-a775-18014e533e4d'
qr = QrCodeWidget(payload, barLevel='M', barWidth=410, barHeight=410, barBorder=4)
drawing = Drawing(410, 410)
drawing.add(qr)
renderSVG.drawToFile(drawing, str(assets / 'order-041-qr.svg'))
(assets / 'order-041-qr.json').write_text(json.dumps({'order':'НЗ-041','payload':payload,'demo':True,'purpose':'Уникальный демонстрационный идентификатор наряд-заказа. Не ссылка на опубликованную систему.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('QR generated:', payload)

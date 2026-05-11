import re 
content = open('pages/dashboard.py', 'r', encoding='utf-8').read() 
content = content.replace('applymap', 'map') 
content = content.replace(".style.map(color_sla, subset=['SLA %%'])\n                use_container_width", ".style.map(color_sla, subset=['SLA %%']),\n                use_container_width") 
open('pages/dashboard.py', 'w', encoding='utf-8').write(content) 
print('LISTO - archivo corregido') 

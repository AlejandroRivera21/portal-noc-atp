import pandas as pd 
df = pd.read_csv('data/timeout_history.csv', encoding='latin-1') 
df.to_csv('data/timeout_history.csv', index=False, encoding='utf-8-sig') 
print('Listo -', len(df), 'registros convertidos') 

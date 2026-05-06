import pandas as pd 
df = pd.read_csv('data/timeout_history.csv', encoding='utf-8-sig') 
df['proceso'] = df['proceso'].str.encode('latin-1', errors='ignore').str.decode('utf-8', errors='ignore') 
df['descripcion'] = df['descripcion'].str.encode('latin-1', errors='ignore').str.decode('utf-8', errors='ignore') 
df.to_csv('data/timeout_history.csv', index=False, encoding='utf-8-sig') 
print('Listo -', len(df), 'registros corregidos') 

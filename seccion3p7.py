
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

con = sqlite3.connect('cps_lab3.db')
df = pd.read_sql_query('SELECT id, ts, a0 FROM tramas ORDER BY id', con)
con.close()

df['ts'] = pd.to_datetime(df['ts'])
inicio = pd.Timestamp('2026-10-08 15:00:00')
df['minuto'] = (df['ts'] - inicio).dt.total_seconds() / 60


df['cambio'] = df['a0'].diff().abs()
df['cambio_grande'] = df['cambio'] > 20


df['fallo'] = (
    df['cambio_grande'].rolling(window=5, center=True, min_periods=5).sum() >= 4
)

marcadas = df[df['fallo']]
fuera_20 = marcadas[(marcadas['minuto'] < 20) | (marcadas['minuto'] >= 21)]
print('Tramas marcadas:', len(marcadas))
print('Primera trama marcada:', marcadas['ts'].min())
print('Última trama marcada:', marcadas['ts'].max())
print('Intervalo de minutos:', round(marcadas['minuto'].min(), 3), 'a', round(marcadas['minuto'].max(), 3))
print('Falsos positivos fuera del minuto 20:', len(fuera_20))
print('Marcadas minuto 4:', len(marcadas[(marcadas['minuto'] >= 4) & (marcadas['minuto'] < 5)]))
print('Marcadas minuto 8:', len(marcadas[(marcadas['minuto'] >= 8) & (marcadas['minuto'] < 9)]))

plt.figure(figsize=(11,4.9))
plt.plot(df['minuto'], df['a0'], '.', ms=3, alpha=0.7, label='Lecturas A0')
plt.scatter(marcadas['minuto'], marcadas['a0'], c='#E06C4E', s=27, zorder=4, label='Tramas marcadas')
plt.xlabel('Minuto de captura (desde las 15:00:00)')
plt.ylabel('Lectura A0 (0–1023)')
plt.title('Detección de entrada flotante en A0')
plt.xticks(range(0,31,2))
plt.grid(alpha=0.2)
plt.legend(loc='upper right')
plt.tight_layout()
plt.savefig('pregunta7_a0.png', dpi=160)
plt.close()

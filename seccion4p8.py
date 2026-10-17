import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

con = sqlite3.connect("cps_lab3.db")
df = pd.read_sql_query("SELECT ts, t_mcu FROM tramas ORDER BY id", con)
con.close()

df["minuto"] = (pd.to_datetime(df["ts"]) - pd.Timestamp("2026-10-08 15:00:00")).dt.total_seconds() / 60
df = df[df["minuto"].between(13, 17)]

plt.plot(df["minuto"], df["t_mcu"])
plt.xlabel("Minuto de captura")
plt.ylabel("Temperatura (°C)")
plt.title("Temperatura interna del Arduino")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("grafico8.png")
plt.show()

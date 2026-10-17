import sqlite3
import pandas as pd

con = sqlite3.connect("cps_lab3.db")

df = pd.read_sql_query("""
    SELECT id, ts, seq, t_ms
    FROM tramas
    ORDER BY id
""", con)

df["ts"] = pd.to_datetime(df["ts"])


df["ts_anterior"] = df["ts"].shift(1)
df["seq_anterior"] = df["seq"].shift(1)
df["t_ms_anterior"] = df["t_ms"].shift(1)

df["dt"] = (
    df["ts"] - df["ts_anterior"]
).dt.total_seconds()


desconexiones = df[
    (df["dt"] > 10) &
    (df["seq"] == 1) &
    (df["t_ms"] < df["t_ms_anterior"])
].copy()

print(desconexiones[
    ["ts_anterior", "ts", "dt"]
].to_string(index=False))


basura = pd.read_sql_query("""
    SELECT ts
    FROM rechazos
    WHERE causa = 'basura'
""", con)

basura["ts"] = pd.to_datetime(basura["ts"])

for _, fila in desconexiones.iterrows():
    encontrada = (
        (basura["ts"] > fila["ts_anterior"]) &
        (basura["ts"] < fila["ts"])
    ).any()

    print(f"Reconexión: {fila['ts']}")
    print(f"Basura durante el intervalo: {encontrada}")


T = (
    df["ts"].iloc[-1] - df["ts"].iloc[0]
).total_seconds()

print("Tiempo total:", T)

n_fallas = len(desconexiones)
tiempo_reparacion = desconexiones["dt"].sum()

MTTR = tiempo_reparacion / n_fallas

tiempo_operativo = T - tiempo_reparacion

MTBF = tiempo_operativo / n_fallas

A = 100 * MTBF / (MTBF + MTTR)

print(f"MTTR: {MTTR:.3f} s")
print(f"MTBF: {MTBF:.3f} s")
print(f"Disponibilidad operacional: {A:.2f} %")

con.close()
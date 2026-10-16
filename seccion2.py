import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

con = sqlite3.connect("cps_lab3.db")
cur = con.cursor()

# ==========================================
# PREGUNTA 4: Disponibilidad por tramas
# ==========================================
# Detalle por sesión usando la función de ventana del Anexo
query_detalle_sesiones = """
WITH numeradas AS (
    SELECT id, ts, seq, t_ms,
           SUM(CASE WHEN seq = 1 THEN 1 ELSE 0 END) OVER (ORDER BY id) AS sesion
    FROM tramas
)
SELECT sesion,
       MIN(ts) AS inicio_ts,
       MAX(ts) AS fin_ts,
       COUNT(*) AS tramas_recibidas,
       MAX(seq) AS max_seq
FROM numeradas
GROUP BY sesion
ORDER BY sesion;
"""

df_sesiones = pd.read_sql_query(query_detalle_sesiones, con)
print("=== 4. DETALLE POR SESIÓN ===")
print(df_sesiones.to_string(index=False))

# Cálculo de la tabla resumen de la Pregunta 4 en SQL
query_tabla_p4 = """
WITH numeradas AS (
    SELECT id, seq,
           SUM(CASE WHEN seq = 1 THEN 1 ELSE 0 END) OVER (ORDER BY id) AS sesion
    FROM tramas
),
max_por_sesion AS (
    SELECT sesion, MAX(seq) AS max_seq, COUNT(*) AS n_val_sesion
    FROM numeradas
    GROUP BY sesion
),
totales AS (
    SELECT COUNT(*) AS n_sesiones,
           SUM(max_seq) AS n_esp,
           SUM(n_val_sesion) AS n_val,
           (SELECT COUNT(*) FROM rechazos WHERE causa IN ('checksum', 'truncada')) AS n_corr
    FROM max_por_sesion
)
SELECT n_sesiones,
       n_esp,
       n_val,
       n_corr,
       (n_esp - n_val - n_corr) AS n_perd,
       ROUND(100.0 * n_val / n_esp, 2) AS D_porcentaje
FROM totales;
"""

n_ses, n_esp, n_val, n_corr, n_perd, d_pct = cur.execute(query_tabla_p4).fetchone()
print("\n=== 4. TABLA DE DISPONIBILIDAD POR TRAMAS ===")
print(f"N° de sesiones : {n_ses}")
print(f"N_esp          : {n_esp}")
print(f"N_val          : {n_val}")
print(f"N_corr         : {n_corr}")
print(f"N_perd         : {n_perd}")
print(f"D [%]          : {d_pct:.2f} %")


# ==========================================
# PREGUNTA 5a: Throughput y temporización
# ==========================================
df = pd.read_sql_query("SELECT * FROM tramas ORDER BY id", con)
df["ts_dt"] = pd.to_datetime(df["ts"])

# Tiempo T (en segundos) entre la primera y la última trama válida según ts
T = (df["ts_dt"].iloc[-1] - df["ts_dt"].iloc[0]).total_seconds()
X = n_val / T  # Throughput [tramas/s]

# Largo promedio L en bytes (desde '$' hasta el último dígito de CS + 2 bytes por \r\n)
# Se reconstruye la trama o se mide desde las válidas
largos_tramas = (
    df.apply(
        lambda r: len(f"$CPS,{int(r['seq'])},{int(r['t_ms'])},{r['t_mcu']:.1f},{int(r['a0'])},{int(r['pulsos'])},{int(r['boton'])}*XX") + 2,
        axis=1
    )
)
L = largos_tramas.mean()

# Tasa de bits R (8N1 -> 10 bits/byte) y utilización del enlace rho (sobre 115200 bps)
R = 10.0 * L * X
rho = 100.0 * (R / 115200.0)

print("\n=== 5a. THROUGHPUT Y UTILIZACIÓN DEL ENLACE ===")
print(f"Tiempo total T          : {T:.3f} s")
print(f"Throughput X            : {X:.4f} tramas/s")
print(f"Largo promedio L        : {L:.2f} bytes/trama")
print(f"Tasa de bits R (8N1)    : {R:.2f} bit/s")
print(f"Utilización del canal ρ : {rho:.4f} %")


# ==========================================
# PREGUNTA 5b: Intervalos dt_k e Histograma
# ==========================================
df["dt"] = df["ts_dt"].diff().dt.total_seconds()
dt = df["dt"].dropna()

cat_1 = (dt < 3).sum()
cat_2 = ((dt >= 3) & (dt < 5)).sum()
cat_3 = ((dt >= 5) & (dt <= 10)).sum()
cat_4 = (dt > 10).sum()

print("\n=== 5b. CLASIFICACIÓN DE INTERVALOS dt_k ===")
print(f"Total de intervalos (N_val - 1) : {len(dt)}")
print(f"  1) dt < 3 s         : {cat_1}")
print(f"  2) 3 <= dt < 5 s    : {cat_2}")
print(f"  3) 5 <= dt <= 10 s  : {cat_3}")
print(f"  4) dt > 10 s        : {cat_4}")

# Mostrar el detalle de los intervalos mayores a 3 s para análisis
print("\nDetalle de intervalos dt >= 3 s:")
print(df.loc[df["dt"] >= 3, ["id", "ts", "seq", "dt"]].to_string(index=False))

# Gráfico del histograma con eje vertical logarítmico
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(dt, bins=30, edgecolor="black", alpha=0.8)
ax.set_yscale("log")
ax.set_xlabel(r"Intervalo entre tramas válidas consecutivas $\Delta t_k$ [s]")
ax.set_ylabel("Frecuencia (escala logarítmica)")
ax.set_title(r"Histograma de intervalos $\Delta t_k$ entre tramas válidas")
ax.grid(True, which="both", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("histograma_dt.png", dpi=150)
print("\nGráfico guardado como 'histograma_dt.png'")

con.close()
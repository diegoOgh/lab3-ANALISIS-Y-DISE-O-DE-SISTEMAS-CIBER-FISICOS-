import os
import math
import sqlite3
from collections import Counter

HEX_DIGITS = set("0123456789ABCDEFabcdef")

# ==========================================
# PREGUNTA 1.1: Función validar(linea)
# ==========================================
def validar(linea):
    """Retorna (campos, causa). Si la linea se rechaza, campos es None."""
    # 1. Causa "basura": la línea no comienza con '$'
    if not linea.startswith("$"):
        return None, "basura"

    # 2. Causa "truncada": no contiene '*' o CS no tiene exactamente 2 dígitos hex
    if "*" not in linea:
        return None, "truncada"
    
    cuerpo, cs = linea[1:].split("*", 1)
    if len(cs) != 2 or not all(c in HEX_DIGITS for c in cs):
        return None, "truncada"

    # 3. Causa "checksum": el XOR calculado entre '$' y '*' no coincide con CS
    xor_calc = 0
    for c in cuerpo:
        xor_calc ^= ord(c)
    
    if xor_calc != int(cs, 16):
        return None, "checksum"

    # 4. Causa "formato": identificador != CPS, != 7 campos o algún campo no numérico
    partes = cuerpo.split(",")
    if len(partes) != 7 or partes[0] != "CPS":
        return None, "formato"

    try:
        seq = int(partes[1])
        t_ms = int(partes[2])
        t_mcu = float(partes[3])
        a0 = int(partes[4])
        pulsos = int(partes[5])
        boton = int(partes[6])
        if not math.isfinite(t_mcu):
            return None, "formato"
    except ValueError:
        return None, "formato"

    campos = (seq, t_ms, t_mcu, a0, pulsos, boton)
    return campos, "ok"


# --- Lectura y clasificación de captura_nodo.txt ---
validas, rechazos = [], []
conteo_causas = Counter()

with open("captura_nodo.txt", encoding="utf-8") as f:
    for linea in f:
        if linea.startswith("#"):
            continue
        ts, texto = linea.rstrip("\r\n").split(";", 1)
        campos, causa = validar(texto)
        
        if causa == "ok":
            validas.append((ts, *campos))
        else:
            rechazos.append((ts, texto, causa))
            conteo_causas[causa] += 1

print("=== 1.1 RESUMEN DE VALIDACIÓN EN PYTHON ===")
print(f"Total líneas de datos (sin '#'): {len(validas) + len(rechazos)}")
print(f"Tramas válidas ('ok'):           {len(validas)}")
print(f"Total líneas rechazadas:         {len(rechazos)}")
for c in ["basura", "truncada", "checksum", "formato"]:
    print(f"  - {c}: {conteo_causas[c]}")


# ==========================================
# PREGUNTA 1.2: Carga en SQLite (cps_lab3.db)
# ==========================================
db_path = "cps_lab3.db"
if os.path.exists(db_path):
    os.remove(db_path)  # Limpia la base previa si re-ejecutas el script

con = sqlite3.connect(db_path)
cur = con.cursor()

# Creación del esquema exigido
cur.executescript("""
CREATE TABLE tramas (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, seq INTEGER, t_ms INTEGER,
    t_mcu REAL, a0 INTEGER, pulsos INTEGER, boton INTEGER
);

CREATE TABLE rechazos (
    id INTEGER PRIMARY KEY, ts TEXT NOT NULL, linea TEXT, causa TEXT
);
""")

# Carga masiva con executemany dentro de una única transacción
with con:
    cur.executemany(
        """INSERT INTO tramas (ts, seq, t_ms, t_mcu, a0, pulsos, boton)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        validas
    )
    cur.executemany(
        """INSERT INTO rechazos (ts, linea, causa)
           VALUES (?, ?, ?)""",
        rechazos
    )

# Verificación del número de filas mediante consultas SQL
n_tramas_sql = cur.execute("SELECT COUNT(*) FROM tramas;").fetchone()[0]
n_rechazos_sql = cur.execute("SELECT COUNT(*) FROM rechazos;").fetchone()[0]

print("\n=== 1.2 VERIFICACIÓN DE CARGA EN SQLITE ===")
print(f"Filas en tabla 'tramas':   {n_tramas_sql}")
print(f"Filas en tabla 'rechazos': {n_rechazos_sql}")


# ==========================================
# PREGUNTA 1.3: Verificación cruzada con respaldo
# ==========================================
cur.execute("ATTACH DATABASE 'cps_lab3_respaldo.db' AS ref;")

# 1. Comparación en tabla 'tramas': filas, SUM(seq), SUM(a0)
stats_propia = cur.execute(
    "SELECT COUNT(*), SUM(seq), SUM(a0) FROM main.tramas;"
).fetchone()
stats_ref = cur.execute(
    "SELECT COUNT(*), SUM(seq), SUM(a0) FROM ref.tramas;"
).fetchone()

print("\n=== 1.3 VERIFICACIÓN CRUZADA ===")
print(f"tramas (propia)   -> Filas: {stats_propia[0]}, SUM(seq): {stats_propia[1]}, SUM(a0): {stats_propia[2]}")
print(f"tramas (respaldo) -> Filas: {stats_ref[0]}, SUM(seq): {stats_ref[1]}, SUM(a0): {stats_ref[2]}")

# 2. Comparación en tabla 'rechazos' por causa
rech_propia = dict(cur.execute(
    "SELECT causa, COUNT(*) FROM main.rechazos GROUP BY causa;"
).fetchall())
rech_ref = dict(cur.execute(
    "SELECT causa, COUNT(*) FROM ref.rechazos GROUP BY causa;"
).fetchall())

print("\nComparación de 'rechazos' por causa (propia vs. respaldo):")
for c in ["basura", "truncada", "checksum", "formato"]:
    print(f"  - {c:8s}: propia = {rech_propia.get(c, 0)} | respaldo = {rech_ref.get(c, 0)}")

# 3. Operador EXCEPT en ambos sentidos
diff_propia_menos_ref = cur.execute("""
    SELECT ts, seq, t_ms, t_mcu, a0, pulsos, boton FROM main.tramas
    EXCEPT
    SELECT ts, seq, t_ms, t_mcu, a0, pulsos, boton FROM ref.tramas;
""").fetchall()

diff_ref_menos_propia = cur.execute("""
    SELECT ts, seq, t_ms, t_mcu, a0, pulsos, boton FROM ref.tramas
    EXCEPT
    SELECT ts, seq, t_ms, t_mcu, a0, pulsos, boton FROM main.tramas;
""").fetchall()

print(f"\nDiferencias (propia EXCEPT respaldo): {len(diff_propia_menos_ref)} filas")
for fila in diff_propia_menos_ref:
    print("  +", fila)

print(f"Diferencias (respaldo EXCEPT propia): {len(diff_ref_menos_propia)} filas")
for fila in diff_ref_menos_propia:
    print("  -", fila)

con.close()
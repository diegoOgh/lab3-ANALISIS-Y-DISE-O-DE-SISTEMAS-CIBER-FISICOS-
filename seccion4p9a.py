
import sqlite3
import pandas as pd

con = sqlite3.connect("cps_lab3.db")

consulta = """
SELECT a.ts, a.seq, b.ts AS ts_original, b.seq AS seq_original
FROM tramas a
JOIN tramas b
ON a.seq = b.seq
AND a.t_ms = b.t_ms
AND a.t_mcu = b.t_mcu
AND a.a0 = b.a0
AND a.boton = b.boton
AND b.id < a.id
ORDER BY a.id
"""

coincidencias = pd.read_sql_query(consulta, con)

replay = coincidencias[
    (coincidencias["ts"] >= "2026-10-08 15:22:00") &
    (coincidencias["ts"] < "2026-10-08 15:24:00")
]

print(replay.to_string(index=False))
print("Tramas repetidas:", len(replay))
print("Coincidencias fuera del ataque:",
      len(coincidencias) - len(replay))

con.close()

import subprocess
import time
import sys
from datetime import datetime

INTERVALO_HORAS = 6

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}")

def run_cycle():
    log("Iniciando ciclo...")
    try:
        result = subprocess.run(
            [sys.executable, "run.py"],
            capture_output=False
        )
        if result.returncode == 0:
            log("Ciclo completado correctamente")
        else:
            log(f"Ciclo terminado con error (codigo {result.returncode})")
    except Exception as e:
        log(f"Error ejecutando ciclo: {e}")

if __name__ == "__main__":
    log(f"NEXORA Scheduler iniciado — ciclos cada {INTERVALO_HORAS} horas")
    log("Ctrl+C para detener")
    print("=" * 60)

    run_cycle()

    while True:
        proxima = datetime.now().timestamp() + INTERVALO_HORAS * 3600
        proxima_str = datetime.fromtimestamp(proxima).strftime('%H:%M')
        log(f"Proximo ciclo a las {proxima_str}")
        time.sleep(INTERVALO_HORAS * 3600)
        run_cycle()

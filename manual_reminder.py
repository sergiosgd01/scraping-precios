"""Muestra un recordatorio si no se ha enviado el reporte manual de hoy."""

import datetime
import subprocess
from pathlib import Path


def reporte_enviado_hoy():
    fecha = datetime.date.today().strftime("%Y-%m-%d")
    return (Path("data") / f"actualizacion_manual_{fecha}.ok").exists()


if __name__ == "__main__":
    if not reporte_enviado_hoy():
        subprocess.run(
            [
                "osascript",
                "-e",
                'display notification "Aún no has actualizado los precios de HSN. Abre la actualización manual cuando puedas." with title "Precios HSN pendientes" sound name "Glass"',
            ],
            check=False,
        )

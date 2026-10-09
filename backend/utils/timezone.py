# /app/backend/utils/timezone.py
# Utilidad central de zona horaria para TODO el sistema.
# Guatemala no usa horario de verano: desfase fijo GMT-6 todo el año.
# Regla: "hoy" y la hora actual se calculan SIEMPRE en hora de Guatemala,
# sin importar la zona horaria del servidor.

from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo

GUATEMALA_TZ = ZoneInfo("America/Guatemala")


def now_gt() -> datetime:
    """Datetime actual con zona horaria de Guatemala (GMT-6)."""
    return datetime.now(GUATEMALA_TZ)


def today_gt() -> date:
    """Fecha de hoy (objeto date) en hora de Guatemala."""
    return now_gt().date()


def today_str_gt() -> str:
    """Fecha de hoy 'YYYY-MM-DD' en hora de Guatemala."""
    return now_gt().strftime("%Y-%m-%d")


def dia_gt_a_rango_utc(fecha_str: str):
    """Convierte un día de Guatemala 'YYYY-MM-DD' al rango UTC ISO [inicio, fin].

    El día local de Guatemala [00:00:00, 23:59:59] equivale en UTC a
    [fecha 06:00:00, fecha+1 05:59:59]. Así, los timestamps almacenados en
    UTC se agrupan correctamente por el día local de Guatemala.
    """
    inicio_gt = datetime.strptime(fecha_str, "%Y-%m-%d").replace(tzinfo=GUATEMALA_TZ)
    fin_gt = inicio_gt + timedelta(days=1) - timedelta(seconds=1)
    return (
        inicio_gt.astimezone(timezone.utc).isoformat(),
        fin_gt.astimezone(timezone.utc).isoformat(),
    )


def rango_gt_a_utc(fecha_inicio_str: str, fecha_fin_str: str):
    """Convierte un rango de días de Guatemala a rango UTC ISO [inicio, fin].

    inicio = fecha_inicio 00:00:00 (GT) -> UTC
    fin    = fecha_fin    23:59:59 (GT) -> UTC
    """
    inicio_gt = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").replace(tzinfo=GUATEMALA_TZ)
    fin_gt = (
        datetime.strptime(fecha_fin_str, "%Y-%m-%d").replace(tzinfo=GUATEMALA_TZ)
        + timedelta(days=1)
        - timedelta(seconds=1)
    )
    return (
        inicio_gt.astimezone(timezone.utc).isoformat(),
        fin_gt.astimezone(timezone.utc).isoformat(),
    )

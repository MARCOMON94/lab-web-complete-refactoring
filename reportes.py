import csv, io, json
from datetime import datetime

def generar_reporte_resenas(resenas: list[dict], formato: str) -> str:
    total = len(resenas)
    promedio = sum(r["puntuacion"] for r in resenas) / total if total else 0
    fecha = datetime.now().strftime("%Y-%m-%d")

    if formato == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "producto", "puntuacion", "sentimiento"])
        writer.writeheader()
        writer.writerows(resenas)
        return output.getvalue()

    elif formato == "json":
        return json.dumps({
            "fecha": fecha,
            "resenas": resenas,
            "resumen": {"total": total, "puntuacion_media": round(promedio, 2)}
        }, ensure_ascii=False, indent=2)

    elif formato == "txt":
        lineas = [f"REPORTE DE RESEÑAS — {fecha}", "=" * 40]
        for r in resenas:
            lineas.append(f"  #{r['id']} {r['producto']:25} {r['puntuacion']}/5  {r['sentimiento']}")
        lineas.append("=" * 40)
        lineas.append(f"  Media: {promedio:.2f}/5 sobre {total} reseñas")
        return "\n".join(lineas)

    else:
        raise ValueError(f"Formato no soportado: {formato}")
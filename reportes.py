import csv
import io
import json
from abc import ABC, abstractmethod
from datetime import datetime


def calcular_resumen(resenas: list[dict]) -> dict:
    total = len(resenas)
    promedio = sum(r["puntuacion"] for r in resenas) / total if total else 0

    return {
        "total": total,
        "promedio": promedio,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
    }


class GeneradorReporte(ABC):
    @abstractmethod
    def generar(self, resenas: list[dict]) -> str:
        ...


class ReporteCSV(GeneradorReporte):
    def generar(self, resenas: list[dict]) -> str:
        output = io.StringIO()

        campos = ["id", "producto", "puntuacion", "sentimiento"]
        writer = csv.DictWriter(output, fieldnames=campos)

        writer.writeheader()
        writer.writerows(resenas)

        return output.getvalue()


class ReporteJSON(GeneradorReporte):
    def generar(self, resenas: list[dict]) -> str:
        resumen = calcular_resumen(resenas)

        datos = {
            "fecha": resumen["fecha"],
            "resenas": resenas,
            "resumen": {
                "total": resumen["total"],
                "puntuacion_media": round(resumen["promedio"], 2),
            },
        }

        return json.dumps(datos, ensure_ascii=False, indent=2)


class ReporteTXT(GeneradorReporte):
    def generar(self, resenas: list[dict]) -> str:
        resumen = calcular_resumen(resenas)

        lineas = [
            f"REPORTE DE RESEÑAS — {resumen['fecha']}",
            "=" * 40,
        ]

        for resena in resenas:
            lineas.append(
                f"#{resena['id']} {resena['producto']} "
                f"{resena['puntuacion']}/5 {resena['sentimiento']}"
            )

        lineas.append("=" * 40)
        lineas.append(
            f"Media: {resumen['promedio']:.2f}/5 sobre {resumen['total']} reseñas"
        )

        return "\n".join(lineas)


class ReporteMarkdown(GeneradorReporte):
    def generar(self, resenas: list[dict]) -> str:
        resumen = calcular_resumen(resenas)

        lineas = [
            f"# Reporte de reseñas — {resumen['fecha']}",
            "",
            "| Producto | Puntuación | Sentimiento |",
            "|----------|------------|-------------|",
        ]

        for resena in resenas:
            lineas.append(
                f"| {resena['producto']} | "
                f"{resena['puntuacion']}/5 | "
                f"{resena['sentimiento']} |"
            )

        lineas.append("")
        lineas.append(
            f"**Media: {resumen['promedio']:.2f}/5 · "
            f"Total: {resumen['total']} reseñas**"
        )

        return "\n".join(lineas)


FORMATOS = {
    "csv": ReporteCSV,
    "json": ReporteJSON,
    "txt": ReporteTXT,
    "md": ReporteMarkdown,
}


def generar_reporte_resenas(resenas: list[dict], formato: str) -> str:
    if formato not in FORMATOS:
        raise ValueError(f"Formato no soportado: {formato}")

    generador = FORMATOS[formato]()

    return generador.generar(resenas)
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from analizador import (
    AnalizadorResenas,
    AuditorConsola,
    AlertaConsola,
    ClienteMock,
    RepositorioMemoria,
    ValidadorTexto,
)
from procesador import limpiar_resena
from reportes import generar_reporte_resenas


app = FastAPI(
    title="Sistema de reseñas refactorizado",
    description="Lab de refactorización aplicando KISS, DRY, SRP, OCP, LSP, ISP y DIP.",
    version="1.0.0",
)


RESENAS_EJEMPLO = [
    {
        "id": 1,
        "producto": "Teclado Pro",
        "puntuacion": 5,
        "sentimiento": "positivo",
    },
    {
        "id": 2,
        "producto": "Ratón Basic",
        "puntuacion": 2,
        "sentimiento": "negativo",
    },
    {
        "id": 3,
        "producto": "Monitor Ultra",
        "puntuacion": 4,
        "sentimiento": "positivo",
    },
]


class ProcesarTextoRequest(BaseModel):
    texto: str
    lowercase: bool = True
    strip_special: bool = True
    max_length: int = 1000
    min_palabras: int = 3


class AnalizarResenaRequest(BaseModel):
    resena_id: int
    texto: str


def crear_config_limpieza(datos: ProcesarTextoRequest) -> dict:
    return {
        "lowercase": datos.lowercase,
        "strip_special": datos.strip_special,
        "max_length": datos.max_length,
        "min_palabras": datos.min_palabras,
    }


def crear_respuesta_mock(texto: str) -> dict:
    texto_lower = texto.lower()

    palabras_negativas = ["malo", "tarde", "roto", "horrible", "defectuoso"]

    es_negativa = any(
        palabra in texto_lower
        for palabra in palabras_negativas
    )

    if es_negativa:
        return {
            "sentimiento": "negativo",
            "aspectos": ["calidad", "envío"],
            "resumen": "La reseña indica una mala experiencia.",
        }

    return {
        "sentimiento": "positivo",
        "aspectos": ["calidad"],
        "resumen": "La reseña indica una buena experiencia.",
    }


@app.get("/")
def home():
    return {
        "mensaje": "Sistema de reseñas funcionando",
        "documentacion": "/docs",
        "endpoints": [
            "POST /procesar",
            "POST /analizar",
            "GET /reportes?formato=csv|json|txt|md",
        ],
    }


@app.post("/procesar")
def procesar_texto(datos: ProcesarTextoRequest):
    config = crear_config_limpieza(datos)

    return limpiar_resena(datos.texto, config)


@app.post("/analizar")
def analizar_resena(datos: AnalizarResenaRequest):
    respuesta_mock = crear_respuesta_mock(datos.texto)

    analizador = AnalizadorResenas(
        validador=ValidadorTexto(),
        llm=ClienteMock(respuesta_mock),
        repo=RepositorioMemoria(),
        alertas=AlertaConsola(),
        auditor=AuditorConsola(),
    )

    return analizador.analizar(
        datos.resena_id,
        datos.texto,
    )


@app.get("/reportes")
def obtener_reporte(
    formato: Literal["csv", "json", "txt", "md"] = Query("json")
):
    contenido = generar_reporte_resenas(
        RESENAS_EJEMPLO,
        formato,
    )

    return PlainTextResponse(contenido)
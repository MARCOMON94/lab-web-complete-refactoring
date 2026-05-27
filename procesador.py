import re


def normalizar_espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip())


def quitar_caracteres_especiales(texto: str) -> str:
    return re.sub(r"[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9\s]", "", texto)


def limpiar_resena(texto: str, config: dict) -> dict:
    texto_procesado = normalizar_espacios(texto)

    if config.get("lowercase", True):
        texto_procesado = texto_procesado.lower()

    if config.get("strip_special", True):
        texto_procesado = quitar_caracteres_especiales(texto_procesado)

    max_length = config.get("max_length", 1000)
    texto_procesado = texto_procesado[:max_length]

    palabras = texto_procesado.split()

    stats = {
        "longitud": len(texto_procesado),
        "palabras": len(palabras),
        "tiene_numeros": any(caracter.isdigit() for caracter in texto_procesado),
    }

    valido = stats["longitud"] > 0 and stats["palabras"] >= config.get("min_palabras", 3)

    return {
        "original": texto,
        "procesado": texto_procesado,
        "stats": stats,
        "valido": valido,
    }
import re
from functools import reduce

def limpiar_resena(texto: str, config: dict) -> dict:
    pipeline = [
        lambda x: x.strip(),
        lambda x: re.sub(r'\s+', ' ', x),
        lambda x: x.lower() if config.get("lowercase", True) else x,
        lambda x: re.sub(r'[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9\s.,!?]', '', x) if config.get("strip_special", True) else x,
        lambda x: x[:config.get("max_length", 1000)] if len(x) > config.get("max_length", 1000) else x,
    ]

    texto_procesado = reduce(lambda acc, fn: fn(acc), pipeline, texto)

    palabras = texto_procesado.split()
    stats = {
        "longitud": len(texto_procesado),
        "palabras": len(palabras),
        "tiene_numeros": any(c.isdigit() for c in texto_procesado),
        "ratio_espacios": len([c for c in texto_procesado if c == ' ']) / len(texto_procesado) if texto_procesado else 0,
        "densidad_lexica": len(set(palabras)) / len(palabras) if palabras else 0,
    }

    return {
        "original": texto,
        "procesado": texto_procesado,
        "stats": stats,
        "valido": stats["longitud"] > 0 and stats["palabras"] >= config.get("min_palabras", 3),
    }
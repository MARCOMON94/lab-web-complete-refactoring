def assert_lanza_error(tipo_error, funcion, *args, **kwargs):
    try:
        funcion(*args, **kwargs)
        assert False, f"Se esperaba {tipo_error.__name__}"
    except tipo_error:
        pass


def test_limpiar_resena_basica():
    from procesador import limpiar_resena

    config = {
        "lowercase": True,
        "strip_special": True,
        "max_length": 50,
        "min_palabras": 3,
    }

    resultado = limpiar_resena("  Muy BUENO el producto!!!  ", config)

    assert resultado["procesado"] == "muy bueno el producto"
    assert resultado["valido"] is True
    assert resultado["stats"]["palabras"] == 4
    assert "ratio_espacios" not in resultado["stats"]
    assert "densidad_lexica" not in resultado["stats"]


def test_limpiar_resena_texto_corto():
    from procesador import limpiar_resena

    config = {
        "lowercase": True,
        "strip_special": True,
        "max_length": 50,
        "min_palabras": 3,
    }

    resultado = limpiar_resena("ok", config)

    assert resultado["valido"] is False


def test_limpiar_resena_recorta_longitud():
    from procesador import limpiar_resena

    config = {
        "lowercase": True,
        "strip_special": True,
        "max_length": 50,
        "min_palabras": 3,
    }

    resultado = limpiar_resena("A" * 100, config)

    assert resultado["procesado"] == "a" * 50
    assert resultado["stats"]["longitud"] == 50


def test_limpiar_resena_mantiene_numeros_y_acentos():
    from procesador import limpiar_resena

    config = {
        "lowercase": True,
        "strip_special": True,
        "max_length": 100,
        "min_palabras": 3,
    }

    resultado = limpiar_resena("  El envío tardó 2 días!!!  ", config)

    assert resultado["procesado"] == "el envío tardó 2 días"
    assert resultado["stats"]["tiene_numeros"] is True


def test_contrato_almacenamiento(storage):
    storage.guardar("test.bin", b"datos")

    assert storage.obtener("test.bin") == b"datos"

    try:
        storage.obtener("no_existe.bin")
        assert False, "Debe lanzar FileNotFoundError"
    except FileNotFoundError:
        pass

    assert storage.eliminar("test.bin") is True
    assert storage.eliminar("no_existe.bin") is False


def test_almacenamiento_local():
    import tempfile
    from almacenamiento import AlmacenamientoLocal

    with tempfile.TemporaryDirectory() as carpeta:
        storage = AlmacenamientoLocal(carpeta)
        test_contrato_almacenamiento(storage)


def test_almacenamiento_con_cache():
    import tempfile
    from almacenamiento import AlmacenamientoLocal, AlmacenamientoConCache

    with tempfile.TemporaryDirectory() as carpeta:
        storage_base = AlmacenamientoLocal(carpeta)
        storage_cache = AlmacenamientoConCache(storage_base)

        test_contrato_almacenamiento(storage_cache)


def test_procesar_adjuntos():
    import tempfile
    from almacenamiento import AlmacenamientoLocal, procesar_adjuntos

    with tempfile.TemporaryDirectory() as carpeta:
        storage = AlmacenamientoLocal(carpeta)

        storage.guardar("foto.jpg", b"12345")
        storage.guardar("documento.pdf", b"abcdef")

        resultado = procesar_adjuntos(
            storage,
            ["foto.jpg", "documento.pdf", "no_existe.txt"]
        )

        assert resultado["foto.jpg"] == "5_bytes"
        assert resultado["documento.pdf"] == "6_bytes"
        assert resultado["no_existe.txt"] == "no_encontrado"


def test_reporte_markdown():
    from reportes import generar_reporte_resenas

    resenas = [
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
    ]

    reporte = generar_reporte_resenas(resenas, "md")

    assert "# Reporte de reseñas" in reporte
    assert "| Producto | Puntuación | Sentimiento |" in reporte
    assert "| Teclado Pro | 5/5 | positivo |" in reporte
    assert "| Ratón Basic | 2/5 | negativo |" in reporte
    assert "Media: 3.50/5" in reporte
    assert "Total: 2 reseñas" in reporte


def test_reporte_formato_no_soportado():
    from reportes import generar_reporte_resenas

    assert_lanza_error(
        ValueError,
        generar_reporte_resenas,
        [],
        "excel"
    )


def test_repositorio_solo_lectura():
    from repositorio import RepositorioResenasSoloLectura

    resenas = [
        {
            "id": 1,
            "usuario_id": 10,
            "producto_id": 100,
            "texto": "Muy buen producto",
            "puntuacion": 5,
        },
        {
            "id": 2,
            "usuario_id": 11,
            "producto_id": 101,
            "texto": "Llegó tarde",
            "puntuacion": 2,
        },
    ]

    repo = RepositorioResenasSoloLectura(resenas)

    assert repo.obtener_por_id(1)["texto"] == "Muy buen producto"
    assert repo.obtener_por_id(999) is None
    assert len(repo.listar_todos()) == 2

    resultado_busqueda = repo.buscar({"puntuacion": 2})
    assert len(resultado_busqueda) == 1
    assert resultado_busqueda[0]["texto"] == "Llegó tarde"

    pagina = repo.paginar(pagina=1, por_pagina=1)
    assert pagina["total"] == 2
    assert len(pagina["resultados"]) == 1

    csv = repo.exportar_csv()
    assert "id,usuario_id,producto_id,texto,puntuacion" in csv
    assert "Muy buen producto" in csv


def test_resena_positiva_no_genera_alerta():
    from analizador import (
        AnalizadorResenas,
        ValidadorTexto,
        ClienteMock,
        RepositorioMemoria,
        AlertaConsola,
        AuditorConsola,
    )

    alertas = AlertaConsola()
    alertas_enviadas = []

    alertas.enviar_alerta = lambda mensaje: alertas_enviadas.append(mensaje)

    analizador = AnalizadorResenas(
        validador=ValidadorTexto(),
        llm=ClienteMock({
            "sentimiento": "positivo",
            "aspectos": ["calidad"],
            "resumen": "Muy bueno",
        }),
        repo=RepositorioMemoria(),
        alertas=alertas,
        auditor=AuditorConsola(),
    )

    resultado = analizador.analizar(
        1,
        "El producto es excelente, muy recomendable"
    )

    assert resultado["resena_id"] == 1
    assert resultado["sentimiento"] == "positivo"
    assert len(alertas_enviadas) == 0


def test_resena_negativa_genera_alerta():
    from analizador import (
        AnalizadorResenas,
        ValidadorTexto,
        ClienteMock,
        RepositorioMemoria,
        AlertaConsola,
        AuditorConsola,
    )

    alertas = AlertaConsola()
    alertas_enviadas = []

    alertas.enviar_alerta = lambda mensaje: alertas_enviadas.append(mensaje)

    analizador = AnalizadorResenas(
        validador=ValidadorTexto(),
        llm=ClienteMock({
            "sentimiento": "negativo",
            "aspectos": ["envío"],
            "resumen": "El envío fue malo",
        }),
        repo=RepositorioMemoria(),
        alertas=alertas,
        auditor=AuditorConsola(),
    )

    resultado = analizador.analizar(
        2,
        "El pedido llegó tarde y el embalaje estaba roto"
    )

    assert resultado["resena_id"] == 2
    assert resultado["sentimiento"] == "negativo"
    assert len(alertas_enviadas) == 1
    assert "Reseña negativa" in alertas_enviadas[0]


def test_resena_demasiado_corta_lanza_error():
    from analizador import (
        AnalizadorResenas,
        ValidadorTexto,
        ClienteMock,
        RepositorioMemoria,
        AlertaConsola,
        AuditorConsola,
    )

    analizador = AnalizadorResenas(
        validador=ValidadorTexto(),
        llm=ClienteMock({
            "sentimiento": "positivo",
            "aspectos": [],
            "resumen": "ok",
        }),
        repo=RepositorioMemoria(),
        alertas=AlertaConsola(),
        auditor=AuditorConsola(),
    )

    assert_lanza_error(
        ValueError,
        analizador.analizar,
        3,
        "ok"
    )



TESTS = [
    test_limpiar_resena_basica,
    test_limpiar_resena_texto_corto,
    test_limpiar_resena_recorta_longitud,
    test_limpiar_resena_mantiene_numeros_y_acentos,
    test_almacenamiento_local,
    test_almacenamiento_con_cache,
    test_procesar_adjuntos,
    test_reporte_markdown,
    test_reporte_formato_no_soportado,
    test_repositorio_solo_lectura,
    test_resena_positiva_no_genera_alerta,
    test_resena_negativa_genera_alerta,
    test_resena_demasiado_corta_lanza_error,
]


if __name__ == "__main__":
    tests_a_ejecutar = TESTS

    for test in tests_a_ejecutar:
        test()
        print(f"{test.__name__} pasado")

    print("Tests ejecutados correctamente")
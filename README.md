![logo_ironhack_blue 7](https://user-images.githubusercontent.com/23629340/40541063-a07a0a8a-601a-11e8-91b5-2f13e4e6b441.png)

# Lab | Sistema de Reseñas: Refactorización completa

## Contexto

Recibes el código base de un **sistema de análisis de reseñas de clientes**. Funciona. Pasan los tests de humo. Pero está mal diseñado y cada semana que pasa es más difícil de mantener.

Tu misión es refactorizarlo de arriba abajo aplicando los principios del día. Hay **7 partes**, una por principio, y todas forman parte del mismo proyecto.

## Setup

```bash
# fork & clone the repository
cd lab-web-complete-refactoring
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn langchain langchain-openai python-dotenv
pip freeze > requirements.txt
```

Estructura de archivos que tendrás al final:

```bash
lab-web-complete-refactoring/
├── main.py              # FastAPI app
├── procesador.py        # Parte 1 — KISS
├── repositorio.py       # Partes 2, 6 — DRY, ISP
├── analizador.py        # Partes 3, 7 — SRP, DIP
├── reportes.py          # Parte 4 — OCP
├── almacenamiento.py    # Parte 5 — LSP
└── tests.py             # Tests de verificación
```

---

## Parte 1 — KISS: el preprocesador de texto

El texto de las reseñas se limpia antes de analizarse. Alguien lo "optimizó" con lambdas y `reduce` y ahora nadie lo entiende.

**Código de partida** (`procesador.py`):

```python
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
```

**Tu tarea:**

1. Reescribe `limpiar_resena` eliminando el `reduce` y las lambdas encadenadas
2. Elimina las estadísticas que nadie usa (`ratio_espacios`, `densidad_lexica`)
3. El resultado debe ser legible sin comentarios

**Tests que deben pasar:**

```python
config = {"lowercase": True, "strip_special": True, "max_length": 50, "min_palabras": 3}

assert limpiar_resena("  Muy BUENO el producto!!!  ", config)["procesado"] == "muy bueno el producto"
assert limpiar_resena("ok", config)["valido"] == False
assert limpiar_resena("A" * 100, config)["procesado"] == "a" * 50
```

## Parte 2 — DRY: el repositorio repite todo

El repositorio gestiona reseñas, usuarios y productos. Cada recurso tiene su propio bloque de conexión/cursor/try/finally copiado y pegado.

**Código de partida** (`repositorio.py`):

```python
import psycopg2
from fastapi import HTTPException

DATABASE_URL = "postgresql://user:pass@localhost/resenas"

def crear_resena(usuario_id: int, producto_id: int, texto: str, puntuacion: int) -> dict:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO resenas (usuario_id, producto_id, texto, puntuacion) VALUES (%s, %s, %s, %s) RETURNING id",
            (usuario_id, producto_id, texto, puntuacion)
        )
        id_nuevo = cursor.fetchone()[0]
        conn.commit()
        return {"id": id_nuevo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al crear reseña: {e}")
    finally:
        conn.close()

def obtener_resena(id: int) -> dict:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, usuario_id, producto_id, texto, puntuacion FROM resenas WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Reseña {id} no encontrada")
        return {"id": row[0], "usuario_id": row[1], "producto_id": row[2], "texto": row[3], "puntuacion": row[4]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error al obtener reseña: {e}")
    finally:
        conn.close()

def eliminar_resena(id: int) -> bool:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM resenas WHERE id = %s RETURNING id", (id,))
        if not cursor.fetchone():
            raise HTTPException(404, f"Reseña {id} no encontrada")
        conn.commit()
        return True
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al eliminar reseña: {e}")
    finally:
        conn.close()

def crear_usuario(nombre: str, email: str) -> dict:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (nombre, email) VALUES (%s, %s) RETURNING id",
            (nombre, email)
        )
        id_nuevo = cursor.fetchone()[0]
        conn.commit()
        return {"id": id_nuevo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al crear usuario: {e}")
    finally:
        conn.close()

def obtener_usuario(id: int) -> dict:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nombre, email FROM usuarios WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, f"Usuario {id} no encontrado")
        return {"id": row[0], "nombre": row[1], "email": row[2]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error al obtener usuario: {e}")
    finally:
        conn.close()

def crear_producto(nombre: str, categoria: str) -> dict:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO productos (nombre, categoria) VALUES (%s, %s) RETURNING id",
            (nombre, categoria)
        )
        id_nuevo = cursor.fetchone()[0]
        conn.commit()
        return {"id": id_nuevo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al crear producto: {e}")
    finally:
        conn.close()
```

**Tu tarea:**

1. Identifica los 3 patrones duplicados
2. Extrae un context manager para la conexión
3. Extrae una función auxiliar para el patrón "buscar por id o lanzar 404"
4. Reescribe todas las funciones usando tus abstracciones — añadir un nuevo recurso debe requerir solo escribir la SQL

## Parte 3 — SRP: el analizador hace demasiado

`AnalizadorResenas` valida el texto, llama al LLM, guarda en base de datos, envía un email de alerta y registra en el log — todo en un mismo método.

**Código de partida** (`analizador.py`):

```python
import psycopg2, smtplib, json, logging
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

class AnalizadorResenas:
    DATABASE_URL = "postgresql://user:pass@localhost/resenas"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_FROM = "sistema@tienda.com"
    EMAIL_ADMIN = "admin@tienda.com"

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def analizar(self, resena_id: int, texto: str) -> dict:
        # 1. Validar longitud
        if len(texto.strip()) < 10:
            raise ValueError("La reseña es demasiado corta")

        # 2. Llamar al LLM
        respuesta = self.llm.invoke([HumanMessage(content=f"""
        Analiza esta reseña de producto y devuelve un JSON con:
        - sentimiento: positivo/negativo/neutro
        - aspectos: lista de aspectos mencionados (precio, calidad, envío, etc.)
        - resumen: una frase

        Reseña: {texto}
        """)])
        try:
            analisis = json.loads(respuesta.content)
        except json.JSONDecodeError:
            analisis = {"sentimiento": "neutro", "aspectos": [], "resumen": texto[:50]}

        # 3. Guardar en BD
        conn = psycopg2.connect(self.DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analisis (resena_id, sentimiento, aspectos, resumen, fecha) VALUES (%s, %s, %s, %s, %s)",
            (resena_id, analisis["sentimiento"], json.dumps(analisis["aspectos"]), analisis["resumen"], datetime.now())
        )
        conn.commit()
        conn.close()

        # 4. Alertar si es negativo
        if analisis["sentimiento"] == "negativo":
            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(self.EMAIL_FROM, "password123")
                smtp.sendmail(self.EMAIL_FROM, self.EMAIL_ADMIN,
                              f"Reseña negativa #{resena_id}:\n{texto[:200]}")

        # 5. Log
        logging.info(json.dumps({
            "evento": "resena_analizada",
            "resena_id": resena_id,
            "sentimiento": analisis["sentimiento"],
            "timestamp": datetime.now().isoformat()
        }))

        return {**analisis, "resena_id": resena_id}
```

**Tu tarea:**

1. Identifica las 5 responsabilidades de `AnalizadorResenas`
2. Crea una clase por responsabilidad:
   - `ValidadorTexto`
   - `ClienteLLM`
   - `RepositorioAnalisis`
   - `ServicioAlertas`
   - `AuditorEventos`
3. Refactoriza `AnalizadorResenas` para que solo orqueste:

```python
class AnalizadorResenas:
    def __init__(self, validador, llm, repo, alertas, auditor):
        ...

    def analizar(self, resena_id: int, texto: str) -> dict:
        # máximo 10 líneas — solo orquesta
        ...
```

## Parte 4 — OCP: los reportes no son extensibles

Cada vez que el cliente pide un nuevo formato de reporte hay que tocar la función principal y arriesgarse a romper los formatos que ya funcionan.

**Código de partida** (`reportes.py`):

```python
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
```

**Tu tarea:**

1. Crea una clase base abstracta `GeneradorReporte` con un método `generar(resenas) -> str`
2. Implementa `ReporteCSV`, `ReporteJSON`, `ReporteTXT`
3. **Sin tocar nada de lo anterior**, añade `ReporteMarkdown` con esta salida:

```markdown
# Reporte de reseñas — 2026-05-12

| Producto | Puntuación | Sentimiento |
|----------|------------|-------------|
| Teclado Pro | 5/5 | positivo |
| Ratón Basic | 2/5 | negativo |

**Media: 3.50/5 · Total: 2 reseñas**
```

4. Crea un dict `FORMATOS = {"csv": ReporteCSV, ...}` y úsalo en el endpoint FastAPI

## Parte 5 — LSP: la jerarquía de almacenamiento tiene bugs

Los adjuntos de las reseñas (imágenes, PDFs) se guardan en distintos backends. La jerarquía actual tiene dos bugs que hacen que el código que "debería funcionar con cualquier almacenamiento" explote en tiempo de ejecución.

**Código de partida** (`almacenamiento.py`):

```python
from abc import ABC, abstractmethod
from pathlib import Path

class Almacenamiento(ABC):
    @abstractmethod
    def guardar(self, nombre: str, contenido: bytes) -> str: ...
    @abstractmethod
    def obtener(self, nombre: str) -> bytes: ...  # lanza FileNotFoundError si no existe
    @abstractmethod
    def eliminar(self, nombre: str) -> bool: ...  # True si eliminó, False si no existía
    @abstractmethod
    def listar(self) -> list[str]: ...

class AlmacenamientoLocal(Almacenamiento):
    def __init__(self, directorio: str):
        self.directorio = Path(directorio)
        self.directorio.mkdir(exist_ok=True)

    def guardar(self, nombre: str, contenido: bytes) -> str:
        ruta = self.directorio / nombre
        ruta.write_bytes(contenido)
        return str(ruta)

    def obtener(self, nombre: str) -> bytes:
        ruta = self.directorio / nombre
        if not ruta.exists():
            raise FileNotFoundError(f"{nombre} no encontrado")
        return ruta.read_bytes()

    def eliminar(self, nombre: str) -> bool:
        ruta = self.directorio / nombre
        if ruta.exists():
            ruta.unlink()
            return True
        return False

    def listar(self) -> list[str]:
        return [f.name for f in self.directorio.iterdir() if f.is_file()]


class AlmacenamientoSoloLectura(Almacenamiento):
    """Para recursos estáticos del sistema (logos, plantillas)."""
    def __init__(self, directorio: str):
        self.directorio = Path(directorio)

    def guardar(self, nombre: str, contenido: bytes) -> str:
        raise PermissionError("Solo lectura")          # ← VIOLA LSP

    def obtener(self, nombre: str) -> bytes:
        ruta = self.directorio / nombre
        if not ruta.exists():
            raise FileNotFoundError(f"{nombre} no encontrado")
        return ruta.read_bytes()

    def eliminar(self, nombre: str) -> bool:
        raise PermissionError("Solo lectura")           # ← VIOLA LSP

    def listar(self) -> list[str]:
        return [f.name for f in self.directorio.iterdir() if f.is_file()]


class AlmacenamientoConCache(Almacenamiento):
    def __init__(self, base: Almacenamiento):
        self.base = base
        self.cache = {}

    def guardar(self, nombre: str, contenido: bytes) -> str:
        self.cache[nombre] = contenido
        return self.base.guardar(nombre, contenido)

    def obtener(self, nombre: str) -> bytes | None:     # ← VIOLA LSP: tipo de retorno distinto
        if nombre in self.cache:
            return self.cache[nombre]
        try:
            datos = self.base.obtener(nombre)
            self.cache[nombre] = datos
            return datos
        except FileNotFoundError:
            return None                                  # ← debería relanzar el error

    def eliminar(self, nombre: str) -> bool:
        self.cache.pop(nombre, None)
        return self.base.eliminar(nombre)

    def listar(self) -> list[str]:
        return self.base.listar()


# Esta función debe funcionar con CUALQUIER Almacenamiento sin checks especiales
def procesar_adjuntos(storage: Almacenamiento, nombres: list[str]) -> dict:
    resultados = {}
    for nombre in nombres:
        try:
            contenido = storage.obtener(nombre)
            if contenido is None:                        # ← no debería ser necesario
                resultados[nombre] = "no_encontrado"
            else:
                resultados[nombre] = f"{len(contenido)}_bytes"
        except PermissionError:                          # ← no debería ser necesario
            resultados[nombre] = "sin_permiso"
        except FileNotFoundError:
            resultados[nombre] = "no_encontrado"
    return resultados
```

**Tu tarea:**

1. Señala exactamente qué líneas violan LSP y explica por qué
2. Rediseña la jerarquía separando `AlmacenamientoLectura` de `AlmacenamientoEscritura`
3. `AlmacenamientoConCache.obtener` debe lanzar `FileNotFoundError`, nunca devolver `None`
4. `procesar_adjuntos` no debe necesitar ni el check de `None` ni el catch de `PermissionError`

**Test que debe pasar para cualquier `AlmacenamientoEscritura`:**

```python
def test_contrato_almacenamiento(storage):
    storage.guardar("test.bin", b"datos")
    assert storage.obtener("test.bin") == b"datos"
    try:
        storage.obtener("no_existe.bin")
        assert False, "Debe lanzar FileNotFoundError"
    except FileNotFoundError:
        pass
    assert storage.eliminar("test.bin") == True
    assert storage.eliminar("no_existe.bin") == False
```

## Parte 6 — ISP: la interfaz del repositorio es demasiado grande

El repositorio de reseñas tiene una interfaz única que obliga a implementar métodos que no tienen sentido para algunos casos de uso.

**Código de partida** (añade esto a `repositorio.py`):

```python
from abc import ABC, abstractmethod

class RepositorioResenas(ABC):
    @abstractmethod
    def crear(self, datos: dict) -> dict: ...
    @abstractmethod
    def obtener_por_id(self, id: int) -> dict | None: ...
    @abstractmethod
    def listar_todos(self) -> list[dict]: ...
    @abstractmethod
    def actualizar(self, id: int, datos: dict) -> dict | None: ...
    @abstractmethod
    def eliminar(self, id: int) -> bool: ...
    @abstractmethod
    def buscar(self, filtros: dict) -> list[dict]: ...
    @abstractmethod
    def paginar(self, pagina: int, por_pagina: int) -> dict: ...
    @abstractmethod
    def exportar_csv(self) -> str: ...
    @abstractmethod
    def importar_csv(self, contenido: str) -> int: ...
    @abstractmethod
    def archivar(self, id: int) -> bool: ...
    @abstractmethod
    def obtener_historial(self, id: int) -> list[dict]: ...


class RepositorioResenasSoloLectura(RepositorioResenas):
    """Repositorio de consulta para el panel público — no puede crear ni eliminar."""
    def crear(self, datos): raise NotImplementedError        # ← forzado
    def actualizar(self, id, datos): raise NotImplementedError
    def eliminar(self, id): raise NotImplementedError
    def importar_csv(self, contenido): raise NotImplementedError
    def archivar(self, id): raise NotImplementedError
    def obtener_historial(self, id): raise NotImplementedError
    # Solo implementa realmente:
    def obtener_por_id(self, id): ...
    def listar_todos(self): ...
    def buscar(self, filtros): ...
    def paginar(self, pagina, por_pagina): ...
    def exportar_csv(self): ...
```

**Tu tarea:**

1. Divide `RepositorioResenas` en interfaces pequeñas usando `Protocol`:
   - `Readable` (obtener, listar, buscar, paginar)
   - `Writable` (crear, actualizar, eliminar)
   - `Exportable` (exportar_csv)
   - `Importable` (importar_csv)
   - `Archivable` (archivar)
   - `Auditable` (obtener_historial)

2. `RepositorioResenasSoloLectura` implementa solo `Readable` y `Exportable` — sin ningún `NotImplementedError`

3. Los servicios dependen solo de lo que necesitan:

```python
class ServicioExportacion:
    def __init__(self, repo: Exportable): ...  # no necesita saber crear

class ServicioAuditoria:
    def __init__(self, repo: Auditable): ...   # no necesita saber paginar
```

## Parte 7 — DIP: las dependencias están hardcodeadas

`AnalizadorResenas` (que ya refactorizaste en la Parte 3) sigue dependiendo de implementaciones concretas. Eso hace imposible testarlo sin una API key de OpenAI y un servidor SMTP.

**Tu tarea:**

1. Define interfaces abstractas para las dependencias del analizador:

```python
from abc import ABC, abstractmethod

class ClienteLLM(ABC):
    @abstractmethod
    def analizar_texto(self, texto: str) -> dict: ...

class RepositorioAnalisis(ABC):
    @abstractmethod
    def guardar(self, resena_id: int, analisis: dict) -> None: ...

class ServicioAlertas(ABC):
    @abstractmethod
    def enviar_alerta(self, mensaje: str) -> None: ...
```

2. Implementa las versiones de producción (`ClienteOpenAI`, `RepositorioAnalisisPostgres`, `AlertaEmail`) y las versiones para tests (`ClienteMock`, `RepositorioMemoria`, `AlertaConsola`)

3. Refactoriza `AnalizadorResenas.__init__` para recibir las dependencias inyectadas

4. Escribe estos 3 tests (deben pasar **sin API key**):

```python
def test_resena_positiva_no_genera_alerta():
    alertas = AlertaConsola()
    alertas_enviadas = []
    alertas.enviar_alerta = lambda msg: alertas_enviadas.append(msg)

    analizador = AnalizadorResenas(
        validador=ValidadorTexto(),
        llm=ClienteMock({"sentimiento": "positivo", "aspectos": ["calidad"], "resumen": "Muy bueno"}),
        repo=RepositorioMemoria(),
        alertas=alertas,
        auditor=AuditorConsola(),
    )
    analizador.analizar(1, "El producto es excelente, muy recomendable")
    assert len(alertas_enviadas) == 0

def test_resena_negativa_genera_alerta():
    ...

def test_resena_demasiado_corta_lanza_error():
    ...
```

## Entrega

Un único repositorio/carpeta con:

```bash
lab-web-complete-refactoring/
├── procesador.py      # Parte 1
├── repositorio.py     # Partes 2 y 6
├── analizador.py      # Partes 3 y 7
├── reportes.py        # Parte 4
├── almacenamiento.py  # Parte 5
├── main.py            # FastAPI con los endpoints
└── tests.py           # Los tests de las partes 1, 5 y 7
```

## Checklist de entrega

**KISS**
- [ ] `limpiar_resena` no usa `reduce` ni lambdas encadenadas
- [ ] Los 3 tests de la Parte 1 pasan

**DRY**
- [ ] No hay bloques `try/except/finally` con `conn.close()` repetidos
- [ ] Añadir un nuevo recurso (ej. categorías) requiere solo escribir la SQL

**SRP**
- [ ] `AnalizadorResenas.analizar` tiene menos de 10 líneas
- [ ] Cambiar el proveedor de email no requiere tocar `AnalizadorResenas`

**OCP**
- [ ] `ReporteMarkdown` se creó sin modificar las clases existentes
- [ ] El endpoint de reportes usa el dict `FORMATOS`

**LSP**
- [ ] `AlmacenamientoConCache.obtener` nunca devuelve `None`
- [ ] `procesar_adjuntos` no tiene checks por tipo concreto de storage
- [ ] `test_contrato_almacenamiento` pasa para `AlmacenamientoLocal` y `AlmacenamientoConCache`

**ISP**
- [ ] Ninguna clase implementa `raise NotImplementedError`
- [ ] `RepositorioResenasSoloLectura` solo implementa `Readable` y `Exportable`

**DIP**
- [ ] Los 3 tests de la Parte 7 pasan sin API key de OpenAI ni servidor SMTP
- [ ] Cambiar de OpenAI a Claude requiere solo crear `ClienteClaude` y pasarlo al constructor

## Bonus

- Implementa `main.py` con endpoints para las operaciones principales
- Añade `AlmacenamientoS3` como implementación de `AlmacenamientoEscritura`
- Crea `factory.py` con `crear_analizador_produccion()` y `crear_analizador_test()` 
- Añade un endpoint `GET /reportes` que acepte `?formato=csv|json|txt|md`
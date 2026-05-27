import os
from contextlib import contextmanager
from typing import Protocol

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/resenas")


@contextmanager
def conexion_db():
    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        yield cursor
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def fila_o_404(cursor, sql: str, params: tuple, mensaje: str):
    cursor.execute(sql, params)
    fila = cursor.fetchone()

    if fila is None:
        raise HTTPException(status_code=404, detail=mensaje)

    return fila


def crear_resena(usuario_id: int, producto_id: int, texto: str, puntuacion: int) -> dict:
    with conexion_db() as cursor:
        cursor.execute(
            """
            INSERT INTO resenas (usuario_id, producto_id, texto, puntuacion)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (usuario_id, producto_id, texto, puntuacion),
        )

        return {"id": cursor.fetchone()[0]}


def obtener_resena(id: int) -> dict:
    with conexion_db() as cursor:
        fila = fila_o_404(
            cursor,
            """
            SELECT id, usuario_id, producto_id, texto, puntuacion
            FROM resenas
            WHERE id = %s
            """,
            (id,),
            f"Reseña {id} no encontrada",
        )

        return {
            "id": fila[0],
            "usuario_id": fila[1],
            "producto_id": fila[2],
            "texto": fila[3],
            "puntuacion": fila[4],
        }


def eliminar_resena(id: int) -> bool:
    with conexion_db() as cursor:
        fila_o_404(
            cursor,
            "DELETE FROM resenas WHERE id = %s RETURNING id",
            (id,),
            f"Reseña {id} no encontrada",
        )

        return True


def crear_usuario(nombre: str, email: str) -> dict:
    with conexion_db() as cursor:
        cursor.execute(
            """
            INSERT INTO usuarios (nombre, email)
            VALUES (%s, %s)
            RETURNING id
            """,
            (nombre, email),
        )

        return {"id": cursor.fetchone()[0]}


def obtener_usuario(id: int) -> dict:
    with conexion_db() as cursor:
        fila = fila_o_404(
            cursor,
            "SELECT id, nombre, email FROM usuarios WHERE id = %s",
            (id,),
            f"Usuario {id} no encontrado",
        )

        return {
            "id": fila[0],
            "nombre": fila[1],
            "email": fila[2],
        }


def crear_producto(nombre: str, categoria: str) -> dict:
    with conexion_db() as cursor:
        cursor.execute(
            """
            INSERT INTO productos (nombre, categoria)
            VALUES (%s, %s)
            RETURNING id
            """,
            (nombre, categoria),
        )

        return {"id": cursor.fetchone()[0]}


class Readable(Protocol):
    def obtener_por_id(self, id: int) -> dict | None:
        ...

    def listar_todos(self) -> list[dict]:
        ...

    def buscar(self, filtros: dict) -> list[dict]:
        ...

    def paginar(self, pagina: int, por_pagina: int) -> dict:
        ...


class Writable(Protocol):
    def crear(self, datos: dict) -> dict:
        ...

    def actualizar(self, id: int, datos: dict) -> dict | None:
        ...

    def eliminar(self, id: int) -> bool:
        ...


class Exportable(Protocol):
    def exportar_csv(self) -> str:
        ...


class Importable(Protocol):
    def importar_csv(self, contenido: str) -> int:
        ...


class Archivable(Protocol):
    def archivar(self, id: int) -> bool:
        ...


class Auditable(Protocol):
    def obtener_historial(self, id: int) -> list[dict]:
        ...


class RepositorioResenasSoloLectura:
    def __init__(self, resenas: list[dict]):
        self.resenas = resenas

    def obtener_por_id(self, id: int) -> dict | None:
        for resena in self.resenas:
            if resena["id"] == id:
                return resena

        return None

    def listar_todos(self) -> list[dict]:
        return self.resenas

    def buscar(self, filtros: dict) -> list[dict]:
        resultado = self.resenas

        for campo, valor in filtros.items():
            resultado = [
                resena for resena in resultado
                if resena.get(campo) == valor
            ]

        return resultado

    def paginar(self, pagina: int, por_pagina: int) -> dict:
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina

        return {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": len(self.resenas),
            "resultados": self.resenas[inicio:fin],
        }

    def exportar_csv(self) -> str:
        lineas = ["id,usuario_id,producto_id,texto,puntuacion"]

        for resena in self.resenas:
            lineas.append(
                f"{resena['id']},{resena['usuario_id']},"
                f"{resena['producto_id']},{resena['texto']},"
                f"{resena['puntuacion']}"
            )

        return "\n".join(lineas)
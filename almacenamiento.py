from abc import ABC, abstractmethod
from pathlib import Path


class AlmacenamientoLectura(ABC):
    @abstractmethod
    def obtener(self, nombre: str) -> bytes:
        ...

    @abstractmethod
    def listar(self) -> list[str]:
        ...


class AlmacenamientoEscritura(AlmacenamientoLectura):
    @abstractmethod
    def guardar(self, nombre: str, contenido: bytes) -> str:
        ...

    @abstractmethod
    def eliminar(self, nombre: str) -> bool:
        ...


class AlmacenamientoLocal(AlmacenamientoEscritura):
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
        return [
            archivo.name
            for archivo in self.directorio.iterdir()
            if archivo.is_file()
        ]


class AlmacenamientoSoloLectura(AlmacenamientoLectura):
    def __init__(self, directorio: str):
        self.directorio = Path(directorio)

    def obtener(self, nombre: str) -> bytes:
        ruta = self.directorio / nombre

        if not ruta.exists():
            raise FileNotFoundError(f"{nombre} no encontrado")

        return ruta.read_bytes()

    def listar(self) -> list[str]:
        return [
            archivo.name
            for archivo in self.directorio.iterdir()
            if archivo.is_file()
        ]


class AlmacenamientoConCache(AlmacenamientoEscritura):
    def __init__(self, base: AlmacenamientoEscritura):
        self.base = base
        self.cache = {}

    def guardar(self, nombre: str, contenido: bytes) -> str:
        self.cache[nombre] = contenido
        return self.base.guardar(nombre, contenido)

    def obtener(self, nombre: str) -> bytes:
        if nombre in self.cache:
            return self.cache[nombre]

        contenido = self.base.obtener(nombre)
        self.cache[nombre] = contenido

        return contenido

    def eliminar(self, nombre: str) -> bool:
        self.cache.pop(nombre, None)
        return self.base.eliminar(nombre)

    def listar(self) -> list[str]:
        return self.base.listar()


def procesar_adjuntos(storage: AlmacenamientoLectura, nombres: list[str]) -> dict:
    resultados = {}

    for nombre in nombres:
        try:
            contenido = storage.obtener(nombre)
            resultados[nombre] = f"{len(contenido)}_bytes"
        except FileNotFoundError:
            resultados[nombre] = "no_encontrado"

    return resultados
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
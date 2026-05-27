import json
import logging
import os
import smtplib
from abc import ABC, abstractmethod
from datetime import datetime

from dotenv import load_dotenv


load_dotenv()


class ValidadorTexto:
    def __init__(self, longitud_minima: int = 10):
        self.longitud_minima = longitud_minima

    def validar(self, texto: str) -> None:
        if len(texto.strip()) < self.longitud_minima:
            raise ValueError("La reseña es demasiado corta")


class ClienteLLM(ABC):
    @abstractmethod
    def analizar_texto(self, texto: str) -> dict:
        ...


class ClienteOpenAI(ClienteLLM):
    def __init__(self, modelo: str = "gpt-4o-mini"):
        self.modelo = modelo

    def analizar_texto(self, texto: str) -> dict:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(model=self.modelo, temperature=0)

        prompt = f"""
        Analiza esta reseña de producto y devuelve un JSON con:
        - sentimiento: positivo/negativo/neutro
        - aspectos: lista de aspectos mencionados
        - resumen: una frase

        Reseña: {texto}
        """

        respuesta = llm.invoke([HumanMessage(content=prompt)])

        try:
            return json.loads(respuesta.content)
        except json.JSONDecodeError:
            return {
                "sentimiento": "neutro",
                "aspectos": [],
                "resumen": texto[:50],
            }


class ClienteMock(ClienteLLM):
    def __init__(self, respuesta: dict):
        self.respuesta = respuesta

    def analizar_texto(self, texto: str) -> dict:
        return self.respuesta.copy()


class RepositorioAnalisis(ABC):
    @abstractmethod
    def guardar(self, resena_id: int, analisis: dict) -> None:
        ...


class RepositorioAnalisisPostgres(RepositorioAnalisis):
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost/resenas"
        )

    def guardar(self, resena_id: int, analisis: dict) -> None:
        import psycopg2

        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO analisis
                (resena_id, sentimiento, aspectos, resumen, fecha)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    resena_id,
                    analisis["sentimiento"],
                    json.dumps(analisis["aspectos"]),
                    analisis["resumen"],
                    datetime.now(),
                ),
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()


class RepositorioMemoria(RepositorioAnalisis):
    def __init__(self):
        self.datos = []

    def guardar(self, resena_id: int, analisis: dict) -> None:
        self.datos.append({
            "resena_id": resena_id,
            "sentimiento": analisis["sentimiento"],
            "aspectos": analisis["aspectos"],
            "resumen": analisis["resumen"],
        })


class ServicioAlertas(ABC):
    @abstractmethod
    def enviar_alerta(self, mensaje: str) -> None:
        ...


class AlertaEmail(ServicioAlertas):
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_from = os.getenv("EMAIL_FROM", "sistema@tienda.com")
        self.email_admin = os.getenv("EMAIL_ADMIN", "admin@tienda.com")
        self.email_password = os.getenv("EMAIL_PASSWORD", "password123")

    def enviar_alerta(self, mensaje: str) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(self.email_from, self.email_password)
            smtp.sendmail(
                self.email_from,
                self.email_admin,
                mensaje,
            )


class AlertaConsola(ServicioAlertas):
    def enviar_alerta(self, mensaje: str) -> None:
        print(mensaje)


class AuditorConsola:
    def registrar(self, evento: str, datos: dict) -> None:
        logging.info(json.dumps({
            "evento": evento,
            **datos,
            "timestamp": datetime.now().isoformat(),
        }, ensure_ascii=False))


class AnalizadorResenas:
    def __init__(self, validador, llm, repo, alertas, auditor):
        self.validador = validador
        self.llm = llm
        self.repo = repo
        self.alertas = alertas
        self.auditor = auditor

    def analizar(self, resena_id: int, texto: str) -> dict:
        self.validador.validar(texto)
        analisis = self.llm.analizar_texto(texto)
        self.repo.guardar(resena_id, analisis)
        if analisis["sentimiento"] == "negativo":
            self.alertas.enviar_alerta(f"Reseña negativa #{resena_id}:\n{texto[:200]}")
        self.auditor.registrar("resena_analizada", {"resena_id": resena_id, "sentimiento": analisis["sentimiento"]})
        return {**analisis, "resena_id": resena_id}
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
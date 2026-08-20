import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any


MAJOR_ARCANA: dict[str, dict[str, str]] = {
    "El Loco": {"meaning": "comienzos, libertad y apertura a lo desconocido"},
    "El Mago": {"meaning": "recursos, iniciativa y capacidad de crear movimiento"},
    "La Sacerdotisa": {"meaning": "intuición, escucha interior y conocimiento reservado"},
    "La Emperatriz": {"meaning": "creatividad, cuidado y crecimiento fértil"},
    "El Emperador": {"meaning": "estructura, límites y responsabilidad"},
    "El Papa": {"meaning": "aprendizaje, valores y orientación"},
    "Los Enamorados": {"meaning": "elección, vínculo y coherencia con los propios valores"},
    "El Carro": {"meaning": "dirección, voluntad y avance decidido"},
    "La Fuerza": {"meaning": "serenidad, coraje y dominio amable de la energía"},
    "El Ermitaño": {"meaning": "pausa, introspección y búsqueda de claridad"},
    "La Rueda de la Fortuna": {"meaning": "cambio, ciclos y nuevas circunstancias"},
    "La Justicia": {"meaning": "equilibrio, consecuencias y decisiones conscientes"},
    "El Colgado": {"meaning": "perspectiva, entrega y pausa necesaria"},
    "La Muerte": {"meaning": "transformación, cierre y renovación"},
    "La Templanza": {"meaning": "integración, paciencia y armonía"},
    "El Diablo": {"meaning": "deseo, ataduras y consciencia de los patrones"},
    "La Torre": {"meaning": "revelación, ruptura y liberación de estructuras"},
    "La Estrella": {"meaning": "esperanza, inspiración y confianza renovada"},
    "La Luna": {"meaning": "sensibilidad, imaginación y zonas de incertidumbre"},
    "El Sol": {"meaning": "claridad, vitalidad y alegría compartida"},
    "El Juicio": {"meaning": "llamada interior, revisión y despertar"},
    "El Mundo": {"meaning": "culminación, integración y amplitud de perspectiva"},
}


def normalize_question(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9\s]", " ", normalized).strip()


def find_related_readings(
    question: str,
    readings: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    normalized_question = normalize_question(question)
    question_words = set(normalized_question.split())
    scored: list[tuple[float, dict[str, Any]]] = []
    for reading in readings:
        previous_question = normalize_question(str(reading.get("question", "")))
        if not previous_question:
            continue
        previous_words = set(previous_question.split())
        sequence_score = SequenceMatcher(
            None,
            normalized_question,
            previous_question,
        ).ratio()
        overlap_score = (
            len(question_words & previous_words) / len(question_words | previous_words)
            if question_words and previous_words
            else 0.0
        )
        score = max(sequence_score, overlap_score)
        if score >= 0.35:
            scored.append((score, reading))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [reading for _, reading in scored[:limit]]


def build_tarot_prompt(
    question: str,
    spread: str,
    cards: list[dict[str, str]],
    style: str,
    profile: dict[str, Any] | None = None,
    related_readings: list[dict[str, Any]] | None = None,
) -> str:
    profile = profile or {}
    profile_lines = [
        f"- Profesión: {profile['profession']}" if profile.get("profession") else "",
        f"- Objetivos: {', '.join(profile['goals'])}" if profile.get("goals") else "",
        f"- Intereses: {', '.join(profile['interests'])}" if profile.get("interests") else "",
    ]
    profile_context = "\n".join(line for line in profile_lines if line) or "- No hay perfil adicional."
    card_context = "\n".join(
        f"- {card['position']}: {card['name']} ({MAJOR_ARCANA[card['name']]['meaning']})"
        for card in cards
    )
    history_context = "- No hay lecturas anteriores relacionadas."
    if related_readings:
        history_context = "\n\n".join(
            "Pregunta anterior: "
            f"{reading.get('question', '')}\n"
            "Cartas anteriores: "
            f"{', '.join(card.get('name', '') for card in reading.get('cards', []))}\n"
            "Interpretación anterior: "
            f"{str(reading.get('reading', ''))[:1200]}"
            for reading in related_readings
        )
    return f"""Eres un asistente de tarot reflexivo. Realiza una lectura simbólica y orientativa, no una predicción objetiva.

Reglas:
- No afirmes que algo va a ocurrir inevitablemente.
- No hagas diagnósticos ni recomendaciones médicas, legales o financieras.
- No presentes las cartas como hechos ni como poderes sobrenaturales verificables.
- Relaciona las cartas entre sí y con la pregunta, no te limites a enumerar significados.
- Usa un tono {style}, cercano y respetuoso.
- Escribe en español.
- Devuelve únicamente la lectura general, en 2 o 3 párrafos breves.
- Integra de forma natural el significado de todas las cartas y sus posiciones.
- No hagas una interpretación separada de cada carta.
- No incluyas títulos, listas, numeración, preguntas adicionales ni próximos pasos.
- No repitas la pregunta ni describas las instrucciones recibidas.
- Si existe historial relacionado, úsalo para mantener coherencia temática.
- No copies literalmente el historial ni lo trates como una verdad objetiva.
- Si la nueva tirada aporta un matiz diferente, intégralo como una evolución o diferencia.

Perfil no sensible del usuario:
{profile_context}

Tipo de tirada: {spread}
Pregunta del usuario: {question}
Cartas:
{card_context}

Historial relacionado del mismo usuario:
{history_context}
"""

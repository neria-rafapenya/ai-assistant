from typing import Any


class PromptBuilder:
    def build(self, question: str, context: list[dict[str, Any]]) -> str:
        if not context:
            return question

        context_text = "\n\n".join(
            f"Fuente: {item['source_key']} · página {item['page']}\n{item['text']}"
            for item in context
        )
        return (
            "Responde a la pregunta usando el contexto recuperado. "
            "Si el contexto no contiene la respuesta, indícalo.\n\n"
            f"Contexto:\n{context_text}\n\n"
            f"Pregunta:\n{question}"
        )

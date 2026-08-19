from pydantic import BaseModel


class SimulatedChatResponse(BaseModel):
    reply: str
    provider: str = "simulated"


class SimulatedChatProvider:
    provider_name = "simulated"

    def generate_reply(self, message: str) -> SimulatedChatResponse:
        text = message.strip()
        if not text:
            return SimulatedChatResponse(reply="Necesito un mensaje para responder.")

        return SimulatedChatResponse(reply=f"[simulado] Recibi: {text}")

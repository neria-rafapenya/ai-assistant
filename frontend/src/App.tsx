import { useMemo, useState } from "react";
import "./App.css";

type HealthResponse = {
  status: string;
};

type ChatResponse = {
  reply: string;
  session_id: string | null;
  provider: string;
};

function App() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [provider, setProvider] = useState("");
  const [health, setHealth] = useState("sin comprobar");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
    [],
  );

  const checkHealth = async () => {
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health check fallo con status ${response.status}`);
      }
      const data: HealthResponse = await response.json();
      setHealth(data.status);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setHealth("error");
      setError(detail);
    }
  };

  const sendMessage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) {
      setError("Escribe un mensaje antes de enviar.");
      return;
    }

    setIsSending(true);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/chat`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          session_id: null,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat fallo con status ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      setReply(data.reply);
      setProvider(data.provider);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setError(detail);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <main className="app-shell">
      <header>
        <h1>AI Assistant</h1>
        <p>Frontend React conectado a FastAPI con fetch.</p>
      </header>

      <section className="panel">
        <h2>Salud del backend</h2>
        <div className="row">
          <button type="button" className="action" onClick={checkHealth}>
            Comprobar /health
          </button>
          <span className="status">Estado: {health}</span>
        </div>
      </section>

      <section className="panel">
        <h2>Chat</h2>
        <form onSubmit={sendMessage} className="chat-form">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Escribe tu mensaje"
            rows={4}
          />
          <button type="submit" className="action" disabled={isSending}>
            {isSending ? "Enviando..." : "Enviar a /api/v1/chat"}
          </button>
        </form>

        <div className="result">
          <p>
            <strong>Proveedor:</strong> {provider || "sin respuesta"}
          </p>
          <p>
            <strong>Reply:</strong> {reply || "sin respuesta"}
          </p>
        </div>

        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}

export default App;

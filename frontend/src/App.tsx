import { useMemo, useState, type ChangeEvent } from "react";
import "./App.css";

type HealthResponse = {
  status: string;
};

type ChatResponse = {
  reply: string;
  session_id: string | null;
  provider: string;
  route: "general" | "rag";
  sources: string[];
};

type DocumentItem = {
  key: string;
  size: number;
  last_modified: string;
};

type DocumentsResponse = {
  documents: DocumentItem[];
};

type UploadUrlResponse = {
  upload_url: string;
  key: string;
  expires_in: number;
};

type ProcessDocumentResponse = {
  status: string;
  source_key: string;
  processed_key: string;
  chunks: number;
};

type SearchResult = {
  id: string;
  source_key: string;
  page: number;
  text: string;
  score: number;
};

type SearchResponse = {
  query: string;
  results: SearchResult[];
};

function App() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [provider, setProvider] = useState("");
  const [chatRoute, setChatRoute] = useState<"general" | "rag" | "">("");
  const [chatSources, setChatSources] = useState<string[]>([]);
  const [health, setHealth] = useState("sin comprobar");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [healthError, setHealthError] = useState("");
  const [chatError, setChatError] = useState("");
  const [documentsError, setDocumentsError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [processingKey, setProcessingKey] = useState("");
  const [processingMessage, setProcessingMessage] = useState("");
  const [processingError, setProcessingError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
    [],
  );

  const formatSize = (size: number) =>
    `${new Intl.NumberFormat("es-ES").format(size)} bytes`;

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat("es-ES", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));

  const checkHealth = async () => {
    setHealthError("");
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
      setHealthError(detail);
    }
  };

  const loadDocuments = async () => {
    setIsLoadingDocuments(true);
    setDocumentsError("");

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/documents`);
      if (!response.ok) {
        throw new Error(`Documents fallo con status ${response.status}`);
      }

      const data: DocumentsResponse = await response.json();
      setDocuments(data.documents);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setDocumentsError(detail);
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  const sendMessage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) {
      setChatError("Escribe un mensaje antes de enviar.");
      return;
    }

    setIsSending(true);
    setChatError("");

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
      setChatRoute(data.route);
      setChatSources(data.sources);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setChatError(detail);
    } finally {
      setIsSending(false);
    }
  };

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setUploadMessage("");
    setUploadError("");

    if (file && file.type !== "application/pdf") {
      setSelectedFile(null);
      setUploadError("Solo se pueden subir archivos PDF.");
      return;
    }

    setSelectedFile(file);
  };

  const uploadDocument = async () => {
    if (!selectedFile) {
      setUploadError("Selecciona un archivo PDF antes de subirlo.");
      return;
    }

    setIsUploading(true);
    setUploadMessage("");
    setUploadError("");

    try {
      const urlResponse = await fetch(
        `${apiBaseUrl}/api/v1/documents/upload-url`,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify({
            filename: selectedFile.name,
            content_type: selectedFile.type,
          }),
        },
      );

      if (!urlResponse.ok) {
        throw new Error(
          `No se pudo crear la URL de subida (${urlResponse.status})`,
        );
      }

      const uploadData: UploadUrlResponse = await urlResponse.json();
      const uploadResponse = await fetch(uploadData.upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": selectedFile.type,
        },
        body: selectedFile,
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 rechazó la subida (${uploadResponse.status})`);
      }

      setUploadMessage(`Archivo subido: ${uploadData.key}`);
      setSelectedFile(null);
      await loadDocuments();
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setUploadError(detail);
    } finally {
      setIsUploading(false);
    }
  };

  const processDocument = async (key: string) => {
    setProcessingKey(key);
    setProcessingMessage("");
    setProcessingError("");

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/documents/process`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ key }),
      });

      if (!response.ok) {
        throw new Error(
          `No se pudo procesar el documento (${response.status})`,
        );
      }

      const data: ProcessDocumentResponse = await response.json();
      setProcessingMessage(
        `${data.source_key} procesado: ${data.chunks} chunk(s) en ${data.processed_key}`,
      );
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setProcessingError(detail);
    } finally {
      setProcessingKey("");
    }
  };

  const searchRag = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      setSearchError("Escribe una consulta.");
      return;
    }

    setIsSearching(true);
    setSearchError("");

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/v1/rag/search?query=${encodeURIComponent(query)}&limit=5`,
      );
      if (!response.ok) {
        throw new Error(`La búsqueda falló (${response.status})`);
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data.results);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Error desconocido";
      setSearchError(detail);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
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
        {healthError ? <p className="error">{healthError}</p> : null}
      </section>

      <section className="panel">
        <h2>Documentos en S3</h2>
        <div className="row">
          <button
            type="button"
            className="action"
            onClick={loadDocuments}
            disabled={isLoadingDocuments}
          >
            {isLoadingDocuments ? "Cargando..." : "Cargar /api/v1/documents"}
          </button>
          <span className="status">Documentos: {documents.length}</span>
        </div>

        <div className="upload-controls">
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={selectFile}
            disabled={isUploading}
          />
          <button
            type="button"
            className="action"
            onClick={uploadDocument}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? "Subiendo..." : "Subir PDF a S3"}
          </button>
          {selectedFile ? <span>{selectedFile.name}</span> : null}
        </div>

        {uploadMessage ? <p className="success">{uploadMessage}</p> : null}
        {uploadError ? <p className="error">{uploadError}</p> : null}

        {documents.length > 0 ? (
          <ul className="documents-list">
            {documents.map((document) => (
              <li key={document.key} className="document-item">
                <p className="document-key">{document.key}</p>
                <p>
                  <strong>Tamano:</strong> {formatSize(document.size)}
                </p>
                <p>
                  <strong>Ultima modificacion:</strong>{" "}
                  {formatDate(document.last_modified)}
                </p>
                <button
                  type="button"
                  className="action"
                  onClick={() => processDocument(document.key)}
                  disabled={processingKey === document.key}
                >
                  {processingKey === document.key
                    ? "Procesando..."
                    : "Procesar PDF"}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">No hay documentos cargados.</p>
        )}

        {documentsError ? <p className="error">{documentsError}</p> : null}
        {processingMessage ? (
          <p className="success">{processingMessage}</p>
        ) : null}
        {processingError ? <p className="error">{processingError}</p> : null}

        <div className="rag-search">
          <h3>Buscar en documentos</h3>
          <form onSubmit={searchRag} className="search-form">
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Ej.: ingresos económicos"
              aria-label="Consulta RAG"
            />
            <button type="submit" className="action" disabled={isSearching}>
              {isSearching ? "Buscando..." : "Buscar"}
            </button>
          </form>

          {searchResults.length > 0 ? (
            <ul className="search-results">
              {searchResults.map((result) => (
                <li key={result.id} className="search-result">
                  <p>
                    <strong>{result.source_key}</strong> · página {result.page}{" "}
                    · score {result.score}
                  </p>
                  <p>{result.text}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No hay resultados para mostrar.</p>
          )}
          {searchError ? <p className="error">{searchError}</p> : null}
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
            <strong>Ruta:</strong> {chatRoute || "sin respuesta"}
          </p>
          <p>
            <strong>Reply:</strong> {reply || "sin respuesta"}
          </p>
          {chatSources.length > 0 ? (
            <p>
              <strong>Fuentes:</strong> {chatSources.join(", ")}
            </p>
          ) : null}
        </div>

        {chatError ? <p className="error">{chatError}</p> : null}
      </section>
    </main>
  );
}

export default App;

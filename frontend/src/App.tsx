import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import { useAuth } from "react-oidc-context";
import { AuthGuard } from "./auth-guard";
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

type UserProfile = {
  date_of_birth: string | null;
  profession: string | null;
  goals: string[];
  interests: string[];
  response_style: string | null;
  topics_to_avoid: string[];
  health_conditions: string | null;
  health_data_consent: boolean;
  age: number | null;
  zodiac_sign: string | null;
  onboarding_completed: boolean;
};

const splitList = (value: string) =>
  value.split(",").map((item) => item.trim()).filter(Boolean);

function ProfilePage() {
  const auth = useAuth();
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState({
    date_of_birth: "",
    profession: "",
    goals: "",
    interests: "",
    response_style: "reflexivo",
    topics_to_avoid: "",
    health_conditions: "",
    health_data_consent: false,
  });

  const headers = () => ({
    "content-type": "application/json",
    Authorization: `Bearer ${auth.user?.access_token ?? ""}`,
  });

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/profile`, {
          headers: { Authorization: `Bearer ${auth.user?.access_token ?? ""}` },
        });
        if (!response.ok) throw new Error(`No se pudo cargar el perfil (${response.status})`);
        const data: UserProfile = await response.json();
        setProfile({
          date_of_birth: data.date_of_birth ?? "",
          profession: data.profession ?? "",
          goals: data.goals.join(", "),
          interests: data.interests.join(", "),
          response_style: data.response_style ?? "reflexivo",
          topics_to_avoid: data.topics_to_avoid.join(", "),
          health_conditions: data.health_conditions ?? "",
          health_data_consent: data.health_data_consent,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar el perfil");
      } finally {
        setIsLoading(false);
      }
    };
    void loadProfile();
  }, [apiBaseUrl, auth.user?.access_token]);

  const saveProfile = async () => {
    setIsSaving(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/profile`, {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify({
          ...profile,
          date_of_birth: profile.date_of_birth || null,
          profession: profile.profession || null,
          goals: splitList(profile.goals),
          interests: splitList(profile.interests),
          topics_to_avoid: splitList(profile.topics_to_avoid),
          health_conditions: profile.health_conditions || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? `No se pudo guardar (${response.status})`);
      setMessage("Perfil guardado correctamente.");
      setStep(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el perfil");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <p className="auth-message">Cargando perfil...</p>;

  return (
    <section className="product-page">
      <p className="eyebrow">Tu perfil</p>
      <h1>Cuéntanos un poco sobre ti</h1>
      <p className="lead">Esta información nos ayudará a personalizar tus experiencias.</p>
      <div className="panel">
        <p>Paso {step} de 3</p>
        {step === 1 ? (
          <>
            <label>Fecha de nacimiento<input type="date" value={profile.date_of_birth} onChange={(event) => setProfile({ ...profile, date_of_birth: event.target.value })} /></label>
            <label>Profesión<input value={profile.profession} onChange={(event) => setProfile({ ...profile, profession: event.target.value })} placeholder="Ej.: diseñadora, profesor, estudiante" /></label>
          </>
        ) : null}
        {step === 2 ? (
          <>
            <label>Objetivos, separados por comas<input value={profile.goals} onChange={(event) => setProfile({ ...profile, goals: event.target.value })} placeholder="crecimiento personal, trabajo" /></label>
            <label>Intereses, separados por comas<input value={profile.interests} onChange={(event) => setProfile({ ...profile, interests: event.target.value })} placeholder="tarot, proyectos, relaciones" /></label>
            <label>Preferencia de respuesta<select value={profile.response_style} onChange={(event) => setProfile({ ...profile, response_style: event.target.value })}><option value="breve">Breve y directa</option><option value="reflexivo">Reflexiva</option><option value="detallado">Detallada</option><option value="practico">Con recomendaciones prácticas</option></select></label>
            <label>Temas que prefieres evitar, separados por comas<input value={profile.topics_to_avoid} onChange={(event) => setProfile({ ...profile, topics_to_avoid: event.target.value })} /></label>
          </>
        ) : null}
        {step === 3 ? (
          <>
            <p>La información de salud es opcional y se tratará por separado. No se utilizará para diagnósticos ni predicciones médicas.</p>
            <label className="checkbox-label"><input type="checkbox" checked={profile.health_data_consent} onChange={(event) => setProfile({ ...profile, health_data_consent: event.target.checked })} /> Acepto explícitamente que esta información se almacene para personalizar la experiencia.</label>
            <label>Información de salud opcional<textarea value={profile.health_conditions} disabled={!profile.health_data_consent} onChange={(event) => setProfile({ ...profile, health_conditions: event.target.value })} placeholder="Puedes dejarlo vacío" /></label>
          </>
        ) : null}
        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="success">{message}</p> : null}
        <div className="row">
          {step > 1 ? <button type="button" className="action" onClick={() => setStep(step - 1)}>Anterior</button> : null}
          {step < 3 ? <button type="button" className="action" onClick={() => setStep(step + 1)}>Continuar</button> : <button type="button" className="action" onClick={() => void saveProfile()} disabled={isSaving}>{isSaving ? "Guardando..." : "Guardar perfil"}</button>}
        </div>
      </div>
    </section>
  );
}

function DevPage() {
  const auth = useAuth();
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [provider, setProvider] = useState("");
  const [chatRoute, setChatRoute] = useState<"general" | "rag" | "">("");
  const [chatSources, setChatSources] = useState<string[]>([]);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
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

  const authHeaders = () => ({
    Authorization: `Bearer ${auth.user?.access_token ?? ""}`,
  });

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
      const response = await fetch(`${apiBaseUrl}/api/v1/documents`, {
        headers: authHeaders(),
      });
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
          ...authHeaders(),
        },
        body: JSON.stringify({
          message: trimmed,
          session_id: chatSessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat fallo con status ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      setChatSessionId(data.session_id);
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
            ...authHeaders(),
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
      await processDocument(uploadData.key);
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
          ...authHeaders(),
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
        { headers: authHeaders() },
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
                    : "Procesar PDF de nuevo"}
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

function HomePage() {
  return (
    <section className="product-page">
      <p className="eyebrow">AI Assistant</p>
      <h1>Un espacio para escucharte</h1>
      <p className="lead">
        Explora una lectura de tarot o encuentra sentido a tus sueños con una
        experiencia personal y reflexiva.
      </p>
      <div className="choice-grid">
        <NavLink className="choice-card" to="/tarot">
          <span className="choice-icon">✦</span>
          <h2>Lectura de tarot</h2>
          <p>Formula una pregunta y recibe una lectura guiada.</p>
        </NavLink>
        <NavLink className="choice-card" to="/suenos">
          <span className="choice-icon">☾</span>
          <h2>Interpretar un sueño</h2>
          <p>Describe lo que has soñado y explora sus posibles significados.</p>
        </NavLink>
      </div>
    </section>
  );
}

function ExperiencePage({ type }: { type: "tarot" | "suenos" }) {
  const isTarot = type === "tarot";
  return (
    <section className="product-page experience-page">
      <p className="eyebrow">{isTarot ? "Tarot" : "Sueños"}</p>
      <h1>{isTarot ? "Tu lectura comienza aquí" : "Cuéntame tu sueño"}</h1>
      <p className="lead">
        {isTarot
          ? "Escribe tu pregunta con calma. La interpretación será una guía para tu reflexión personal."
          : "Describe las imágenes, emociones y detalles que recuerdes. Los matices importan."}
      </p>
      <div className="coming-soon-card">
        <span className="choice-icon">{isTarot ? "✦" : "☾"}</span>
        <h2>Próximamente</h2>
        <p>
          Estamos preparando esta experiencia. Mientras tanto, puedes revisar
          las integraciones actuales desde el área de desarrollo.
        </p>
        <NavLink className="action" to="/dev">
          Abrir herramientas de desarrollo
        </NavLink>
      </div>
    </section>
  );
}

function HistoryPage() {
  return (
    <section className="product-page">
      <p className="eyebrow">Tu espacio</p>
      <h1>Historial</h1>
      <p className="lead">
        Aquí aparecerán tus lecturas e interpretaciones guardadas cuando
        activemos la autenticación.
      </p>
      <div className="coming-soon-card">
        <h2>Disponible próximamente</h2>
        <p>El historial será privado y estará asociado a tu cuenta.</p>
      </div>
    </section>
  );
}

function App() {
  const auth = useAuth();

  return (
    <BrowserRouter>
      <div className="app-layout">
        <aside className="sidebar">
          <NavLink className="brand" to="/">
            <span className="brand-mark">✦</span>
            <span>AI Assistant</span>
          </NavLink>
          <nav className="main-nav" aria-label="Navegación principal">
            <NavLink to="/" end>
              Inicio
            </NavLink>
            <NavLink to="/tarot">Tarot</NavLink>
            <NavLink to="/suenos">Sueños</NavLink>
            <NavLink to="/historial">Historial</NavLink>
            {auth.isAuthenticated ? <NavLink to="/perfil">Mi perfil</NavLink> : null}
          </nav>
          <nav className="secondary-nav" aria-label="Navegación secundaria">
            <NavLink to="/dev">Desarrollo</NavLink>
            {auth.isAuthenticated ? (
              <button
                type="button"
                className="logout-button"
                onClick={() => void auth.signoutRedirect()}
              >
                Cerrar sesión
              </button>
            ) : null}
          </nav>
        </aside>
        <main className="content-area">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route
              path="/tarot"
              element={
                <AuthGuard>
                  <ExperiencePage type="tarot" />
                </AuthGuard>
              }
            />
            <Route
              path="/suenos"
              element={
                <AuthGuard>
                  <ExperiencePage type="suenos" />
                </AuthGuard>
              }
            />
            <Route
              path="/historial"
              element={
                <AuthGuard>
                  <HistoryPage />
                </AuthGuard>
              }
            />
            <Route path="/perfil" element={<AuthGuard><ProfilePage /></AuthGuard>} />
            <Route path="/dev" element={<DevPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

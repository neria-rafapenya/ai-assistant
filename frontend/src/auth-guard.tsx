import type { ReactNode } from "react";
import { useAuth } from "react-oidc-context";

export function LoginPage() {
  const auth = useAuth();

  return (
    <section className="product-page auth-page">
      <p className="eyebrow">AI Assistant</p>
      <h1>Tu espacio personal</h1>
      <p className="lead">
        Inicia sesión para guardar tus lecturas de tarot, interpretaciones de
        sueños y conversaciones.
      </p>
      <button
        type="button"
        className="action"
        onClick={() => void auth.signinRedirect()}
      >
        Iniciar sesión
      </button>
    </section>
  );
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const auth = useAuth();

  if (auth.isLoading) {
    return <p className="auth-message">Comprobando sesión...</p>;
  }

  if (auth.error) {
    return (
      <p className="error auth-message">
        No se pudo iniciar la sesión: {auth.error.message}
      </p>
    );
  }

  return auth.isAuthenticated ? children : <LoginPage />;
}

import type { PropsWithChildren } from "react";
import { AuthProvider } from "react-oidc-context";

const issuer =
  import.meta.env.VITE_COGNITO_ISSUER ??
  "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_5fX8JYeKk";

const oidcConfig = {
  authority: issuer,
  client_id:
    import.meta.env.VITE_COGNITO_CLIENT_ID ?? "4086ign9h6tpj0r5o1mhhhab74n",
  redirect_uri:
    import.meta.env.VITE_COGNITO_REDIRECT_URI ?? window.location.origin + "/",
  post_logout_redirect_uri:
    import.meta.env.VITE_COGNITO_LOGOUT_URI ?? window.location.origin + "/",
  response_type: "code",
  scope: "openid email profile",
};

export function AppAuthProvider({ children }: PropsWithChildren) {
  return <AuthProvider {...oidcConfig}>{children}</AuthProvider>;
}

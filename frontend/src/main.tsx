import React from "react";
import ReactDOM from "react-dom/client";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import App from "./App";

const msalConfig = {
  auth: {
    clientId: "<YOUR_AZURE_AD_APP_CLIENT_ID>",
    authority: "https://login.microsoftonline.com/<TENANT_ID_OR_COMMON>",
    redirectUri: window.location.origin
  },
  cache: {
    cacheLocation: "sessionStorage"
  }
};

const pca = new PublicClientApplication(msalConfig);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <MsalProvider instance={pca}>
      <App />
    </MsalProvider>
  </React.StrictMode>
);
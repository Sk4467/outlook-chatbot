import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: "<YOUR_AZURE_AD_APP_CLIENT_ID>",
    authority: "https://login.microsoftonline.com/<TENANT_ID_OR_COMMON>",
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message) => {
        if (level === LogLevel.Error) console.error(message);
      },
      piiLoggingEnabled: false
    }
  }
};

// Scopes for sign-in and Graph email read
export const loginRequest = {
  scopes: ["User.Read", "Mail.Read"]
};

// Use when acquiring tokens silently/explicitly for Graph calls
export const graphTokenRequest = {
  scopes: ["Mail.Read"]
};

export const GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0";
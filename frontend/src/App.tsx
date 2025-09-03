import React, { useState } from "react";
import { useMsal } from "@azure/msal-react";

const GRAPH = "https://graph.microsoft.com/v1.0";
const SCOPES = ["Mail.Read"];
const BACKEND = "http://localhost:8000";

type GraphEmailAddress = { address?: string; name?: string };
type GraphFrom = { emailAddress?: GraphEmailAddress };
type GraphMessage = {
  id: string;
  subject?: string;
  from?: GraphFrom;
  receivedDateTime?: string;
  hasAttachments?: boolean;
};

type AttachmentItem = {
  file: File;
  name: string;
  type: string;
  size?: number;
  selected: boolean;
};

type IngestResult = { chunks: number; attachments: number };
type SourceItem = {
  subject?: string;
  filename?: string;
  receivedAt?: string;
  source?: string;
  loc?: string;
};

function useToken() {
  const { instance, accounts } = useMsal();
  const [token, setToken] = useState<string | null>(null);

  const login = async () => {
    await instance.loginPopup({ scopes: SCOPES });
    const account = instance.getAllAccounts()[0];
    const resp = await instance.acquireTokenSilent({ scopes: SCOPES, account });
    setToken(resp.accessToken);
  };

  const logout = () => {
    instance.logoutPopup();
  };

  const acquire = async (): Promise<string | null> => {
    if (!token) {
      const account = instance.getAllAccounts()[0];
      if (!account) return null;
      const resp = await instance.acquireTokenSilent({ scopes: SCOPES, account });
      setToken(resp.accessToken);
      return resp.accessToken;
    }
    return token;
  };

  return { token, login, logout, acquire };
}

export default function App() {
  const { accounts } = useMsal();
  const { login, logout, acquire } = useToken();

  const [messages, setMessages] = useState<GraphMessage[]>([]);
  const [selected, setSelected] = useState<GraphMessage | null>(null);
  const [bodyText, setBodyText] = useState<string>("");
  const [attachments, setAttachments] = useState<AttachmentItem[]>([]);
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);

  const [query, setQuery] = useState<string>("");
  const [answer, setAnswer] = useState<string>("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const signedIn = accounts.length > 0;

  const listMessages = async () => {
    try {
      setLoading(true);
      const at = await acquire();
      if (!at) return;
      const url = `${GRAPH}/me/messages?$select=id,subject,from,receivedDateTime,hasAttachments&$orderby=receivedDateTime desc&$top=25`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${at}` } });
      const data = await res.json();
      setMessages((data?.value as GraphMessage[]) || []);
    } catch (e) {
      console.error("listMessages error:", e);
    } finally {
      setLoading(false);
    }
  };

  const selectMessage = async (m: GraphMessage) => {
    try {
      setLoading(true);
      setSelected(m);
      setBodyText("");
      setAttachments([]);

      const at = await acquire();
      if (!at) return;

      // Fetch body (HTML) and minimal fields
      const msgRes = await fetch(
        `${GRAPH}/me/messages/${m.id}?$select=id,subject,from,receivedDateTime,body`,
        { headers: { Authorization: `Bearer ${at}` } }
      );
      const msg = await msgRes.json();

      // HTML -> text
      const html: string = msg?.body?.content || "";
      const doc = new DOMParser().parseFromString(html, "text/html");
      const text = doc.body.textContent || "";
      setBodyText(text);

      // Attachments (small files only: contentBytes present)
      const attRes = await fetch(
        `${GRAPH}/me/messages/${m.id}/attachments?$select=id,name,contentType,size,contentBytes`,
        { headers: { Authorization: `Bearer ${at}` } }
      );
      const attData = await attRes.json();
      const items = (attData.value || [])
        .filter((a: any) => {
          const ct = String(a.contentType || "").toLowerCase();
          return ct.includes("pdf") || ct.includes("spreadsheetml");
        })
        .filter((a: any) => (a.size || 0) <= 3 * 1024 * 1024) // <= ~3MB for contentBytes
        .filter((a: any) => !!a.contentBytes);

      const files: AttachmentItem[] = items.map((a: any) => {
        const bstr = atob(a.contentBytes as string);
        const bytes = new Uint8Array(bstr.length);
        for (let i = 0; i < bstr.length; i++) bytes[i] = bstr.charCodeAt(i);
        const blob = new Blob([bytes], { type: a.contentType || "application/octet-stream" });
        const file = new File([blob], a.name || "attachment", { type: a.contentType || "" });
        return { file, name: a.name, type: a.contentType, size: a.size, selected: true };
      });

      setAttachments(files);
    } catch (e) {
      console.error("selectMessage error:", e);
    } finally {
      setLoading(false);
    }
  };

  const ingest = async () => {
    if (!selected) return;
    try {
      setLoading(true);
      setIngestResult(null);
      const fd = new FormData();
      fd.append("emailSubject", selected.subject || "");
      fd.append("emailFrom", selected?.from?.emailAddress?.address || "");
      fd.append("receivedAt", selected.receivedDateTime || "");
      fd.append("bodyText", bodyText || "");
      attachments
        .filter((a) => a.selected)
        .forEach((a) => fd.append("attachments", a.file, a.name));

      const res = await fetch(`${BACKEND}/ingest`, { method: "POST", body: fd });
      const data = await res.json();
      setIngestResult(data as IngestResult);
    } catch (e) {
      console.error("ingest error:", e);
    } finally {
      setLoading(false);
    }
  };

  const ask = async () => {
    try {
      setLoading(true);
      setAnswer("Thinking...");
      setSources([]);
      const res = await fetch(`${BACKEND}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, k: 6 }),
      });
      const data = await res.json();
      setAnswer((data?.answer as string) || "");
      setSources((data?.sources as SourceItem[]) || []);
    } catch (e) {
      console.error("ask error:", e);
      setAnswer("There was an error generating the answer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "system-ui", padding: 16, display: "grid", gap: 12 }}>
      <h2>Outlook RAG Prototype</h2>

      {!signedIn ? (
        <button onClick={login}>Sign in with Microsoft</button>
      ) : (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={listMessages} disabled={loading}>Load Messages</button>
          <button onClick={logout}>Sign out</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12 }}>
        <div>
          <h3>Messages</h3>
          <ul style={{ listStyle: "none", padding: 0, maxHeight: 400, overflow: "auto" }}>
            {messages.map((m) => (
              <li key={m.id} style={{ marginBottom: 6 }}>
                <button onClick={() => selectMessage(m)} style={{ width: "100%", textAlign: "left" }}>
                  <strong>{m.subject || "(no subject)"}</strong>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    {m?.from?.emailAddress?.address} —{" "}
                    {m.receivedDateTime ? new Date(m.receivedDateTime).toLocaleString() : ""}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3>Selected Email</h3>
          {selected ? (
            <>
              <div style={{ marginBottom: 8 }}>
                <div><strong>Subject:</strong> {selected.subject}</div>
                <div><strong>From:</strong> {selected?.from?.emailAddress?.address}</div>
                <div>
                  <strong>Received:</strong>{" "}
                  {selected.receivedDateTime ? new Date(selected.receivedDateTime).toLocaleString() : ""}
                </div>
              </div>

              <div>
                <strong>Body (text)</strong>
                <textarea
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  style={{ width: "100%", height: 150 }}
                />
              </div>

              <div>
                <strong>Attachments</strong>
                <ul style={{ listStyle: "none", padding: 0 }}>
                  {attachments.map((a, i) => (
                    <li key={i}>
                      <label>
                        <input
                          type="checkbox"
                          checked={a.selected}
                          onChange={(e) => {
                            const next = [...attachments];
                            next[i].selected = e.target.checked;
                            setAttachments(next);
                          }}
                        />{" "}
                        {a.name} ({a.type}, {Math.round((a.size || 0) / 1024)} KB)
                      </label>
                    </li>
                  ))}
                </ul>
              </div>

              <button onClick={ingest} disabled={loading}>Ingest to Vector Store</button>
              {ingestResult && (
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>
                  Chunks: {ingestResult.chunks}, Attachments used: {ingestResult.attachments}
                </div>
              )}
            </>
          ) : (
            <div>Select a message to view.</div>
          )}
        </div>
      </div>

      <div>
        <h3>Chat</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            style={{ flex: 1 }}
          />
          <button onClick={ask} disabled={loading || !query.trim()}>Ask</button>
        </div>
        {answer && (
          <div style={{ marginTop: 8 }}>
            <strong>Answer</strong>
            <div style={{ whiteSpace: "pre-wrap" }}>{answer}</div>
            <strong>Sources</strong>
            <ul>
              {sources.map((s, i) => (
                <li key={i}>
                  {s.subject} — {s.filename || s.source} {s.loc || ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
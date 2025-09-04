import React, { useEffect, useState } from "react";

const BACKEND = "http://localhost:8000";

type GmailUser = { slot: number; email?: string | null; configured: boolean };
type GmailMessage = {
  id: string;
  from: string;
  subject: string;
  date: string;
  body_text: string;
  combined_text: string;
  attachments: Array<{ filename?: string; content_type?: string; size?: number }>;
};

type GmailAttachment = {
  index: number;
  filename?: string;
  content_type?: string;
  size?: number;
  download_url: string; // relative to backend
};

function toBase64Unicode(str: string): string {
  try {
    // Handle Unicode safely for Base64
    return btoa(unescape(encodeURIComponent(str)));
  } catch {
    return "[encode error]";
  }
}

export default function App() {
  const [users, setUsers] = useState<GmailUser[]>([]);
  const [messagesByUser, setMessagesByUser] = useState<Record<number, GmailMessage[]>>({});
  const [selected, setSelected] = useState<Record<number, GmailMessage | null>>({ 1: null, 2: null });
  const [showEncrypted, setShowEncrypted] = useState<Record<number, boolean>>({ 1: false, 2: false });
  const [fetchCount, setFetchCount] = useState<number>(10);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachmentsByUser, setAttachmentsByUser] = useState<Record<number, GmailAttachment[]>>({});
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);

  // Simple RAG ask state
  const [question, setQuestion] = useState("");
  const [ragAnswer, setRagAnswer] = useState<string>("");
  const [ragRoute, setRagRoute] = useState<string>("");
  const [ragSources, setRagSources] = useState<any[]>([]);

  const loadUsers = async () => {
    setError(null);
    try {
      const res = await fetch(`${BACKEND}/gmail/users`);
      const data = await res.json();
      setUsers(data.users || []);
    } catch (e: any) {
      setError("Failed to load users");
      console.error(e);
    }
  };

  const updateEmails = async (n = 10) => {
    setLoading(true);
    setError(null);
    try {
      const next: Record<number, GmailMessage[]> = { ...messagesByUser };
      const nextSelected: Record<number, GmailMessage | null> = { ...selected };
      for (const u of users) {
        if (!u.configured) {
          next[u.slot] = [];
          nextSelected[u.slot] = null;
          // clear attachments panel as well
          setAttachmentsByUser((prev) => ({ ...prev, [u.slot]: [] }));
          continue;
        }
        const res = await fetch(`${BACKEND}/gmail/messages?user=${u.slot}&n=${n}`);
        const data = await res.json();
        if (data.error) {
          console.warn(`User ${u.slot}:`, data.error);
          next[u.slot] = [];
          nextSelected[u.slot] = null;
        } else {
          next[u.slot] = (data.value || []) as GmailMessage[];
          nextSelected[u.slot] = (data.value || [])[0] || null;
          // reset attachments for this user until explicitly loaded
          setAttachmentsByUser((prev) => ({ ...prev, [u.slot]: [] }));
        }
      }
      setMessagesByUser(next);
      setSelected(nextSelected);
    } catch (e: any) {
      setError("Failed to fetch messages");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const loadAttachments = async (slot: number) => {
    const msg = selected[slot];
    if (!msg) return;
    setError(null);
    try {
      const res = await fetch(`${BACKEND}/gmail/message/${encodeURIComponent(msg.id)}/attachments?user=${slot}`);
      const data = await res.json();
      setAttachmentsByUser((prev) => ({ ...prev, [slot]: (data.value || []) as GmailAttachment[] }));
    } catch (e) {
      console.error(e);
      setError("Failed to load attachments");
    }
  };

  const ingestAttachment = async (slot: number, att: GmailAttachment) => {
    const msg = selected[slot];
    if (!msg) return;
    setIngestStatus("Ingesting...");
    try {
      const payload = {
        messageId: msg.id,
        attachmentId: String(att.index),
        filename: att.filename || `attachment-${att.index}`,
        contentType: att.content_type || "application/octet-stream",
        blob_uri: `${BACKEND}${att.download_url}`,
      };
      const res = await fetch(`${BACKEND}/rag/ingest/attachment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.error) {
        setIngestStatus(`Error: ${data.error}`);
      } else {
        setIngestStatus(`Ingested (${data.kind || 'ok'}): ${data.chunks || 0} chunks`);
      }
    } catch (e: any) {
      console.error(e);
      setIngestStatus("Ingest failed");
    } finally {
      setTimeout(() => setIngestStatus(null), 3000);
    }
  };

  const ingestMailBody = async (slot: number) => {
    const msg = selected[slot];
    if (!msg) return;
    setIngestStatus("Ingesting mail body...");
    try {
      const payload = {
        messageId: msg.id,
        subject: msg.subject || "",
        sender: msg.from || "",
        receivedAt: msg.date || "",
        bodyText: msg.body_text || "",
      };
      const res = await fetch(`${BACKEND}/rag/ingest/mail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.error) {
        setIngestStatus(`Error: ${data.error}`);
      } else {
        setIngestStatus(`Mail body ingested: ${data.chunks || 0} chunks`);
      }
    } catch (e) {
      console.error(e);
      setIngestStatus("Mail body ingest failed");
    } finally {
      setTimeout(() => setIngestStatus(null), 3000);
    }
  };

  const askRag = async () => {
    if (!question.trim()) return;
    setRagAnswer("Thinking...");
    setRagSources([]);
    setRagRoute("");
    try {
      const res = await fetch(`${BACKEND}/rag/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, k: 6 }),
      });
      const data = await res.json();
      setRagAnswer(data.answer || "");
      setRagRoute(data.route || "");
      setRagSources(data.sources || []);
    } catch (e) {
      console.error(e);
      setRagAnswer("Ask failed");
    }
  };

  return (
    <div style={{ fontFamily: "system-ui", padding: 16, display: "grid", gap: 12 }}>
      <h2>Gmail IMAP Viewer</h2>

      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        <button onClick={loadUsers} disabled={loading}>Load Users</button>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label htmlFor="fetchCount"><strong>Fetch last:</strong></label>
          <input
            id="fetchCount"
            type="range"
            min={1}
            max={50}
            value={fetchCount}
            onChange={(e) => setFetchCount(parseInt(e.target.value))}
          />
          <span style={{ width: 24, textAlign: "right" }}>{fetchCount}</span>
          <span>messages</span>
        </div>

        <button onClick={() => updateEmails(fetchCount)} disabled={loading || users.length === 0}>
          Update Emails
        </button>
      </div>

      {error && <div style={{ color: "red" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {users.map((u) => (
          <div key={u.slot} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
            <div style={{ marginBottom: 8 }}>
              <strong>User {u.slot}:</strong> {u.email || "(not configured)"}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 12 }}>
              <div>
                <h4 style={{ margin: 0 }}>Messages</h4>
                <ul style={{ listStyle: "none", padding: 0, maxHeight: 300, overflow: "auto" }}>
                  {(messagesByUser[u.slot] || []).map((m) => (
                    <li key={m.id} style={{ marginBottom: 6 }}>
                      <button
                        style={{ width: "100%", textAlign: "left" }}
                        onClick={() => setSelected((prev) => ({ ...prev, [u.slot]: m }))}
                      >
                        <strong>{m.subject || "(no subject)"} </strong>
                        <div style={{ fontSize: 12, opacity: 0.7 }}>{m.from} — {m.date}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <h4 style={{ margin: 0, flex: 1 }}>Preview</h4>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => setShowEncrypted((prev) => ({ ...prev, [u.slot]: false }))}
                      disabled={!showEncrypted[u.slot]}
                    >
                      Show Normal
                    </button>
                    <button
                      onClick={() => setShowEncrypted((prev) => ({ ...prev, [u.slot]: true }))}
                      disabled={showEncrypted[u.slot]}
                    >
                      Show Encrypted
                    </button>
                  </div>
                </div>

                {selected[u.slot] ? (
                  <div
                    style={{
                      whiteSpace: "pre-wrap",
                      overflowWrap: "anywhere",
                      wordBreak: "break-word",
                      maxHeight: 300,
                      overflow: "auto",
                      border: "1px solid #eee",
                      padding: 8
                    }}
                  >
                    {showEncrypted[u.slot]
                      ? toBase64Unicode(selected[u.slot]?.combined_text || "")
                      : (selected[u.slot]?.combined_text || "")
                    }
                  </div>
                ) : (
                  <div style={{ color: "#666" }}>Select a message to preview.</div>
                )}

                <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
                  <button onClick={() => loadAttachments(u.slot)} disabled={!selected[u.slot] || loading}>Load Attachments</button>
                  <button onClick={() => ingestMailBody(u.slot)} disabled={!selected[u.slot] || loading}>Ingest Mail Body</button>
                  {ingestStatus && <span style={{ fontSize: 12, opacity: 0.8 }}>{ingestStatus}</span>}
                </div>
                {(attachmentsByUser[u.slot] || []).length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <strong>Attachments</strong>
                    <ul style={{ listStyle: "none", padding: 0 }}>
                      {(attachmentsByUser[u.slot] || []).map((a) => (
                        <li key={a.index} style={{ marginBottom: 6, display: "flex", justifyContent: "space-between", gap: 8 }}>
                          <div>
                            {a.filename || `attachment-${a.index}`} ({a.content_type || "?"}, {Math.round((a.size || 0)/1024)} KB)
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <a href={`${BACKEND}${a.download_url}`} target="_blank" rel="noreferrer">Download</a>
                            <button onClick={() => ingestAttachment(u.slot, a)}>Ingest</button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <h3>Ask RAG</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question..." style={{ flex: 1 }} />
          <button onClick={askRag} disabled={!question.trim()}>Ask</button>
        </div>
        {ragAnswer && (
          <div style={{ marginTop: 8 }}>
            <div style={{ marginBottom: 4 }}><strong>Route:</strong> {ragRoute || ""}</div>
            <strong>Answer</strong>
            <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", wordBreak: "break-word" }}>{ragAnswer}</div>
            {ragSources?.length > 0 && (
              <>
                <strong>Sources</strong>
                <ul>
                  {ragSources.map((s, i) => (
                    <li key={i}>{s.subject || s.filename} {s.page ? `(page ${s.page})` : s.sheet ? `(sheet ${s.sheet})` : ""}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

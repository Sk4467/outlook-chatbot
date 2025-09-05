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

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      askRag();
    }
  };

  return (
    <div className="app">
      <style jsx>{`
        .app {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
          min-height: 100vh;
          background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
          padding: 2rem;
          box-sizing: border-box;
        }

        .header {
          max-width: 1400px;
          margin: 0 auto 2rem;
          text-align: center;
        }

        .header h1 {
          margin: 0 0 0.5rem;
          font-size: 2.5rem;
          font-weight: 700;
          color: #1e293b;
          background: linear-gradient(135deg, #3b82f6, #8b5cf6);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .header p {
          margin: 0;
          color: #64748b;
          font-size: 1.1rem;
        }

        .controls {
          max-width: 1400px;
          margin: 0 auto 2rem;
          display: flex;
          gap: 1rem;
          align-items: center;
          flex-wrap: wrap;
          justify-content: center;
          padding: 1.5rem;
          background: white;
          border-radius: 1rem;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .btn {
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 0.5rem;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.9rem;
        }

        .btn-primary {
          background: #3b82f6;
          color: white;
        }

        .btn-secondary {
          background: #f1f5f9;
          color: #475569;
          border: 1px solid #e2e8f0;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .fetch-control {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: #f8fafc;
          padding: 0.75rem 1rem;
          border-radius: 0.5rem;
          border: 1px solid #e2e8f0;
        }

        .fetch-control label {
          font-weight: 600;
          color: #374151;
          font-size: 0.9rem;
        }

        .fetch-control input[type="range"] {
          width: 100px;
        }

        .fetch-control span {
          font-weight: 600;
          color: #3b82f6;
          min-width: 2rem;
          text-align: center;
        }

        .error {
          max-width: 1400px;
          margin: 0 auto 1rem;
          padding: 1rem;
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 0.5rem;
          color: #dc2626;
          font-weight: 500;
        }

        .users-grid {
          max-width: 1400px;
          margin: 0 auto 2rem;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
          gap: 2rem;
        }

        .user-card {
          background: white;
          border-radius: 1rem;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }

        .user-header {
          padding: 1.5rem 1.5rem 1rem;
          background: linear-gradient(135deg, #f8fafc, #f1f5f9);
          border-bottom: 1px solid #e2e8f0;
        }

        .user-title {
          font-size: 1.1rem;
          font-weight: 700;
          color: #1e293b;
          margin: 0;
        }

        .user-email {
          color: #64748b;
          font-size: 0.9rem;
          margin: 0.25rem 0 0;
        }

        .user-content {
          display: grid;
          grid-template-columns: 1fr 1.5fr;
          gap: 0;
          min-height: 400px;
        }

        .messages-panel {
          padding: 1.5rem;
          border-right: 1px solid #e2e8f0;
          background: #fafbfc;
        }

        .messages-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 0 0 1rem;
        }

        .messages-list {
          list-style: none;
          padding: 0;
          margin: 0;
          max-height: 300px;
          overflow-y: auto;
        }

        .message-item {
          margin-bottom: 0.5rem;
        }

        .message-btn {
          width: 100%;
          text-align: left;
          padding: 0.75rem;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          background: white;
          cursor: pointer;
        }

        .message-subject {
          font-weight: 600;
          color: #1e293b;
          margin-bottom: 0.25rem;
          display: block;
        }

        .message-meta {
          font-size: 0.8rem;
          color: #64748b;
        }

        .preview-panel {
          padding: 1.5rem;
        }

        .preview-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .preview-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin: 0;
        }

        .preview-toggle {
          display: flex;
          gap: 0.5rem;
        }

        .preview-content {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          word-break: break-word;
          max-height: 300px;
          overflow-y: auto;
          padding: 1rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', monospace;
          font-size: 0.9rem;
          line-height: 1.5;
          margin-bottom: 1rem;
        }

        .preview-empty {
          color: #64748b;
          font-style: italic;
          text-align: center;
          padding: 2rem;
        }

        .actions {
          display: flex;
          gap: 0.75rem;
          align-items: center;
          flex-wrap: wrap;
          margin-bottom: 1rem;
        }

        .status {
          font-size: 0.85rem;
          color: #059669;
          font-weight: 500;
        }

        .attachments {
          margin-top: 1rem;
        }

        .attachments-title {
          font-weight: 600;
          color: #374151;
          margin: 0 0 0.75rem;
        }

        .attachments-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .attachment-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          gap: 1rem;
        }

        .attachment-info {
          flex: 1;
          font-size: 0.9rem;
          color: #374151;
        }

        .attachment-actions {
          display: flex;
          gap: 0.5rem;
        }

        .attachment-link {
          color: #3b82f6;
          text-decoration: none;
          font-weight: 500;
          font-size: 0.9rem;
        }

        .rag-section {
          max-width: 1400px;
          margin: 0 auto;
          background: white;
          border-radius: 1rem;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          padding: 2rem;
        }

        .rag-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1e293b;
          margin: 0 0 1.5rem;
          background: linear-gradient(135deg, #059669, #10b981);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .rag-input {
          display: flex;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .rag-input input {
          flex: 1;
          padding: 0.75rem 1rem;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          font-size: 1rem;
        }

        .rag-input input:focus {
          outline: none;
          border-color: #3b82f6;
        }

        .rag-answer {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 0.75rem;
          padding: 1.5rem;
        }

        .rag-route {
          font-size: 0.9rem;
          color: #6366f1;
          font-weight: 600;
          margin-bottom: 1rem;
        }

        .rag-answer-title {
          font-weight: 700;
          color: #1e293b;
          margin: 0 0 1rem;
        }

        .rag-answer-content {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          word-break: break-word;
          color: #374151;
          line-height: 1.6;
          margin-bottom: 1.5rem;
        }

        .rag-sources-title {
          font-weight: 700;
          color: #1e293b;
          margin: 0 0 0.75rem;
        }

        .rag-sources-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .rag-sources-list li {
          padding: 0.5rem;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 0.5rem;
          margin-bottom: 0.5rem;
          color: #374151;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
          .app {
            padding: 1rem;
          }
          
          .users-grid {
            grid-template-columns: 1fr;
          }
          
          .user-content {
            grid-template-columns: 1fr;
          }
          
          .messages-panel {
            border-right: none;
            border-bottom: 1px solid #e2e8f0;
          }
          
          .controls {
            flex-direction: column;
            align-items: stretch;
            gap: 1rem;
          }
          
          .fetch-control {
            justify-content: center;
          }
        }
      `}</style>

      <div className="header">
        <h1>Gmail RAG Assistant</h1>
        <p>Intelligent email analysis and document processing</p>
      </div>

      <div className="controls">
        <button className="btn btn-primary" onClick={loadUsers} disabled={loading}>
          Load Users
        </button>

        <div className="fetch-control">
          <label htmlFor="fetchCount">Fetch last:</label>
          <input
            id="fetchCount"
            type="range"
            min={1}
            max={50}
            value={fetchCount}
            onChange={(e) => setFetchCount(parseInt(e.target.value))}
          />
          <span>{fetchCount}</span>
          <span>messages</span>
        </div>

        <button 
          className="btn btn-primary" 
          onClick={() => updateEmails(fetchCount)} 
          disabled={loading || users.length === 0}
        >
          Update Emails
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="users-grid">
        {users.map((u) => (
          <div key={u.slot} className="user-card">
            <div className="user-header">
              <h3 className="user-title">User {u.slot}</h3>
              <p className="user-email">{u.email || "(not configured)"}</p>
            </div>

            <div className="user-content">
              <div className="messages-panel">
                <h4 className="messages-title">Messages</h4>
                <ul className="messages-list">
                  {(messagesByUser[u.slot] || []).map((m) => (
                    <li key={m.id} className="message-item">
                      <button
                        className="message-btn"
                        onClick={() => setSelected((prev) => ({ ...prev, [u.slot]: m }))}
                      >
                        <span className="message-subject">{m.subject || "(no subject)"}</span>
                        <div className="message-meta">{m.from} — {m.date}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="preview-panel">
                <div className="preview-header">
                  <h4 className="preview-title">Preview</h4>
                  <div className="preview-toggle">
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowEncrypted((prev) => ({ ...prev, [u.slot]: false }))}
                      disabled={!showEncrypted[u.slot]}
                    >
                      Normal
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowEncrypted((prev) => ({ ...prev, [u.slot]: true }))}
                      disabled={showEncrypted[u.slot]}
                    >
                      Encrypted
                    </button>
                  </div>
                </div>

                {selected[u.slot] ? (
                  <div className="preview-content">
                    {showEncrypted[u.slot]
                      ? toBase64Unicode(selected[u.slot]?.combined_text || "")
                      : (selected[u.slot]?.combined_text || "")
                    }
                  </div>
                ) : (
                  <div className="preview-empty">Select a message to preview</div>
                )}

                <div className="actions">
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => loadAttachments(u.slot)} 
                    disabled={!selected[u.slot] || loading}
                  >
                    Load Attachments
                  </button>
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => ingestMailBody(u.slot)} 
                    disabled={!selected[u.slot] || loading}
                  >
                    Ingest Mail Body
                  </button>
                  {ingestStatus && <span className="status">{ingestStatus}</span>}
                </div>

                {(attachmentsByUser[u.slot] || []).length > 0 && (
                  <div className="attachments">
                    <h5 className="attachments-title">Attachments</h5>
                    <ul className="attachments-list">
                      {(attachmentsByUser[u.slot] || []).map((a) => (
                        <li key={a.index} className="attachment-item">
                          <div className="attachment-info">
                            {a.filename || `attachment-${a.index}`} ({a.content_type || "?"}, {Math.round((a.size || 0)/1024)} KB)
                          </div>
                          <div className="attachment-actions">
                            <a href={`${BACKEND}${a.download_url}`} target="_blank" rel="noreferrer" className="attachment-link">
                              Download
                            </a>
                            <button className="btn btn-secondary" onClick={() => ingestAttachment(u.slot, a)}>
                              Ingest
                            </button>
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

      <div className="rag-section">
        <h3 className="rag-title">Ask RAG Assistant</h3>
        <div className="rag-input">
          <input 
            value={question} 
            onChange={(e) => setQuestion(e.target.value)} 
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your emails..." 
          />
          <button className="btn btn-primary" onClick={askRag} disabled={!question.trim()}>
            Ask
          </button>
        </div>
        {ragAnswer && (
          <div className="rag-answer">
            {ragRoute && <div className="rag-route">Route: {ragRoute}</div>}
            <h4 className="rag-answer-title">Answer</h4>
            <div className="rag-answer-content">{ragAnswer}</div>
            {ragSources?.length > 0 && (
              <>
                <h4 className="rag-sources-title">Sources</h4>
                <ul className="rag-sources-list">
                  {ragSources.map((s, i) => (
                    <li key={i}>
                      {s.subject || s.filename} {s.page ? `(page ${s.page})` : s.sheet ? `(sheet ${s.sheet})` : ""}
                    </li>
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

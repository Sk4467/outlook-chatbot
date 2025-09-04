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
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
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
  download_url: string;
};

type ChatMessage = {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: any[];
  route?: string;
};

function toBase64Unicode(str: string): string {
  try {
    return btoa(unescape(encodeURIComponent(str)));
  } catch {
    return "[encode error]";
  }
}

// Simple markdown renderer for chat messages
function renderMarkdown(text: string): JSX.Element {
  const lines = text.split('\n');
  const elements: JSX.Element[] = [];
  let currentList: string[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  let codeBlockLanguage = '';

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} style={{
          margin: '1rem 0',
          paddingLeft: '1.5rem',
          color: '#ffffff'
        }}>
          {currentList.map((item, i) => (
            <li key={i} style={{ marginBottom: '0.5rem' }}>
              {renderInlineMarkdown(item)}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushCodeBlock = () => {
    if (codeBlockContent.length > 0) {
      elements.push(
        <pre key={`code-${elements.length}`} style={{
          background: '#0a0a0a',
          border: '1px solid #333333',
          borderRadius: '0.5rem',
          padding: '1rem',
          margin: '1rem 0',
          overflowX: 'auto',
          fontSize: '0.85rem',
          fontFamily: 'ui-monospace, "Cascadia Code", monospace',
          color: '#ffffff'
        }}>
          <code>{codeBlockContent.join('\n')}</code>
        </pre>
      );
      codeBlockContent = [];
      codeBlockLanguage = '';
    }
  };

  lines.forEach((line, index) => {
    // Handle code blocks
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock();
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
        codeBlockLanguage = line.substring(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      return;
    }

    // Handle lists
    if (line.match(/^\s*[-*+]\s+/)) {
      const listItem = line.replace(/^\s*[-*+]\s+/, '');
      currentList.push(listItem);
      return;
    }

    if (line.match(/^\s*\d+\.\s+/)) {
      flushList();
      const listItem = line.replace(/^\s*\d+\.\s+/, '');
      elements.push(
        <ol key={`ol-${elements.length}`} style={{
          margin: '1rem 0',
          paddingLeft: '1.5rem',
          color: '#ffffff'
        }} start={parseInt(line.match(/^\s*(\d+)\./)?.[1] || '1')}>
          <li style={{ marginBottom: '0.5rem' }}>
            {renderInlineMarkdown(listItem)}
          </li>
        </ol>
      );
      return;
    }

    flushList();

    // Handle headers
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={index} style={{
          fontSize: '1.125rem',
          fontWeight: 600,
          color: '#ffffff',
          margin: '1.5rem 0 1rem',
          borderBottom: '1px solid #333333',
          paddingBottom: '0.5rem'
        }}>
          {renderInlineMarkdown(line.substring(4))}
        </h3>
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2 key={index} style={{
          fontSize: '1.25rem',
          fontWeight: 600,
          color: '#ffffff',
          margin: '1.5rem 0 1rem',
          borderBottom: '1px solid #333333',
          paddingBottom: '0.5rem'
        }}>
          {renderInlineMarkdown(line.substring(3))}
        </h2>
      );
    } else if (line.startsWith('# ')) {
      elements.push(
        <h1 key={index} style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          color: '#ffffff',
          margin: '1.5rem 0 1rem',
          borderBottom: '1px solid #333333',
          paddingBottom: '0.5rem'
        }}>
          {renderInlineMarkdown(line.substring(2))}
        </h1>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={index} style={{ height: '0.5rem' }} />);
    } else {
      elements.push(
        <p key={index} style={{
          margin: '0.5rem 0',
          lineHeight: 1.6,
          color: '#ffffff'
        }}>
          {renderInlineMarkdown(line)}
        </p>
      );
    }
  });

  flushList();
  flushCodeBlock();

  return <div>{elements}</div>;
}

function renderInlineMarkdown(text: string): JSX.Element {
  const parts = [];
  let currentText = text;
  let key = 0;

  // Handle inline code first
  currentText = currentText.replace(/`([^`]+)`/g, (match, code) => {
    const placeholder = `__INLINE_CODE_${key}__`;
    parts.push({
      type: 'code',
      content: code,
      placeholder,
      key: key++
    });
    return placeholder;
  });

  // Handle bold text
  currentText = currentText.replace(/\*\*([^*]+)\*\*/g, (match, bold) => {
    const placeholder = `__BOLD_${key}__`;
    parts.push({
      type: 'bold',
      content: bold,
      placeholder,
      key: key++
    });
    return placeholder;
  });

  // Handle italic text
  currentText = currentText.replace(/\*([^*]+)\*/g, (match, italic) => {
    const placeholder = `__ITALIC_${key}__`;
    parts.push({
      type: 'italic',
      content: italic,
      placeholder,
      key: key++
    });
    return placeholder;
  });

  // Replace placeholders with JSX elements
  let result: (string | JSX.Element)[] = [currentText];
  
  parts.forEach(part => {
    const newResult: (string | JSX.Element)[] = [];
    result.forEach(item => {
      if (typeof item === 'string') {
        const splitParts = item.split(part.placeholder);
        for (let i = 0; i < splitParts.length; i++) {
          if (i > 0) {
            if (part.type === 'code') {
              newResult.push(
                <code key={part.key} style={{
                  background: '#333333',
                  padding: '0.125rem 0.25rem',
                  borderRadius: '0.25rem',
                  fontSize: '0.875em',
                  fontFamily: 'ui-monospace, "Cascadia Code", monospace',
                  color: '#ffffff'
                }}>
                  {part.content}
                </code>
              );
            } else if (part.type === 'bold') {
              newResult.push(
                <strong key={part.key} style={{ fontWeight: 600 }}>
                  {part.content}
                </strong>
              );
            } else if (part.type === 'italic') {
              newResult.push(
                <em key={part.key} style={{ fontStyle: 'italic' }}>
                  {part.content}
                </em>
              );
            }
          }
          if (splitParts[i]) {
            newResult.push(splitParts[i]);
          }
        }
      } else {
        newResult.push(item);
      }
    });
    result = newResult;
  });

  return <span>{result}</span>;
}

export default function App() {
  const [users, setUsers] = useState<GmailUser[]>([]);
  const [messagesByUser, setMessagesByUser] = useState<Record<number, GmailMessage[]>>({});
  const [selected, setSelected] = useState<Record<number, GmailMessage | null>>({ 1: null, 2: null });
  const [showEncrypted, setShowEncrypted] = useState<Record<number, boolean>>({ 1: false, 2: false });
  const [fetchCount, setFetchCount] = useState<number>(5);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachmentsByUser, setAttachmentsByUser] = useState<Record<number, GmailAttachment[]>>({});
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  
  // Layout state
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [selectedUserForDetails, setSelectedUserForDetails] = useState<number | null>(null);
  const [showEmailDetails, setShowEmailDetails] = useState(false);

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

  const bulkFetchAndIngest = async (userSlot: number) => {
    setLoading(true);
    setIngestStatus(`Starting bulk fetch and ingest for User ${userSlot}...`);
    try {
      const res = await fetch(`${BACKEND}/gmail/bulk-fetch-ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user: userSlot, 
          n: fetchCount,
          ingest_attachments: true,
          ingest_mail_bodies: true
        }),
      });
      const data = await res.json();
      
      if (data.error) {
        setIngestStatus(`Error: ${data.error}`);
        setError(data.error);
      } else {
        const summary = `Bulk ingest completed!\nEmails: ${data.emails_fetched}\nMail bodies: ${data.mail_bodies_ingested}\nAttachments: ${data.attachments_ingested}/${data.attachments_processed}`;
        setIngestStatus(summary);
        
        await updateEmails(fetchCount);
        
        if (data.errors && data.errors.length > 0) {
          console.warn("Bulk ingest errors:", data.errors);
          setError(`Some items failed to ingest. Check console for details.`);
        }
      }
    } catch (e) {
      console.error(e);
      setIngestStatus("Bulk fetch and ingest failed");
      setError("Network or server error");
    } finally {
      setLoading(false);
      setTimeout(() => setIngestStatus(null), 8000);
    }
  };

  const bulkFetchAndIngestAll = async () => {
    setLoading(true);
    setIngestStatus("Starting bulk fetch and ingest for ALL users...");
    
    const configuredUsers = users.filter(u => u.configured);
    let totalEmails = 0, totalBodies = 0, totalAttachments = 0;
    const allErrors: string[] = [];
    
    try {
      for (const user of configuredUsers) {
        setIngestStatus(`Processing User ${user.slot}...`);
        
        const res = await fetch(`${BACKEND}/gmail/bulk-fetch-ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            user: user.slot, 
            n: fetchCount,
            ingest_attachments: true,
            ingest_mail_bodies: true
          }),
        });
        const data = await res.json();
        
        if (data.error) {
          allErrors.push(`User ${user.slot}: ${data.error}`);
        } else {
          totalEmails += data.emails_fetched || 0;
          totalBodies += data.mail_bodies_ingested || 0;
          totalAttachments += data.attachments_ingested || 0;
          if (data.errors) {
            allErrors.push(...data.errors);
          }
        }
      }
      
      const summary = `Bulk ingest completed for ALL users!\nTotal emails: ${totalEmails}\nMail bodies: ${totalBodies}\nAttachments: ${totalAttachments}`;
      setIngestStatus(summary);
      
      await updateEmails(fetchCount);
      
      if (allErrors.length > 0) {
        console.warn("Bulk ingest errors:", allErrors);
        setError(`${allErrors.length} items failed to ingest. Check console for details.`);
      }
      
    } catch (e) {
      console.error(e);
      setIngestStatus("Bulk ingest failed for all users");
      setError("Network or server error");
    } finally {
      setLoading(false);
      setTimeout(() => setIngestStatus(null), 10000);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim()) return;
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: currentMessage,
      timestamp: new Date()
    };
    
    setChatMessages(prev => [...prev, userMessage]);
    setCurrentMessage("");
    setIsTyping(true);
    
    try {
      const res = await fetch(`${BACKEND}/rag/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: currentMessage, k: 6 }),
      });
      const data = await res.json();
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.answer || "Sorry, I couldn't process your request.",
        timestamp: new Date(),
        sources: data.sources || [],
        route: data.route || ""
      };
      
      setChatMessages(prev => [...prev, assistantMessage]);
    } catch (e) {
      console.error(e);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "Sorry, there was an error processing your request.",
        timestamp: new Date()
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const styles = {
    app: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
      height: '100vh',
      background: '#000000',
      color: '#ffffff',
      display: 'flex',
      flexDirection: 'column' as const,
      overflow: 'hidden'
    },
    header: {
      padding: '1.5rem 2rem',
      borderBottom: '1px solid #333333',
      background: '#111111'
    },
    headerTitle: {
      margin: '0 0 0.5rem',
      fontSize: '1.5rem',
      fontWeight: 600,
      color: '#ffffff'
    },
    headerSubtitle: {
      margin: '0',
      color: '#888888',
      fontSize: '0.9rem'
    },
    controls: {
      display: 'flex',
      gap: '1rem',
      alignItems: 'center',
      padding: '1rem 2rem',
      background: '#111111',
      borderBottom: '1px solid #333333',
      flexWrap: 'wrap' as const
    },
    btn: {
      padding: '0.5rem 1rem',
      border: '1px solid #333333',
      borderRadius: '0.375rem',
      background: '#222222',
      color: '#ffffff',
      fontWeight: 500,
      cursor: 'pointer',
      fontSize: '0.875rem',
      transition: 'all 0.2s ease'
    },
    btnPrimary: {
      background: '#ffffff',
      color: '#000000',
      borderColor: '#ffffff'
    },
    fetchControl: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      background: '#222222',
      padding: '0.5rem 1rem',
      borderRadius: '0.375rem',
      border: '1px solid #333333'
    },
    error: {
      padding: '0.75rem 2rem',
      background: '#1f1f1f',
      color: '#ff6b6b',
      fontSize: '0.875rem',
      borderBottom: '1px solid #333333'
    },
    statusIndicator: {
      padding: '0.75rem',
      margin: '1rem 2rem',
      background: '#1a1a1a',
      border: '1px solid #333333',
      borderRadius: '0.5rem',
      color: '#10b981',
      fontSize: '0.875rem',
      whiteSpace: 'pre-line' as const
    },
    mainLayout: {
      flex: 1,
      display: 'flex',
      minHeight: 0
    },
    leftPanel: {
      width: leftPanelCollapsed ? '60px' : '400px',
      background: '#111111',
      borderRight: '1px solid #333333',
      display: 'flex',
      flexDirection: 'column' as const,
      transition: 'width 0.3s ease',
      overflow: 'hidden'
    },
    panelHeader: {
      padding: '1rem',
      borderBottom: '1px solid #333333',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: '1rem'
    },
    panelTitle: {
      fontWeight: 600,
      fontSize: '1rem',
      color: '#ffffff',
      margin: '0',
      whiteSpace: 'nowrap' as const,
      overflow: 'hidden',
      opacity: leftPanelCollapsed ? 0 : 1,
      transition: 'opacity 0.3s ease'
    },
    collapseBtn: {
      background: 'none',
      border: 'none',
      color: '#888888',
      cursor: 'pointer',
      padding: '0.25rem',
      borderRadius: '0.25rem',
      transition: 'all 0.2s ease',
      fontSize: '1.2rem'
    },
    usersList: {
      flex: 1,
      overflowY: 'auto' as const,
      padding: leftPanelCollapsed ? '0' : '1rem'
    },
    userCard: {
      background: '#1a1a1a',
      border: '1px solid #333333',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      overflow: 'hidden',
      transition: 'all 0.3s ease'
    },
    userHeader: {
      padding: leftPanelCollapsed ? '0.75rem 0.5rem' : '1rem',
      cursor: 'pointer',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      transition: 'background 0.2s ease'
    },
    userInfo: {
      overflow: 'hidden'
    },
    userTitle: {
      fontWeight: 600,
      color: '#ffffff',
      margin: '0',
      fontSize: leftPanelCollapsed ? '0.75rem' : '0.9rem',
      whiteSpace: 'nowrap' as const,
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    },
    userEmail: {
      color: '#888888',
      fontSize: '0.8rem',
      margin: '0.25rem 0 0',
      whiteSpace: 'nowrap' as const,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      display: leftPanelCollapsed ? 'none' : 'block'
    },
    userStatus: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      flexShrink: 0
    },
    userConfigured: {
      background: '#10b981'
    },
    userNotConfigured: {
      background: '#6b7280'
    },
    chatContainer: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      background: '#000000'
    },
    chatHeader: {
      padding: '1rem 2rem',
      borderBottom: '1px solid #333333',
      background: '#111111'
    },
    chatTitle: {
      fontSize: '1.25rem',
      fontWeight: 600,
      color: '#ffffff',
      margin: '0 0 0.5rem'
    },
    chatSubtitle: {
      color: '#888888',
      fontSize: '0.9rem',
      margin: '0'
    },
    chatMessages: {
      flex: 1,
      overflowY: 'auto' as const,
      padding: '2rem',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '1.5rem'
    },
    emptyState: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center' as const,
      padding: '3rem'
    },
    emptyStateTitle: {
      fontSize: '1.5rem',
      color: '#ffffff',
      margin: '0 0 1rem',
      fontWeight: 600
    },
    emptyStateText: {
      color: '#888888',
      margin: '0 0 2rem',
      fontSize: '1rem',
      lineHeight: 1.5
    },
    messageBubble: {
      maxWidth: '70%'
    },
    messageBubbleUser: {
      alignSelf: 'flex-end'
    },
    messageBubbleAssistant: {
      alignSelf: 'flex-start'
    },
    messageContent: {
      padding: '1rem 1.25rem',
      borderRadius: '1rem',
      wordBreak: 'break-word' as const,
      lineHeight: 1.5
    },
    messageContentUser: {
      background: '#ffffff',
      color: '#000000',
      border: '1px solid #ffffff'
    },
    messageContentAssistant: {
      background: '#1a1a1a',
      color: '#ffffff',
      border: '1px solid #333333'
    },
    messageTimestamp: {
      fontSize: '0.75rem',
      color: '#666666',
      marginTop: '0.5rem'
    },
    messageTimestampUser: {
      textAlign: 'right' as const
    },
    messageTimestampAssistant: {
      textAlign: 'left' as const
    },
    chatInputContainer: {
      padding: '1.5rem 2rem',
      borderTop: '1px solid #333333',
      background: '#111111'
    },
    chatInputWrapper: {
      display: 'flex',
      gap: '1rem',
      alignItems: 'flex-end',
      maxWidth: '100%'
    },
    chatInput: {
      flex: 1,
      padding: '1rem',
      border: '1px solid #333333',
      borderRadius: '0.75rem',
      background: '#000000',
      color: '#ffffff',
      fontSize: '0.95rem',
      lineHeight: 1.4,
      resize: 'none' as const,
      minHeight: '50px',
      maxHeight: '150px',
      fontFamily: 'inherit'
    },
    sendBtn: {
      padding: '1rem 1.5rem',
      background: '#ffffff',
      color: '#000000',
      border: '1px solid #ffffff',
      borderRadius: '0.75rem',
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      whiteSpace: 'nowrap' as const
    }
  };

    return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.headerTitle}>Gmail RAG Assistant</h1>
        <p style={styles.headerSubtitle}>Intelligent email analysis and document processing</p>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button 
          style={{...styles.btn, ...styles.btnPrimary}} 
          onClick={loadUsers} 
          disabled={loading}
        >
          Load Users
        </button>

        <div style={styles.fetchControl}>
          <label htmlFor="fetchCount" style={{fontWeight: 500, color: '#ffffff', fontSize: '0.875rem'}}>Fetch last:</label>
          <input
            id="fetchCount"
            type="range"
            min={1}
            max={50}
            value={fetchCount}
            onChange={(e) => setFetchCount(parseInt(e.target.value))}
            style={{width: '80px', accentColor: '#ffffff'}}
          />
          <span style={{fontWeight: 600, color: '#ffffff', minWidth: '2rem', textAlign: 'center', fontSize: '0.875rem'}}>{fetchCount}</span>
          <span style={{fontWeight: 500, color: '#ffffff', fontSize: '0.875rem'}}>messages</span>
        </div>

        <button 
          style={{...styles.btn, ...styles.btnPrimary}} 
          onClick={() => updateEmails(fetchCount)} 
          disabled={loading || users.length === 0}
        >
          Update Emails
        </button>
        
        <button 
          style={{...styles.btn, ...styles.btnPrimary}} 
          onClick={() => bulkFetchAndIngestAll()} 
          disabled={loading || users.filter(u => u.configured).length === 0}
        >
          Fetch & Ingest All
        </button>
      </div>

      {/* Error Display */}
      {error && <div style={styles.error}>{error}</div>}

      {/* Status Display */}
      {ingestStatus && (
        <div style={styles.statusIndicator}>
          {ingestStatus}
        </div>
      )}

      {/* Main Layout */}
      <div style={styles.mainLayout}>
        {/* Left Panel - Users */}
        <div style={styles.leftPanel}>
          <div style={styles.panelHeader}>
            <h3 style={styles.panelTitle}>Email Accounts</h3>
            <button 
              style={styles.collapseBtn}
              onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
            >
              {leftPanelCollapsed ? '→' : '←'}
            </button>
          </div>
          
          <div style={styles.usersList}>
            {users.map((user) => (
              <div key={user.slot} style={styles.userCard}>
                <div 
                  style={styles.userHeader}
                  onClick={() => setSelectedUserForDetails(
                    selectedUserForDetails === user.slot ? null : user.slot
                  )}
                >
                  <div style={styles.userInfo}>
                    <h4 style={styles.userTitle}>User {user.slot}</h4>
                    <p style={styles.userEmail}>{user.email || "(not configured)"}</p>
                  </div>
                  <div style={{
                    ...styles.userStatus,
                    ...(user.configured ? styles.userConfigured : styles.userNotConfigured)
                  }}></div>
                </div>
                
                {selectedUserForDetails === user.slot && !leftPanelCollapsed && (
                  <div style={{
                    padding: '1rem',
                    borderTop: '1px solid #333333',
                    background: '#0f0f0f'
                  }}>
                    <div style={{maxHeight: '200px', overflowY: 'auto'}}>
                      {(messagesByUser[user.slot] || []).slice(0, 5).map((message) => (
                        <div 
                          key={message.id}
                          style={{
                            padding: '0.5rem',
                            marginBottom: '0.5rem',
                            background: '#1a1a1a',
                            borderRadius: '0.25rem',
                            cursor: 'pointer',
                            transition: 'background 0.2s ease'
                          }}
                          onClick={() => {
                            setSelected(prev => ({ ...prev, [user.slot]: message }));
                            setShowEmailDetails(true);
                          }}
                        >
                          <div style={{
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            color: '#ffffff',
                            marginBottom: '0.25rem',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {message.subject || "(no subject)"}
                          </div>
                          <div style={{
                            fontSize: '0.7rem',
                            color: '#888888',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {message.from} • {message.date}
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap'}}>
                      <button 
                        style={{...styles.btn, fontSize: '0.75rem', padding: '0.375rem 0.75rem'}}
                        onClick={() => bulkFetchAndIngest(user.slot)} 
                        disabled={!user.configured || loading}
                      >
                        Bulk Ingest
                      </button>
                      <button 
                        style={{...styles.btn, fontSize: '0.75rem', padding: '0.375rem 0.75rem'}}
                        onClick={() => loadAttachments(user.slot)} 
                        disabled={!selected[user.slot] || loading}
                      >
                        Load Attachments
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel - Chat */}
        <div style={styles.chatContainer}>
          <div style={styles.chatHeader}>
            <h2 style={styles.chatTitle}>Chat Assistant</h2>
            <p style={styles.chatSubtitle}>Ask questions about your email content</p>
          </div>
          
          <div style={styles.chatMessages}>
            {chatMessages.length === 0 && (
              <div style={styles.emptyState}>
                <h3 style={styles.emptyStateTitle}>Welcome to Gmail RAG Assistant</h3>
                <p style={styles.emptyStateText}>Ask questions about your email content and I'll help you find the answers.</p>
                <p style={styles.emptyStateText}>Start by loading and ingesting your email data, then ask me anything!</p>
              </div>
            )}
            
            {chatMessages.map((message) => (
              <div 
                key={message.id} 
                style={{
                  ...styles.messageBubble,
                  ...(message.type === 'user' ? styles.messageBubbleUser : styles.messageBubbleAssistant)
                }}
              >
                <div style={{
                  ...styles.messageContent,
                  ...(message.type === 'user' ? styles.messageContentUser : styles.messageContentAssistant)
                }}>
                  {message.type === 'user' ? (
                    message.content
                  ) : (
                    renderMarkdown(message.content)
                  )}
                </div>
                <div style={{
                  ...styles.messageTimestamp,
                  ...(message.type === 'user' ? styles.messageTimestampUser : styles.messageTimestampAssistant)
                }}>
                  {message.timestamp.toLocaleTimeString()}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div style={{
                    marginTop: '1rem',
                    paddingTop: '1rem',
                    borderTop: '1px solid #333333'
                  }}>
                    <div style={{
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      color: '#888888',
                      marginBottom: '0.5rem'
                    }}>Sources:</div>
                    <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
                      {message.sources.map((source, i) => (
                        <div key={i} style={{
                          fontSize: '0.75rem',
                          padding: '0.25rem 0.5rem',
                          background: '#333333',
                          color: '#ffffff',
                          borderRadius: '0.25rem',
                          border: '1px solid #555555'
                        }}>
                          {source.subject || source.filename} 
                          {source.page ? ` (page ${source.page})` : source.sheet ? ` (sheet ${source.sheet})` : ""}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {isTyping && (
              <div style={{
                display: 'flex',
                gap: '0.25rem',
                alignItems: 'center',
                padding: '1rem 1.25rem',
                background: '#1a1a1a',
                border: '1px solid #333333',
                borderRadius: '1rem',
                maxWidth: '70%',
                alignSelf: 'flex-start'
              }}>
                <div style={{
                  width: '6px',
                  height: '6px',
                  background: '#888888',
                  borderRadius: '50%',
                  animation: 'typing 1.4s infinite'
                }}></div>
                <div style={{
                  width: '6px',
                  height: '6px',
                  background: '#888888',
                  borderRadius: '50%',
                  animation: 'typing 1.4s infinite 0.2s'
                }}></div>
                <div style={{
                  width: '6px',
                  height: '6px',
                  background: '#888888',
                  borderRadius: '50%',
                  animation: 'typing 1.4s infinite 0.4s'
                }}></div>
              </div>
            )}
          </div>

          <div style={styles.chatInputContainer}>
            <div style={styles.chatInputWrapper}>
              <textarea
                style={styles.chatInput}
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your emails..."
                rows={1}
              />
              <button 
                style={styles.sendBtn}
                onClick={sendMessage} 
                disabled={!currentMessage.trim() || isTyping}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Email Details Modal */}
      {showEmailDetails && selectedUserForDetails !== null && selected[selectedUserForDetails] && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '2rem'
        }} onClick={() => setShowEmailDetails(false)}>
          <div style={{
            background: '#111111',
            border: '1px solid #333333',
            borderRadius: '1rem',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{
              padding: '1.5rem',
              borderBottom: '1px solid #333333',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h3 style={{
                fontSize: '1.2rem',
                fontWeight: 600,
                color: '#ffffff',
                margin: '0'
              }}>
                {selected[selectedUserForDetails]?.subject || "(no subject)"}
              </h3>
              <button 
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#888888',
                  cursor: 'pointer',
                  fontSize: '1.5rem',
                  padding: '0.25rem',
                  borderRadius: '0.25rem',
                  transition: 'all 0.2s ease'
                }}
                onClick={() => setShowEmailDetails(false)}
              >
                ×
              </button>
            </div>
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1.5rem'
            }}>
              <div style={{
                background: '#0a0a0a',
                border: '1px solid #333333',
                borderRadius: '0.5rem',
                padding: '1rem',
                fontFamily: 'ui-monospace, "Cascadia Code", monospace',
                fontSize: '0.85rem',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: '400px',
                overflowY: 'auto',
                marginBottom: '1rem'
              }}>
                {showEncrypted[selectedUserForDetails] 
                  ? toBase64Unicode(selected[selectedUserForDetails]?.combined_text || "")
                  : (selected[selectedUserForDetails]?.combined_text || "")
                }
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <button
                  style={styles.btn}
                  onClick={() => setShowEncrypted(prev => ({ ...prev, [selectedUserForDetails]: false }))}
                  disabled={!showEncrypted[selectedUserForDetails]}
                >
                  Normal
                </button>
                <button
                  style={styles.btn}
                  onClick={() => setShowEncrypted(prev => ({ ...prev, [selectedUserForDetails]: true }))}
                  disabled={showEncrypted[selectedUserForDetails]}
                >
                  Encrypted
                </button>
                <button 
                  style={{...styles.btn, ...styles.btnPrimary}}
                  onClick={() => ingestMailBody(selectedUserForDetails)} 
                  disabled={loading}
                >
                  Ingest Mail Body
                </button>
              </div>
              
              {(attachmentsByUser[selectedUserForDetails] || []).length > 0 && (
                <div>
                  <h4 style={{ color: '#ffffff', marginBottom: '1rem' }}>Attachments</h4>
                  {(attachmentsByUser[selectedUserForDetails] || []).map((attachment) => (
                    <div key={attachment.index} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '0.75rem',
                      background: '#222222',
                      border: '1px solid #333333',
                      borderRadius: '0.5rem',
                      marginBottom: '0.5rem'
                    }}>
                      <div style={{ color: '#ffffff' }}>
                        {attachment.filename || `attachment-${attachment.index}`} 
                        ({attachment.content_type || "?"}, {Math.round((attachment.size || 0)/1024)} KB)
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <a 
                          href={`${BACKEND}${attachment.download_url}`} 
                          target="_blank" 
                          rel="noreferrer"
                          style={{
                            ...styles.btn,
                            textDecoration: 'none',
                            display: 'inline-block'
                          }}
                        >
                          Download
                        </a>
                        <button 
                          style={{...styles.btn, ...styles.btnPrimary}}
                          onClick={() => ingestAttachment(selectedUserForDetails, attachment)}
                        >
                          Ingest
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes typing {
          0%, 60%, 100% {
            transform: scale(1);
            opacity: 0.5;
          }
          30% {
            transform: scale(1.2);
            opacity: 1;
          }
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }

        ::-webkit-scrollbar-track {
          background: #111111;
        }

        ::-webkit-scrollbar-thumb {
          background: #333333;
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: #555555;
        }

        /* Button hover effects */
        button:hover:not(:disabled) {
          opacity: 0.8;
        }

        /* Input focus effects */
        input:focus, textarea:focus {
          outline: none;
          border-color: #555555 !important;
        }

        textarea::placeholder {
          color: #666666;
        }

        /* Responsive design */
        @media (max-width: 768px) {
          .main-layout > div:first-child {
            width: ${leftPanelCollapsed ? '50px' : '300px'} !important;
          }
        }
      `}</style>
    </div>
  );
}
// frontend/src/graph.ts

export const GRAPH = "https://graph.microsoft.com/v1.0";
export const ATTACHMENT_MAX_BYTES = 3 * 1024 * 1024; // ~3MB (contentBytes typically present only for small files)

export type GraphEmailAddress = { address?: string; name?: string };
export type GraphFrom = { emailAddress?: GraphEmailAddress };
export type GraphMessage = {
  id: string;
  subject?: string;
  from?: GraphFrom;
  receivedDateTime?: string;
  hasAttachments?: boolean;
};

export type AttachmentFile = {
  file: File;
  name: string;
  type: string;
  size?: number;
};

/**
 * List recent messages with minimal fields.
 */
export async function listMessages(
  accessToken: string,
  top: number = 25
): Promise<GraphMessage[]> {
  const url = `${GRAPH}/me/messages?$select=id,subject,from,receivedDateTime,hasAttachments&$orderby=receivedDateTime desc&$top=${top}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Graph listMessages failed: ${res.status}`);
  const data = await res.json();
  return (data.value as GraphMessage[]) || [];
}

/**
 * Fetch message and return plain text body (HTML -> text).
 */
export async function getMessageBodyText(
  accessToken: string,
  messageId: string
): Promise<string> {
  const url = `${GRAPH}/me/messages/${messageId}?$select=id,body`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Graph getMessageBodyText failed: ${res.status}`);
  const msg = await res.json();
  const html: string = msg?.body?.content || "";
  return htmlToText(html);
}

/**
 * Fetch small attachments (with contentBytes) and return as File objects.
 * Only returns supported types (PDF, XLSX) within size threshold.
 */
export async function getSmallAttachmentsAsFiles(
  accessToken: string,
  messageId: string
): Promise<AttachmentFile[]> {
  const url = `${GRAPH}/me/messages/${messageId}/attachments?$select=id,name,contentType,size,contentBytes`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok)
    throw new Error(`Graph getSmallAttachmentsAsFiles failed: ${res.status}`);
  const data = await res.json();
  const values: any[] = data.value || [];

  const items = values
    .filter((a) => !!a.contentBytes) // FileAttachment with inline content
    .filter((a) => (a.size || 0) <= ATTACHMENT_MAX_BYTES)
    .filter((a) => isSupportedContentType(String(a.contentType || "")));

  const files: AttachmentFile[] = items.map((a) => {
    const bytes = base64ToBytes(a.contentBytes as string);
    const blob = new Blob([bytes], {
      type: a.contentType || "application/octet-stream",
    });
    const file = new File([blob], a.name || "attachment", {
      type: a.contentType || "",
    });
    return { file, name: a.name, type: a.contentType, size: a.size };
  });

  return files;
}

/**
 * Basic HTML -> text conversion.
 */
export function htmlToText(html: string): string {
  if (!html) return "";
  const doc = new DOMParser().parseFromString(html, "text/html");
  return doc.body.textContent || "";
}

/**
 * Check if content type is supported for the prototype (PDF, XLSX).
 */
export function isSupportedContentType(contentType: string): boolean {
  const ct = contentType.toLowerCase();
  return ct.includes("pdf") || ct.includes("spreadsheetml");
}

/**
 * Base64 string -> Uint8Array
 */
export function base64ToBytes(b64: string): Uint8Array {
  const bstr = atob(b64);
  const bytes = new Uint8Array(bstr.length);
  for (let i = 0; i < bstr.length; i++) bytes[i] = bstr.charCodeAt(i);
  return bytes;
}
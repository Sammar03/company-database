import { useCallback, useEffect, useState, type DragEvent } from "react";
import type { Chat, ChatMessage, DocumentInfo } from "./types";
import {
  ApiError,
  deleteDocument,
  listDocuments,
  sendChat,
  uploadDocuments,
} from "./api/client";
import { loadChats, saveChats } from "./chats";
import DocumentList from "./components/DocumentList";
import ChatList from "./components/ChatList";
import ChatWindow from "./components/ChatWindow";
import { AIChatInput } from "./components/AIChatInput";

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [chats, setChats] = useState<Chat[]>(loadChats);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ text: string; error: boolean } | null>(null);
  const [dragging, setDragging] = useState(false);
  // Admin key is entered at runtime (never shipped in the bundle) and stored
  // only on this device; required to delete documents.
  const [adminKey, setAdminKey] = useState(
    () => localStorage.getItem("company-rag-admin-key") ?? ""
  );
  const isAdmin = adminKey !== "";

  useEffect(() => saveChats(chats), [chats]);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      /* backend may be starting; list stays empty */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Auto-clear a successful upload message.
  useEffect(() => {
    if (uploadMsg && !uploadMsg.error) {
      const t = setTimeout(() => setUploadMsg(null), 4000);
      return () => clearTimeout(t);
    }
  }, [uploadMsg]);

  const handleUpload = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const res = await uploadDocuments(files);
      await refresh();
      const parts: string[] = [];
      if (res.indexed.length) parts.push(`Indexed ${res.indexed.length} file(s)`);
      parts.push(...res.errors);
      setUploadMsg({
        text: parts.join(" · ") || "No files indexed",
        error: res.errors.length > 0 && res.indexed.length === 0,
      });
    } catch (err) {
      setUploadMsg({
        text: err instanceof ApiError ? err.message : "Upload failed.",
        error: true,
      });
    } finally {
      setUploading(false);
    }
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!dragging) setDragging(true);
  };
  const onDragLeave = (e: DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleUpload(Array.from(e.dataTransfer.files));
  };

  const handleDeleteDoc = async (filename: string) => {
    setDeleting(filename);
    try {
      await deleteDocument(filename, adminKey);
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        alert("Admin key rejected — re-enter it to delete documents.");
        localStorage.removeItem("company-rag-admin-key");
        setAdminKey("");
      }
    } finally {
      setDeleting(null);
    }
  };

  const toggleAdmin = () => {
    if (isAdmin) {
      localStorage.removeItem("company-rag-admin-key");
      setAdminKey("");
      return;
    }
    const key = window.prompt("Enter admin key to enable document deletion:");
    if (key) {
      localStorage.setItem("company-rag-admin-key", key);
      setAdminKey(key);
    }
  };

  const messages = chats.find((c) => c.id === currentId)?.messages ?? [];

  const appendToChat = (id: string, msg: ChatMessage) =>
    setChats((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, messages: [...c.messages, msg], updatedAt: Date.now() }
          : c
      )
    );

  const handleSend = async (text: string) => {
    const id = currentId ?? crypto.randomUUID();
    const history = currentId ? messages : [];
    const userMsg: ChatMessage = { role: "user", content: text };

    if (!currentId) {
      const title = text.length > 40 ? text.slice(0, 40) + "…" : text;
      setChats((prev) => [
        { id, title, messages: [userMsg], updatedAt: Date.now() },
        ...prev,
      ]);
      setCurrentId(id);
    } else {
      appendToChat(id, userMsg);
    }

    setLoading(true);
    try {
      const res = await sendChat(text, history);
      appendToChat(id, {
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        grounded: res.grounded,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      appendToChat(id, { role: "assistant", content: `⚠️ ${msg}`, grounded: false });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteChat = (id: string) => {
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (id === currentId) setCurrentId(null);
  };

  return (
    <div className="flex h-screen bg-snow text-ink-black">
      <aside className="flex w-[260px] shrink-0 flex-col gap-2 overflow-y-auto bg-paper p-3">
        <ChatList
          chats={chats}
          currentId={currentId}
          onSelect={setCurrentId}
          onNew={() => setCurrentId(null)}
          onDelete={handleDeleteChat}
        />
        <div className="mt-2">
          <div className="flex items-center justify-between px-3 py-2">
            <h2 className="text-xs font-medium uppercase tracking-wide text-ash">
              Documents
            </h2>
            <button
              onClick={toggleAdmin}
              className="text-[11px] text-ash transition hover:text-ink-black"
              title={isAdmin ? "Exit admin mode" : "Enter admin key to delete documents"}
            >
              {isAdmin ? "Admin ✓" : "Admin"}
            </button>
          </div>
          <DocumentList
            documents={documents}
            onDelete={handleDeleteDoc}
            deleting={deleting}
            isAdmin={isAdmin}
          />
        </div>
      </aside>

      <main
        className="relative flex min-w-0 flex-1 flex-col"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        {dragging && (
          <div className="pointer-events-none absolute inset-0 z-20 m-3 flex items-center justify-center rounded-[28px] border-2 border-dashed border-ink-black/30 bg-snow/70 backdrop-blur-sm">
            <p className="text-sm font-medium text-ink-black">
              Drop files to upload (PDF, TXT, MD)
            </p>
          </div>
        )}

        <header className="flex items-center px-6 py-3">
          <span className="text-lg font-semibold tracking-[-0.27px]">Company Database</span>
        </header>

        <div className="min-h-0 flex-1">
          <ChatWindow messages={messages} loading={loading} />
        </div>

        <div className="pb-6">
          {(uploading || uploadMsg) && (
            <p
              className={`mx-auto mb-1 max-w-3xl px-4 text-center text-xs ${
                uploadMsg?.error ? "text-red-500" : "text-ash"
              }`}
            >
              {uploading ? "Uploading…" : uploadMsg?.text}
            </p>
          )}
          <AIChatInput onSend={handleSend} onUpload={handleUpload} disabled={loading} />
          <p className="mx-auto -mt-1 max-w-3xl px-4 text-center text-[11px] leading-snug text-ash">
            Ask a question about your documents. Answers are grounded in the uploaded
            files and include source citations.
          </p>
        </div>
      </main>
    </div>
  );
}

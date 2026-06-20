import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import type { ChatMessage } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
}

export default function ChatWindow({ messages, loading }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="px-6 text-center text-2xl text-ink-black sm:px-16">
          Your documents, ready to answer.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 py-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 px-2 text-sm text-ash">
            <Loader2 className="h-4 w-4 animate-spin" />
            Searching the documents…
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

import { FileText, Trash2 } from "lucide-react";
import type { DocumentInfo } from "../types";

interface Props {
  documents: DocumentInfo[];
  onDelete: (filename: string) => void;
  deleting: string | null;
  isAdmin: boolean;
}

export default function DocumentList({ documents, onDelete, deleting, isAdmin }: Props) {
  if (documents.length === 0) {
    return <p className="px-3 py-2 text-sm text-ash">No documents indexed yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-0.5">
      {documents.map((doc) => (
        <li
          key={doc.filename}
          className="group flex items-center justify-between gap-2 rounded-[10px] px-3 py-2 hover:bg-fog"
        >
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-ash" />
            <div className="min-w-0">
              <p className="truncate text-sm text-ink-black" title={doc.filename}>
                {doc.filename}
              </p>
            </div>
          </div>
          {isAdmin && (
            <button
              onClick={() => onDelete(doc.filename)}
              disabled={deleting === doc.filename}
              className="shrink-0 rounded p-1 text-ash opacity-0 transition hover:text-red-500 group-hover:opacity-100 disabled:opacity-50"
              aria-label={`Delete ${doc.filename}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

import dynamic from "next/dynamic";
import { Code2 } from "lucide-react";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

// Map backend language values to Monaco Editor language identifiers
const getMonacoLanguage = (lang: string): string => {
  const languageMap: Record<string, string> = {
    python: "python",
    cpp: "cpp",
    java: "java",
    nodejs: "javascript",
  };
  return languageMap[lang] || lang;
};

interface EditorPanelProps {
  language: string;
  code: string;
  onCodeChange: (code: string) => void;
}

export function EditorPanel({
  language,
  code,
  onCodeChange,
}: EditorPanelProps) {
  return (
    <div className="h-full flex flex-col bg-[#121212]">
      <div className="flex items-center justify-between px-4 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-emerald-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Editor
          </span>
        </div>
      </div>
      <div className="flex-1 relative no-scrollbar overflow-hidden">
        <Editor
          height="100%"
          language={getMonacoLanguage(language)}
          value={code}
          onChange={(v) => onCodeChange(v || "")}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: "var(--font-mono)",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 16 },
            scrollbar: {
              vertical: "hidden",
              horizontal: "hidden",
            },
          }}
        />
      </div>
    </div>
  );
}

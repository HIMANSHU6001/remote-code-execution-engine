// EditorPanel.tsx
"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import { useTheme } from "@/context/ThemeContext";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

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
  onEditorMount?: (editor: any) => void;
}

export function EditorPanel({
  language,
  code,
  onCodeChange,
  onEditorMount,
}: EditorPanelProps) {
  const { isDark } = useTheme();

  return (
    <div className="h-full flex flex-col" >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 shrink-0 border-b"
        style={{
          height: "41px",
          borderColor: "var(--border-subtle)",
          background: "var(--panel-header-tint)",
        }}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-text-tertiary">
            Editor
          </span>
        </div>
      </div>

      {/* Monaco */}
      <div className="flex-1 relative no-scrollbar overflow-hidden">
        <Editor
          height="100%"
          language={getMonacoLanguage(language)}
          value={code}
          onMount={onEditorMount}
          onChange={(v) => onCodeChange(v || "")}
          theme={isDark ? "vs-dark" : "light"}
          options={{
            minimap: { enabled: false },
            fontSize: 13.5,
            fontFamily: "var(--font-mono)",
            fontLigatures: true,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            glyphMargin: true,
            padding: { top: 16, bottom: 16 },
            lineNumbersMinChars: 3,
            renderLineHighlight: "gutter",
            scrollbar: {
              vertical: "auto",
              horizontal: "hidden",
              verticalScrollbarSize: 6,
            },
            cursorBlinking: "smooth",
            cursorSmoothCaretAnimation: "on",
          }}
        />
      </div>
    </div>
  );
}
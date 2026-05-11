// ProblemHeader.tsx
import { ChevronLeft, Sparkles, ChevronDown } from "lucide-react";
import type { ProblemWithDescription } from "./types";
import Link from "next/link";

interface ProblemHeaderProps {
  problem: ProblemWithDescription;
  language: string;
  onLanguageChange: (lang: string) => void;
  isAIOpen: boolean;
  onToggleAI: () => void;
}

const LANGUAGES = [
  { value: "python", label: "Python 3" },
  { value: "cpp", label: "C++" },
  { value: "java", label: "Java" },
  { value: "nodejs", label: "Node.js" },
];

export function ProblemHeader({
  problem,
  language,
  onLanguageChange,
  isAIOpen,
  onToggleAI,
}: ProblemHeaderProps) {
  return (
    <header
      className="flex items-center justify-between px-4 shrink-0 border-b"
      style={{
        height: "48px",
        background: "#0a0a0c",
        borderColor: "rgba(255,255,255,0.06)",
      }}
    >
      {/* Left: back + title */}
      <div className="flex items-center gap-3 min-w-0">
        <Link
          href="/problems"
          className="flex items-center gap-1 text-zinc-600 hover:text-zinc-300 transition-colors shrink-0"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="text-xs font-medium hidden sm:block">Problems</span>
        </Link>

        <div
          className="w-px h-4 shrink-0"
          style={{ background: "rgba(255,255,255,0.08)" }}
        />

        <span className="text-sm font-semibold text-zinc-200 truncate">
          {problem.title}
        </span>
      </div>

      {/* Right: language selector + AI toggle */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Language selector */}
        <div className="relative flex items-center">
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="appearance-none pl-3 pr-7 py-1.5 rounded-lg text-[11px] font-semibold text-zinc-400 hover:text-zinc-300 transition-colors focus:outline-none cursor-pointer"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          <ChevronDown
            className="h-3 w-3 text-zinc-600 absolute right-2 pointer-events-none"
          />
        </div>

        {/* AI toggle */}
        <button
          onClick={onToggleAI}
          className="flex items-center gap-1.5 h-7 px-3 rounded-lg text-[11px] font-semibold transition-all"
          style={
            isAIOpen
              ? {
                background: "rgba(16,185,129,0.12)",
                border: "1px solid rgba(16,185,129,0.25)",
                color: "#34d399",
                boxShadow: "0 0 12px rgba(16,185,129,0.1)",
              }
              : {
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "#71717a",
              }
          }
        >
          <Sparkles
            className="h-3.5 w-3.5"
            style={isAIOpen ? { fill: "#34d399" } : {}}
          />
          Ask AI
        </button>
      </div>
    </header>
  );
}
// ProblemHeader.tsx
import { ChevronLeft, Sparkles, ChevronDown, Sun, Moon } from "lucide-react";
import type { ProblemWithDescription } from "./types";
import Link from "next/link";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

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
  const { isDark, toggleTheme } = useTheme();

  return (
    <header
      className="flex items-center justify-between px-4 shrink-0 border-b"
      style={{
        height: "48px",
        background: "var(--navbar-bg)",
        borderColor: "var(--border-subtle)",
      }}
    >
      {/* Left: back + title */}
      <div className="flex items-center gap-3 min-w-0">
        <Link
          href="/problems"
          className="flex items-center gap-1 text-text-muted hover:text-text-secondary transition-colors shrink-0"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="text-xs font-medium hidden sm:block">Problems</span>
        </Link>

        <div
          className="w-px h-4 shrink-0"
          style={{ background: "var(--divider)" }}
        />

        <span className="text-sm font-semibold text-text-primary truncate">
          {problem.title}
        </span>
      </div>

      {/* Right: theme toggle + language selector + AI toggle */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="hover-langfuse relative w-8 h-8 flex items-center justify-center rounded-lg border border-border-primary hover:bg-[var(--hover-bg)] transition-all duration-200"
          aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
        >
          <Sun
            className={cn(
              "h-4 w-4 absolute transition-all duration-300",
              isDark
                ? "rotate-0 scale-100 text-amber-400"
                : "rotate-90 scale-0 text-amber-400"
            )}
          />
          <Moon
            className={cn(
              "h-4 w-4 absolute transition-all duration-300",
              isDark
                ? "-rotate-90 scale-0 text-text-tertiary"
                : "rotate-0 scale-100 text-text-tertiary"
            )}
          />
        </button>

        {/* Language selector */}
        <div className="relative flex items-center">
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="appearance-none pl-3 pr-7 py-1.5 rounded-lg text-[11px] font-semibold text-text-tertiary hover:text-text-secondary transition-colors focus:outline-none cursor-pointer"
            style={{
              background: "var(--hover-bg)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          <ChevronDown
            className="h-3 w-3 text-text-muted absolute right-2 pointer-events-none"
          />
        </div>

        {/* AI toggle */}
        <button
          onClick={onToggleAI}
          className="flex items-center gap-1.5 h-7 px-3 rounded-lg text-[11px] font-semibold transition-all hover-langfuse"
          style={
            isAIOpen
              ? {
                border: "1px solid rgba(16,185,129,0.25)",
                color: "#34d399",
                boxShadow: "0 0 12px rgba(16,185,129,0.1)",
              }
              : {
                border: "1px solid var(--border-subtle)",
                color: "var(--text-tertiary)",
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
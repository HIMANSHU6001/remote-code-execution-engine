import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, HelpCircle, Cpu, Database, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProblemWithDescription } from "./types";

interface DescriptionPanelProps {
  problem: ProblemWithDescription;
}

const difficultyConfig = {
  easy: {
    label: "Easy",
    color: "#10b981",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.2)",
  },
  medium: {
    label: "Medium",
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.2)",
  },
  hard: {
    label: "Hard",
    color: "#f43f5e",
    bg: "rgba(244,63,94,0.08)",
    border: "rgba(244,63,94,0.2)",
  },
};

export function DescriptionPanel({ problem }: DescriptionPanelProps) {
  const diff = difficultyConfig[problem.difficulty as keyof typeof difficultyConfig] ?? difficultyConfig.medium;

  return (
    <div
      className="h-full flex flex-col no-scrollbar overflow-y-auto"
      style={{ background: "var(--surface-secondary)" }}
    >
      {/* Sticky header */}
      <div
        className="flex items-center justify-between px-4 shrink-0 sticky top-0 z-10 border-b"
        style={{
          height: "41px",
          background: "var(--panel-header-bg)",
          backdropFilter: "blur(12px)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded-md bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <BookOpen className="h-3 w-3 text-emerald-400" />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-text-tertiary">
            Problem
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Cpu className="h-3 w-3 text-text-muted" />
            <span className="text-[11px] text-text-muted font-mono">{problem.base_time_limit_ms}ms</span>
          </div>
          <div
            className="w-px h-3"
            style={{ background: "var(--divider)" }}
          />
          <div className="flex items-center gap-1.5">
            <Database className="h-3 w-3 text-text-muted" />
            <span className="text-[11px] text-text-muted font-mono">{problem.base_memory_limit_mb}MB</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-8 max-w-2xl mx-auto w-full bg-background">
        {/* Title */}
        <h1 className="text-2xl font-bold text-text-primary tracking-tight mb-4 leading-snug">
          {problem.title}
        </h1>

        {/* Badges */}
        <div className="flex flex-wrap gap-2 items-center mb-8">
          <span
            className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border"
            style={{ color: diff.color, background: diff.bg, borderColor: diff.border }}
          >
            {diff.label}
          </span>

          {(problem.topics?.length ?? 0) > 0 && (
            <div
              className="w-px h-3.5"
              style={{ background: "var(--divider)" }}
            />
          )}

          {problem.topics?.map((t) => (
            <span
              key={t.id}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors cursor-default"
              style={{
                background: "var(--tag-bg)",
                border: "1px solid var(--tag-border)",
                color: "var(--text-tertiary)",
              }}
            >
              {t.name}
            </span>
          ))}
        </div>

        {/* Divider */}
        <div className="mb-6" style={{ height: "1px", background: "var(--divider)" }} />

        {/* Description */}
        <div
          className="prose prose-sm max-w-none"
          style={
            {
              "--tw-prose-body": "var(--text-secondary)",
              "--tw-prose-headings": "var(--text-primary)",
              "--tw-prose-strong": "var(--text-primary)",
              "--tw-prose-code": "var(--code-text)",
              "--tw-prose-links": "var(--text-secondary)",
              "--tw-prose-bullets": "var(--text-muted)",
              "--tw-prose-counters": "var(--text-muted)",
              lineHeight: "1.75",
            } as React.CSSProperties
          }
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code: ({ children, className }) =>
                className ? (
                  <code className={className}>{children}</code>
                ) : (
                  <code
                    style={{
                      background: "var(--code-bg)",
                      color: "var(--code-text)",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontSize: "0.85em",
                      fontFamily: "var(--font-mono, monospace)",
                      border: "1px solid var(--code-border)",
                    }}
                  >
                    {children}
                  </code>
                ),
              pre: ({ children }) => (
                <pre
                  style={{
                    background: "var(--surface-elevated)",
                    border: "1px solid var(--code-border)",
                    borderRadius: "10px",
                    padding: "14px 16px",
                    overflowX: "auto",
                    fontSize: "13px",
                    fontFamily: "var(--font-mono, monospace)",
                    margin: "12px 0",
                  }}
                >
                  {children}
                </pre>
              ),
              blockquote: ({ children }) => (
                <blockquote
                  style={{
                    borderLeft: "3px solid var(--border-primary)",
                    paddingLeft: "14px",
                    margin: "12px 0",
                    color: "var(--text-tertiary)",
                    fontStyle: "italic",
                  }}
                >
                  {children}
                </blockquote>
              ),
            }}
          >
            {problem.description}
          </ReactMarkdown>
        </div>

        {/* Hints */}
        {problem.hints && problem.hints.length > 0 && (
          <div className="mt-10 space-y-3">
            <div className="flex items-center gap-2 mb-4">
              <div
                className="h-px flex-1"
                style={{ background: "var(--divider)" }}
              />
              <div className="flex items-center gap-1.5">
                <HelpCircle className="h-3.5 w-3.5 text-amber-500/70" />
                <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-text-muted">
                  Hints
                </span>
              </div>
              <div
                className="h-px flex-1"
                style={{ background: "var(--divider)" }}
              />
            </div>

            <div className="space-y-2">
              {problem.hints.map((hint, i) => (
                <details
                  key={i}
                  className="group rounded-xl overflow-hidden border transition-colors"
                  style={{
                    background: "rgba(245,158,11,0.03)",
                    borderColor: "rgba(245,158,11,0.12)",
                  }}
                >
                  <summary
                    className="flex items-center justify-between px-4 py-3 text-xs font-semibold cursor-pointer list-none select-none"
                    style={{ color: "#a16207" }}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold"
                        style={{
                          background: "rgba(245,158,11,0.15)",
                          color: "#f59e0b",
                        }}
                      >
                        {i + 1}
                      </span>
                      Hint {i + 1}
                    </span>
                    <ChevronDown
                      className="h-3.5 w-3.5 transition-transform group-open:rotate-180"
                      style={{ color: "#a16207" }}
                    />
                  </summary>
                  <div
                    className="px-4 pb-4 text-xs leading-relaxed border-t"
                    style={{
                      color: "#92400e",
                      borderColor: "rgba(245,158,11,0.1)",
                      paddingTop: "10px",
                    }}
                  >
                    {hint}
                  </div>
                </details>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
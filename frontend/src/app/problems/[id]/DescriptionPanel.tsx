import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, HelpCircle, Code2, Cpu, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProblemWithDescription } from "./types";

interface DescriptionPanelProps {
  problem: ProblemWithDescription;
}

export function DescriptionPanel({ problem }: DescriptionPanelProps) {
  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] no-scrollbar overflow-y-auto">
      {/* Sticky Header */}
      <div className="flex items-center justify-between px-4 h-11 border-b border-white/5 shrink-0 bg-[#121212]/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center h-5 w-5 rounded-md bg-emerald-500/10 border border-emerald-500/20">
            <BookOpen className="h-3 w-3 text-emerald-500" />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-zinc-400">
            Problem Description
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
            <Cpu className="h-3 w-3" />
            <span>{problem.base_time_limit_ms}ms</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
            <Database className="h-3 w-3" />
            <span>{problem.base_memory_limit_mb}MB</span>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-3xl mx-auto w-full">
        {/* Title and Difficulty */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white tracking-tight mb-4">
            {problem.title}
          </h1>
          <div className="flex flex-wrap gap-2 items-center">
            <span
              className={cn(
                "px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-colors",
                problem.difficulty === "easy"
                  ? "text-emerald-400 bg-emerald-400/5 border-emerald-400/20"
                  : problem.difficulty === "medium"
                    ? "text-amber-400 bg-amber-400/5 border-amber-400/20"
                    : "text-rose-400 bg-rose-400/5 border-rose-400/20"
              )}
            >
              {problem.difficulty}
            </span>

            <div className="h-4 w-px bg-white/10 mx-1" />

            {problem.topics?.map((t) => (
              <span
                key={t.id}
                className="px-2.5 py-1 rounded-full bg-white/5 hover:bg-white/10 text-zinc-400 text-[10px] font-medium border border-white/5 cursor-default transition-all"
              >
                {t.name}
              </span>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="prose prose-invert max-w-none prose-p:text-zinc-300 prose-p:leading-relaxed prose-headings:text-white prose-headings:font-bold prose-strong:text-white prose-strong:font-semibold prose-code:text-emerald-400 prose-code:bg-emerald-400/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-[#1a1a1a] prose-pre:border prose-pre:border-white/5 prose-li:text-zinc-300 prose-a:text-emerald-400 prose-a:no-underline hover:prose-a:underline">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {problem.description}
          </ReactMarkdown>
        </div>

        {/* Hints Section */}
        {problem.hints && problem.hints.length > 0 && (
          <div className="mt-12 space-y-4 pt-8 border-t border-white/5">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-amber-500" />
              Hints
            </h2>
            <div className="space-y-3">
              {problem.hints.map((hint, i) => (
                <details key={i} className="group bg-white/5 border border-white/5 rounded-xl overflow-hidden transition-all hover:bg-white/10">
                  <summary className="px-5 py-4 text-sm font-medium text-zinc-300 cursor-pointer list-none flex items-center justify-between">
                    <span>Hint {i + 1}</span>
                    <span className="text-zinc-500 group-open:rotate-180 transition-transform">↓</span>
                  </summary>
                  <div className="px-5 pb-4 text-sm text-zinc-400 border-t border-white/5 pt-3 leading-relaxed">
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

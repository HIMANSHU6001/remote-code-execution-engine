import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProblemWithDescription } from "./types";

interface DescriptionPanelProps {
  problem: ProblemWithDescription;
}

export function DescriptionPanel({ problem }: DescriptionPanelProps) {
  return (
    <div className="h-full flex flex-col bg-[#121212] no-scrollbar overflow-y-auto">
      <div className="flex items-center gap-2 px-4 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a] sticky top-0 z-10">
        <BookOpen className="h-4 w-4 text-emerald-500" />
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Description
        </span>
      </div>
      <div className="p-6 prose prose-invert max-w-none font-sans">
        <h1 className="text-2xl font-bold text-white mb-4">{problem.title}</h1>
        <div className="flex gap-2 mb-6">
          <span
            className={cn(
              "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest border",
              problem.difficulty === "easy"
                ? "text-emerald-500 bg-emerald-500/10 border-emerald-500/20"
                : problem.difficulty === "medium"
                  ? "text-amber-500 bg-amber-500/10 border-amber-500/20"
                  : "text-rose-500 bg-rose-500/10 border-rose-500/20"
            )}
          >
            {problem.difficulty}
          </span>
          {problem.topics?.map((t) => (
            <span
              key={t.id}
              className="px-2 py-0.5 rounded bg-zinc-800/50 text-zinc-500 text-[10px] font-medium border border-zinc-800"
            >
              {t.name}
            </span>
          ))}
        </div>

        <div className="text-zinc-300 leading-relaxed space-y-4 prose-headings:text-white prose-a:text-emerald-500 prose-strong:text-white prose-code:text-emerald-400 prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {problem.description}
          </ReactMarkdown>
        </div>

        <div className="mt-8 space-y-6">
          {(problem.sample_test_cases || []).map((tc, index) => (
            <div key={tc.id} className="space-y-3">
              <h3 className="text-sm font-bold text-white">Example {index + 1}:</h3>
              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-xl font-mono text-xs space-y-2">
                <p>
                  <span className="text-zinc-500">Input:</span> {tc.input_data}
                </p>
                <p>
                  <span className="text-zinc-500">Output:</span>{" "}
                  {tc.expected_output}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

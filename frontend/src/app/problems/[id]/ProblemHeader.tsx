import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import type { ProblemWithDescription } from "./types";

interface ProblemHeaderProps {
  problem: ProblemWithDescription;
  language: string;
  onLanguageChange: (lang: string) => void;
}

export function ProblemHeader({
  problem,
  language,
  onLanguageChange,
}: ProblemHeaderProps) {
  return (
    <header className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 shrink-0 bg-[#0f0f0f]">
      <div className="flex items-center gap-4">
        <Link
          href="/problems"
          className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="text-sm font-medium">Problems</span>
        </Link>
        <div className="h-4 w-px bg-zinc-800" />
        <span className="text-sm font-bold text-white">{problem.title}</span>
      </div>
      <div className="flex items-center gap-3">
        <select
          value={language}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 rounded-md px-2 py-1 outline-none focus:border-emerald-500"
        >
          <option value="python">Python3</option>
          <option value="cpp">C++</option>
          <option value="java">Java</option>
          <option value="nodejs">Node.js</option>
        </select>
      </div>
    </header>
  );
}

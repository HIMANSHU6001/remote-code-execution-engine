import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ProblemWithDescription } from "./types";

interface TestcasesPanelProps {
  problem: ProblemWithDescription;
  activeSampleCaseIndex: number;
  onCaseChange: (index: number) => void;
}

export function TestcasesPanel({
  problem,
  activeSampleCaseIndex,
  onCaseChange,
}: TestcasesPanelProps) {
  const activeSampleCase =
    problem.sample_test_cases?.[activeSampleCaseIndex];

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap rounded-xl border border-zinc-800 bg-zinc-900/60 p-2">
        {(problem.sample_test_cases || []).map((_, i) => (
          <Button
            key={i}
            variant="default"
            size="sm"
            onClick={() => onCaseChange(i)}
            className={cn(
              "h-8 rounded-lg border text-xs font-semibold px-3 transition-colors",
              activeSampleCaseIndex === i
                ? "bg-brand-400 border-brand-400 text-zinc-950 hover:bg-brand-400"
                : "bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700"
            )}
          >
            Case {i + 1}
          </Button>
        ))}
      </div>
      <div className="space-y-4">
        {activeSampleCase && (
          <>
            <div className="space-y-2">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                Input
              </p>
              <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300">
                {activeSampleCase.input_data}
              </pre>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                Expected Output
              </p>
              <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300">
                {activeSampleCase.expected_output}
              </pre>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

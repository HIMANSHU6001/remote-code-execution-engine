// TestcasesPanel.tsx
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
  const activeSampleCase = problem.sample_test_cases?.[activeSampleCaseIndex];

  return (
    <div className="space-y-4">
      {/* Case tabs */}
      <div
        className="flex gap-1.5 flex-wrap p-1.5 rounded-xl"
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {(problem.sample_test_cases || []).map((_, i) => {
          const isActive = activeSampleCaseIndex === i;
          return (
            <button
              key={i}
              onClick={() => onCaseChange(i)}
              className="h-7 px-3 rounded-lg text-xs font-semibold transition-all"
              style={
                isActive
                  ? {
                    background: "rgba(16,185,129,0.15)",
                    border: "1px solid rgba(16,185,129,0.3)",
                    color: "#34d399",
                  }
                  : {
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    color: "#71717a",
                  }
              }
            >
              Case {i + 1}
            </button>
          );
        })}
      </div>

      {/* Case detail */}
      {activeSampleCase && (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <p
              className="text-[10px] font-bold uppercase tracking-[0.12em]"
              style={{ color: "#52525b" }}
            >
              Input
            </p>
            <pre
              className="p-3 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto"
              style={{
                background: "#111113",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "#a1a1aa",
              }}
            >
              {activeSampleCase.input_data}
            </pre>
          </div>

          <div className="space-y-1.5">
            <p
              className="text-[10px] font-bold uppercase tracking-[0.12em]"
              style={{ color: "#52525b" }}
            >
              Expected Output
            </p>
            <pre
              className="p-3 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto"
              style={{
                background: "#111113",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "#a1a1aa",
              }}
            >
              {activeSampleCase.expected_output}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
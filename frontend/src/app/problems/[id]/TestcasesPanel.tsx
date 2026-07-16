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
        className="flex gap-1.5 flex-wrap p-1.5"
        style={{
          border: "1px solid var(--border-subtle)",
        }}
      >
        {(problem.sample_test_cases || []).map((_, i) => {
          const isActive = activeSampleCaseIndex === i;
          return (
            <button
              key={i}
              onClick={() => onCaseChange(i)}
              className="h-7 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer hover-langfuse"
              style={
                isActive
                  ? {
                    background: "rgba(16,185,129,0.15)",
                    border: "1px solid rgba(16,185,129,0.3)",
                    color: "#34d399",
                  }
                  : {
                    background: "var(--tag-bg)",
                    border: "1px solid var(--tag-border)",
                    color: "var(--text-tertiary)",
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
              style={{ color: "var(--text-muted)" }}
            >
              Input
            </p>
            <pre
              className="p-3 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto"
              style={{
                background: "var(--code-bg)",
                border: "1px solid var(--code-border)",
                color: "var(--text-secondary)",
              }}
            >
              {activeSampleCase.input_data}
            </pre>
          </div>

          <div className="space-y-1.5">
            <p
              className="text-[10px] font-bold uppercase tracking-[0.12em]"
              style={{ color: "var(--text-muted)" }}
            >
              Expected Output
            </p>
            <pre
              className="p-3 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto"
              style={{
                background: "var(--code-bg)",
                border: "1px solid var(--code-border)",
                color: "var(--text-secondary)",
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
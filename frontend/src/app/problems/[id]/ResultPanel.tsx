// ResultPanel.tsx
import {
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  Terminal,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SubmissionDetailResponseWithCases, SubmissionCaseDetail } from "./types";
import type { SubmissionDetailResponse } from "@/lib/api-client";

interface ResultPanelProps {
  submissionResult: SubmissionDetailResponse | null;
  isSubmitting: boolean;
  activeResultCaseIndex: number;
  onCaseChange: (index: number) => void;
}

function StatBadge({
  icon: Icon,
  value,
}: {
  icon: React.ElementType;
  value: string;
}) {
  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}
    >
      <Icon className="h-3.5 w-3.5 text-zinc-600" />
      <span className="text-xs font-mono text-zinc-400">{value}</span>
    </div>
  );
}

function CodeBlock({ label, content, variant = "default" }: {
  label: string;
  content: string;
  variant?: "default" | "error";
}) {
  return (
    <div className="space-y-1.5">
      <p
        className="text-[10px] font-bold uppercase tracking-[0.12em]"
        style={{ color: variant === "error" ? "#f43f5e" : "#52525b" }}
      >
        {label}
      </p>
      <pre
        className="p-3 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto min-h-[52px]"
        style={{
          background: variant === "error" ? "rgba(244,63,94,0.05)" : "#111113",
          border: `1px solid ${variant === "error" ? "rgba(244,63,94,0.18)" : "rgba(255,255,255,0.07)"}`,
          color: variant === "error" ? "#fda4af" : "#a1a1aa",
        }}
      >
        {content || "—"}
      </pre>
    </div>
  );
}

export function ResultPanel({
  submissionResult,
  isSubmitting,
  activeResultCaseIndex,
  onCaseChange,
}: ResultPanelProps) {
  const submissionWithCases = submissionResult as SubmissionDetailResponseWithCases | null;
  const resultCaseDetails = submissionWithCases?.details ?? [];
  const activeResultCase = resultCaseDetails[activeResultCaseIndex] as SubmissionCaseDetail | undefined;

  if (isSubmitting) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 py-12">
        <div className="relative">
          <div
            className="absolute inset-0 rounded-full blur-lg"
            style={{ background: "rgba(16,185,129,0.2)" }}
          />
          <Loader2 className="h-8 w-8 text-emerald-400 animate-spin relative z-10" />
        </div>
        <div className="text-center space-y-1">
          <p className="text-sm font-medium text-zinc-400">Running your code</p>
          <p className="text-xs text-zinc-600">Executing on secure engine…</p>
        </div>
      </div>
    );
  }

  if (!submissionResult) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 py-12">
        <Terminal className="h-8 w-8 text-zinc-700" />
        <p className="text-sm text-zinc-600">Run your code to see results</p>
      </div>
    );
  }

  const isAccepted = submissionResult.verdict === "ACC";

  return (
    <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-200">
      {/* Verdict row */}
      <div
        className="flex items-center justify-between p-4 rounded-xl border"
        style={{
          background: isAccepted ? "rgba(16,185,129,0.05)" : "rgba(244,63,94,0.05)",
          borderColor: isAccepted ? "rgba(16,185,129,0.18)" : "rgba(244,63,94,0.18)",
        }}
      >
        <div className="flex items-center gap-2.5">
          {isAccepted ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          ) : (
            <XCircle className="h-5 w-5 text-rose-400" />
          )}
          <span
            className="font-bold text-lg tracking-tight"
            style={{ color: isAccepted ? "#34d399" : "#fb7185" }}
          >
            {isAccepted ? "Accepted" : submissionResult.verdict}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatBadge
            icon={Terminal}
            value={`${submissionResult.passed_test_cases ?? 0}/${submissionResult.total_test_cases ?? 0}`}
          />
          <StatBadge
            icon={Clock}
            value={`${submissionResult.execution_time_ms}ms`}
          />
          <StatBadge
            icon={Database}
            value={`${submissionResult.memory_used_mb}MB`}
          />
        </div>
      </div>

      {/* Case tabs */}
      {resultCaseDetails.length > 0 && (
        <>
          <div
            className="flex gap-1.5 flex-wrap p-1.5 rounded-xl"
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            {resultCaseDetails.map((tc, i) => {
              const caseVerdict = (tc as SubmissionCaseDetail).verdict;
              const isPass = caseVerdict === "ACC" || caseVerdict === "PASS";
              const isActive = activeResultCaseIndex === i;

              return (
                <button
                  key={tc.test_case_id || i}
                  onClick={() => onCaseChange(i)}
                  className="flex items-center gap-1.5 h-7 px-3 rounded-lg text-xs font-semibold transition-all"
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
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      background: isPass ? "#10b981" : "#f43f5e",
                      boxShadow: isPass ? "0 0 4px #10b981" : "0 0 4px #f43f5e",
                    }}
                  />
                  Case {i + 1}
                </button>
              );
            })}
          </div>

          <CodeBlock label="Input" content={activeResultCase?.input || "N/A"} />
          {activeResultCase?.stdout && (
            <CodeBlock label="Stdout" content={activeResultCase.stdout} />
          )}
          <div className="grid grid-cols-2 gap-3">
            <CodeBlock label="Your Output" content={activeResultCase?.actual || "No output"} />
            <CodeBlock label="Expected" content={activeResultCase?.expected || "N/A"} />
          </div>
        </>
      )}

      {/* Stderr */}
      {submissionResult.stderr_snippet && (
        <CodeBlock
          label="Error Output"
          content={submissionResult.stderr_snippet}
          variant="error"
        />
      )}

      {/* Fallback when no case details */}
      {resultCaseDetails.length === 0 && (
        <div className="grid grid-cols-2 gap-3">
          <CodeBlock label="Your Output" content={submissionResult.actual_output || "No output"} />
          <CodeBlock label="Expected" content={submissionResult.expected_output || "N/A"} />
        </div>
      )}
    </div>
  );
}
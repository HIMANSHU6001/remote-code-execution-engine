import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  Terminal,
  Loader2,
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
      <div className="h-full flex flex-col items-center justify-center gap-4 py-8">
        <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
        <p className="text-zinc-500 text-sm animate-pulse">
          Executing code on secure engine...
        </p>
      </div>
    );
  }

  if (!submissionResult) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-600 text-sm italic py-12">
        Run your code to see results
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {submissionResult.verdict === "ACC" ? (
            <div className="flex items-center gap-2 text-emerald-500 font-bold text-xl">
              <CheckCircle2 className="h-6 w-6" />
              Accepted
            </div>
          ) : (
            <div className="flex items-center gap-2 text-rose-500 font-bold text-xl">
              <XCircle className="h-6 w-6" />
              {submissionResult.verdict}
            </div>
          )}
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5 text-zinc-400">
            <Terminal className="h-4 w-4" />
            <span className="text-xs">
              {submissionResult.passed_test_cases ?? 0}/
              {submissionResult.total_test_cases ?? 0}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-400">
            <Clock className="h-4 w-4" />
            <span className="text-xs">{submissionResult.execution_time_ms}ms</span>
          </div>
          <div className="flex items-center gap-1.5 text-zinc-400">
            <Database className="h-4 w-4" />
            <span className="text-xs">{submissionResult.memory_used_mb}MB</span>
          </div>
        </div>
      </div>

      {resultCaseDetails.length > 0 && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap rounded-xl border border-zinc-800 bg-zinc-900/60 p-2">
            {resultCaseDetails.map((tc, i) => (
              <Button
                key={tc.test_case_id || i}
                variant="default"
                size="sm"
                onClick={() => onCaseChange(i)}
                className={cn(
                  "h-8 rounded-lg border text-xs font-semibold px-3 transition-colors",
                  activeResultCaseIndex === i
                    ? "bg-brand-500 border-brand-400 text-zinc-950 hover:bg-brand-400"
                    : "bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700"
                )}
              >
                Case {i + 1}
              </Button>
            ))}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
              Input
            </p>
            <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300 min-h-[60px]">
              {activeResultCase?.input || "N/A"}
            </pre>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
              Stdout
            </p>
            <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300 min-h-[60px]">
              {activeResultCase?.stdout || "No stdout"}
            </pre>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                Output
              </p>
              <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300 min-h-[60px]">
                {activeResultCase?.actual || "No output"}
              </pre>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                Expected Output
              </p>
              <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-sm text-zinc-300 min-h-[60px]">
                {activeResultCase?.expected || "N/A"}
              </pre>
            </div>
          </div>
        </div>
      )}

      {submissionResult.stderr_snippet && (
        <div className="space-y-2">
          <p className="text-[10px] font-bold text-rose-500 uppercase tracking-widest">
            Error Output
          </p>
          <pre className="p-4 bg-rose-500/5 border border-rose-500/20 rounded-xl font-mono text-xs text-rose-200 overflow-x-auto">
            {submissionResult.stderr_snippet}
          </pre>
        </div>
      )}

      {resultCaseDetails.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
              Output
            </p>
            <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300 min-h-[60px]">
              {submissionResult.actual_output || "No output"}
            </pre>
          </div>
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
              Expected Output
            </p>
            <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300 min-h-[60px]">
              {submissionResult.expected_output || "N/A"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Play, Send, Loader2, FlaskConical, BarChart2, Sparkles } from "lucide-react";
import { TestcasesPanel } from "./TestcasesPanel";
import { ResultPanel } from "./ResultPanel";
import type { ProblemWithDescription } from "./types";
import type { SubmissionDetailResponse } from "@/lib/api-client";

interface ConsolePanelProps {
  problem: ProblemWithDescription;
  activeTab: string;
  onTabChange: (tab: string) => void;
  activeSampleCaseIndex: number;
  onSampleCaseChange: (index: number) => void;
  activeResultCaseIndex: number;
  onResultCaseChange: (index: number) => void;
  submissionResult: SubmissionDetailResponse | null;
  isSubmitting: boolean;
  onRun: () => void;
  onSubmit: () => void;
  editor: any;
  code: string;
}

export function ConsolePanel({
  problem,
  activeTab,
  onTabChange,
  activeSampleCaseIndex,
  onSampleCaseChange,
  activeResultCaseIndex,
  onResultCaseChange,
  submissionResult,
  isSubmitting,
  onRun,
  onSubmit,
}: ConsolePanelProps) {
  return (
    <div className="h-full flex flex-col no-scrollbar">
      <Tabs value={activeTab} onValueChange={onTabChange} className="flex-1 flex flex-col min-h-0">
        {/* Tab bar */}
        <div
          className="flex items-center justify-between px-3 shrink-0 border-b"
          style={{
            height: "41px",
            borderColor: "var(--border-subtle)",
            background: "var(--panel-header-tint)",
          }}
        >
          <TabsList
            className="flex items-center gap-0 bg-transparent border-0 p-0 h-auto"
          >
            {[
              { value: "testcases", label: "Testcases", icon: FlaskConical },
              { value: "result", label: "Result", icon: BarChart2 },
            ].map(({ value, label, icon: Icon }) => (
              <TabsTrigger
                key={value}
                value={value}
                className="corner-accents cursor-pointer relative flex items-center gap-1.5 h-8 px-3 rounded-lg text-[11px] font-semibold tracking-wide border-0 transition-all
                  text-text-tertiary
                  data-[state=active]:text-emerald-400
                  "
              >
                <Icon className="h-3 w-3" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={onRun}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 h-7 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider text-text-tertiary hover:text-text-primary hover-langfuse border border-transparent hover:border-border-subtle transition-all disabled:opacity-40"
            >
              <Play className="h-3 w-3" />
              Run
            </button>
            <div className="p-0.5 hover-langfuse">
              <button
                onClick={onSubmit}
                disabled={isSubmitting}
                className="cursor-pointer flex items-center gap-1.5 h-7 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider text-white transition-all disabled:opacity-60"
                style={{
                  background: isSubmitting
                    ? "var(--muted-foreground)"
                    : "var(--primary)",
                  boxShadow: isSubmitting ? "none" : "0 0 12px rgba(0,0,0,0.1)",
                  color: "var(--primary-foreground)"
                }}
              >
                {isSubmitting ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Send className="h-3 w-3" />
                )}
                Submit
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 relative">
          <div className="absolute inset-0 overflow-y-auto no-scrollbar bg-background">
            <TabsContent value="testcases" className="m-0 p-4 space-y-4">
              <TestcasesPanel
                problem={problem}
                activeSampleCaseIndex={activeSampleCaseIndex}
                onCaseChange={onSampleCaseChange}
              />
            </TabsContent>

            <TabsContent value="result" className="m-0 p-4 h-full">
              <ResultPanel
                submissionResult={submissionResult}
                isSubmitting={isSubmitting}
                activeResultCaseIndex={activeResultCaseIndex}
                onCaseChange={onResultCaseChange}
              />
            </TabsContent>
          </div>
        </div>
      </Tabs>
    </div>
  );
}
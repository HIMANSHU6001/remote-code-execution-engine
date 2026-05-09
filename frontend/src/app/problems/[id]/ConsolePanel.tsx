import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Play, Send, Loader2 } from "lucide-react";
import { TestcasesPanel } from "./TestcasesPanel";
import { ResultPanel } from "./ResultPanel";
import type { ProblemWithDescription, SubmissionDetailResponseWithCases } from "./types";
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
    <div className="h-full flex flex-col bg-[#121212]">
      <Tabs value={activeTab} onValueChange={onTabChange} className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-2 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a]">
          <TabsList className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-1 h-8">
            <TabsTrigger
              value="testcases"
              className="h-6 px-3 rounded-md font-semibold tracking-wide text-zinc-400 data-[state=active]:bg-emerald-500 data-[state=active]:text-zinc-950 data-[state=active]:shadow-[0_0_0_1px_rgba(16,185,129,0.45)]"
            >
              Testcases
            </TabsTrigger>
            <TabsTrigger
              value="result"
              className="h-6 px-3 rounded-md font-semibold tracking-wide text-zinc-400 data-[state=active]:bg-emerald-500 data-[state=active]:text-zinc-950 data-[state=active]:shadow-[0_0_0_1px_rgba(16,185,129,0.45)]"
            >
              Result
            </TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-2 px-2">
            <Button
              onClick={onRun}
              disabled={isSubmitting}
              variant="ghost"
              size="sm"
              className="h-7 text-zinc-400 hover:text-white gap-1.5 text-[10px] font-bold uppercase"
            >
              <Play className="h-3 w-3" />
              Run
            </Button>
            <Button
              onClick={onSubmit}
              disabled={isSubmitting}
              size="sm"
              className="h-7 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-[10px] font-bold uppercase"
            >
              {isSubmitting ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Send className="h-3 w-3" />
              )}
              Submit
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden relative">
          <div className="absolute inset-0 no-scrollbar overflow-y-auto p-4">
            <TabsContent value="testcases" className="m-0 space-y-4">
              <TestcasesPanel
                problem={problem}
                activeSampleCaseIndex={activeSampleCaseIndex}
                onCaseChange={onSampleCaseChange}
              />
            </TabsContent>

            <TabsContent value="result" className="m-0 h-full">
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

"use client";

import React, { useEffect, useState } from "react";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Loader2 } from "lucide-react";
import {
  getProblemApiProblemsProblemIdGet as getProblemProblemsProblemIdGet,
  submitCodeApiSubmitPost as submitCodeSubmitPost,
  getSubmissionStatusApiSubmissionsJobIdGet as getSubmissionStatusSubmissionsJobIdGet,
  type SubmissionDetailResponse,
  type LanguageConfigResponse,
} from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { ProblemHeader } from "./ProblemHeader";
import { DescriptionPanel } from "./DescriptionPanel";
import { EditorPanel } from "./EditorPanel";
import { ConsolePanel } from "./ConsolePanel";
import { AICodingPanel } from "./AIAgentPanel";
import type { ProblemWithDescription, LanguageConfigMap } from "./types";
import { useParams } from "next/navigation";

export default function ProblemSolvingPage() {
  const params = useParams();
  const id = params?.id as string;

  const [problem, setProblem] = useState<ProblemWithDescription | null>(null);
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [langConfigMap, setLangConfigMap] = useState<LanguageConfigMap>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<SubmissionDetailResponse | null>(null);
  const [activeTab, setActiveTab] = useState("testcases");
  const [activeSampleCaseIndex, setActiveSampleCaseIndex] = useState(0);
  const [activeResultCaseIndex, setActiveResultCaseIndex] = useState(0);
  const [editor, setEditor] = useState<any>(null);
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(false);
  const { isAuthenticated } = useAuth();
  const [latestJobId, setLatestJobId] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchProblem = async () => {
      try {
        const res = await getProblemProblemsProblemIdGet({
          path: { problem_id: id },
        });
        if (res.data) {
          setProblem(res.data as ProblemWithDescription);

          // Build language config map
          if (res.data.language_configs && res.data.language_configs.length > 0) {
            const map: LanguageConfigMap = {};
            res.data.language_configs.forEach((config: LanguageConfigResponse) => {
              map[config.language] = config;
            });
            setLangConfigMap(map);

            // Set initial code from python boilerplate
            const pythonConfig = map["python"];
            setCode(pythonConfig ? pythonConfig.boilerplate : "");
          } else {
            setCode(res.data.difficulty === "easy" ? "# Write your solution here\n" : "");
          }
        }
      } catch (err) {
        console.error("Failed to fetch problem", err);
      }
    };

    fetchProblem();
  }, [id]);

  const handleLanguageChange = (newLanguage: string) => {
    setLanguage(newLanguage);

    const config = langConfigMap[newLanguage];
    if (config) {
      setCode(config.boilerplate);
    } else {
      setCode("");
    }
  };

  const handleSubmit = async (isSubmit: boolean = true) => {
    if (!isAuthenticated || !id) return;

    setIsSubmitting(true);
    setActiveTab("result");
    setSubmissionResult(null);

    try {
      const res = await submitCodeSubmitPost({
        body: {
          problem_id: id,
          language: language as any,
          code: code,
          is_submit: isSubmit,
        },
      });

      if (res.data) {
        setLatestJobId(res.data.job_id);
        pollStatus(res.data.job_id);
      }
    } catch (err) {
      console.error("Submission failed", err);
      setIsSubmitting(false);
    }
  };

  const pollStatus = async (jobId: string) => {
    const poll = async () => {
      try {
        const res = await getSubmissionStatusSubmissionsJobIdGet({
          path: { job_id: jobId },
        });

        if (res.data && res.data.status === "completed") {
          setActiveResultCaseIndex(0);
          setSubmissionResult(res.data);
          setIsSubmitting(false);
          return;
        }

        // Poll every 1 second
        setTimeout(poll, 1000);
      } catch (err) {
        console.error("Polling failed", err);
        setIsSubmitting(false);
      }
    };
    poll();
  };

  if (!problem) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-surface-primary">
        <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden bg-transparent text-text-secondary">
      <ProblemHeader
        problem={problem}
        language={language}
        onLanguageChange={handleLanguageChange}
        isAIOpen={isAIPanelOpen}
        onToggleAI={() => setIsAIPanelOpen(!isAIPanelOpen)}
      />

      <main className="flex-1 overflow-hidden">
        <ResizablePanelGroup orientation="horizontal">
          {/* Left Pane: Description */}
          <ResizablePanel defaultSize={40} minSize={20}>
            <DescriptionPanel problem={problem} />
          </ResizablePanel>

          <ResizableHandle className="w-1 bg-(--resizable-handle) hover:bg-emerald-500/50 transition-colors" />

          {/* Right Pane: Editor & Console */}
          <ResizablePanel defaultSize={isAIPanelOpen ? 45 : 60} minSize={30}>
            <ResizablePanelGroup orientation="vertical">
              {/* Editor */}
              <ResizablePanel defaultSize={70} minSize={20}>
                <EditorPanel
                  language={language}
                  code={code}
                  onCodeChange={setCode}
                  onEditorMount={setEditor}
                />
              </ResizablePanel>

              <ResizableHandle className="h-1 bg-[var(--resizable-handle)] hover:bg-emerald-500/50 transition-colors" />

              {/* Console */}
              <ResizablePanel defaultSize={30} minSize={10}>
                <ConsolePanel
                  problem={problem}
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  activeSampleCaseIndex={activeSampleCaseIndex}
                  onSampleCaseChange={setActiveSampleCaseIndex}
                  activeResultCaseIndex={activeResultCaseIndex}
                  onResultCaseChange={setActiveResultCaseIndex}
                  submissionResult={submissionResult}
                  isSubmitting={isSubmitting}
                  onRun={() => handleSubmit(false)}
                  onSubmit={() => handleSubmit(true)}
                  editor={editor}
                  code={code}
                />
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>

          {isAIPanelOpen && (
            <>
              <ResizableHandle className="w-1 bg-[var(--resizable-handle)] hover:bg-emerald-500/50 transition-colors" />
              <ResizablePanel defaultSize={20} minSize={15}>
                <AICodingPanel
                  code={code}
                  editor={editor}
                  onClose={() => setIsAIPanelOpen(false)}
                  latestJobId={latestJobId}
                />
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </main>
    </div>
  );
}

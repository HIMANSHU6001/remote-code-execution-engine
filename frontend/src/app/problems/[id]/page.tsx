"use client";

import React, { useEffect, useState, use } from "react";
import dynamic from "next/dynamic";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup
} from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Code2,
  Play,
  Send,
  Terminal,
  BookOpen,
  Settings,
  ChevronLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Database
} from "lucide-react";
import Link from "next/link";
import {
  getProblemProblemsProblemIdGet,
  submitCodeSubmitPost,
  getSubmissionStatusSubmissionsJobIdGet,
  type ProblemResponse,
  type SubmissionDetailResponse
} from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ProblemWithDescription extends ProblemResponse {
  description: string;
}

// Dynamic import for Monaco Editor
const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

export default function ProblemSolvingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [problem, setProblem] = useState<ProblemWithDescription | null>(null);
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<SubmissionDetailResponse | null>(null);
  const [activeTab, setActiveTab] = useState("testcases");
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    async function fetchProblem() {
      try {
        const res = await getProblemProblemsProblemIdGet({
          path: { problem_id: id }
        });
        if (res.data) {
          setProblem(res.data as ProblemWithDescription);
          // Set default code based on language
          setCode(res.data.difficulty === 'easy' ? "# Write your solution here\n" : "");
        }
      } catch (err) {
        console.error("Failed to fetch problem", err);
      }
    }
    fetchProblem();
  }, [id]);

  const handleSubmit = async (isSubmit: boolean = true) => {
    if (!isAuthenticated) return;

    setIsSubmitting(true);
    setActiveTab("result");
    setSubmissionResult(null);

    try {
      const res = await submitCodeSubmitPost({
        body: {
          problem_id: id,
          language: language as any,
          code: code,
          is_submit: isSubmit
        }
      });

      if (res.data) {
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
          path: { job_id: jobId }
        });

        if (res.data && res.data.status === "completed") {
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
      <div className="h-screen w-full flex items-center justify-center bg-[#0a0a0a]">
        <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden bg-[#0a0a0a] text-zinc-300">
      {/* Header */}
      <header className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 shrink-0 bg-[#0f0f0f]">
        <div className="flex items-center gap-4">
          <Link href="/problems" className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors">
            <ChevronLeft className="h-4 w-4" />
            <span className="text-sm font-medium">Problems</span>
          </Link>
          <div className="h-4 w-px bg-zinc-800" />
          <span className="text-sm font-bold text-white">{problem.title}</span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 rounded-md px-2 py-1 outline-none focus:border-emerald-500"
          >
            <option value="python">Python3</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
            <option value="nodejs">Node.js</option>
          </select>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {/* Workspace */}
      <main className="flex-1 overflow-hidden">
        <ResizablePanelGroup orientation="horizontal">
          {/* Left Pane: Description */}
          <ResizablePanel defaultSize={40} minSize={20}>
            <div className="h-full flex flex-col bg-[#121212] no-scrollbar overflow-y-auto">
              <div className="flex items-center gap-2 px-4 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a] sticky top-0 z-10">
                <BookOpen className="h-4 w-4 text-emerald-500" />
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Description</span>
              </div>
              <div className="p-6 prose prose-invert max-w-none font-sans">
                <h1 className="text-2xl font-bold text-white mb-4">{problem.title}</h1>
                <div className="flex gap-2 mb-6">
                  <span className={cn(
                    "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest border",
                    problem.difficulty === 'easy' ? "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" :
                      problem.difficulty === 'medium' ? "text-amber-500 bg-amber-500/10 border-amber-500/20" :
                        "text-rose-500 bg-rose-500/10 border-rose-500/20"
                  )}>
                    {problem.difficulty}
                  </span>
                  {problem.topics?.map(t => (
                    <span key={t.id} className="px-2 py-0.5 rounded bg-zinc-800/50 text-zinc-500 text-[10px] font-medium border border-zinc-800">
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
                  {problem.sample_test_cases.map((tc, index) => (
                    <div key={tc.id} className="space-y-3">
                      <h3 className="text-sm font-bold text-white">Example {index + 1}:</h3>
                      <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-xl font-mono text-xs space-y-2">
                        <p><span className="text-zinc-500">Input:</span> {tc.input_data}</p>
                        <p><span className="text-zinc-500">Output:</span> {tc.expected_output}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle className="w-1 bg-[#0a0a0a] hover:bg-emerald-500/50 transition-colors" />

          {/* Right Pane: Editor & Result */}
          <ResizablePanel defaultSize={60} minSize={30}>
            <ResizablePanelGroup orientation="vertical">
              {/* Editor */}
              <ResizablePanel defaultSize={70} minSize={20}>
                <div className="h-full flex flex-col bg-[#121212]">
                  <div className="flex items-center justify-between px-4 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a]">
                    <div className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-emerald-500" />
                      <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Editor</span>
                    </div>
                  </div>
                  <div className="flex-1 relative no-scrollbar overflow-hidden">
                    <Editor
                      height="100%"
                      language={language}
                      value={code}
                      onChange={(v) => setCode(v || "")}
                      theme="vs-dark"
                      options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                        fontFamily: "var(--font-mono)",
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        padding: { top: 16 },
                        scrollbar: {
                          vertical: 'hidden',
                          horizontal: 'hidden'
                        }
                      }}
                    />
                  </div>
                </div>
              </ResizablePanel>

              <ResizableHandle className="h-1 bg-[#0a0a0a] hover:bg-emerald-500/50 transition-colors" />

              {/* Console / Result */}
              <ResizablePanel defaultSize={30} minSize={10}>
                <div className="h-full flex flex-col bg-[#121212]">
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
                    <div className="flex items-center justify-between px-2 h-10 border-b border-zinc-800 shrink-0 bg-[#1a1a1a]">
                      <TabsList className="bg-transparent border-none">
                        <TabsTrigger
                          value="testcases"
                          className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white text-[10px] font-bold uppercase tracking-wider h-7"
                        >
                          Testcases
                        </TabsTrigger>
                        <TabsTrigger
                          value="result"
                          className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white text-[10px] font-bold uppercase tracking-wider h-7"
                        >
                          Result
                        </TabsTrigger>
                      </TabsList>
                      <div className="flex items-center gap-2 px-2">
                        <Button
                          onClick={() => handleSubmit(false)}
                          disabled={isSubmitting}
                          variant="ghost"
                          size="sm"
                          className="h-7 text-zinc-400 hover:text-white gap-1.5 text-[10px] font-bold uppercase"
                        >
                          <Play className="h-3 w-3" />
                          Run
                        </Button>
                        <Button
                          onClick={() => handleSubmit(true)}
                          disabled={isSubmitting}
                          size="sm"
                          className="h-7 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-[10px] font-bold uppercase"
                        >
                          {isSubmitting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
                          Submit
                        </Button>
                      </div>
                    </div>

                    <div className="flex-1 overflow-hidden relative">
                      <div className="absolute inset-0 no-scrollbar overflow-y-auto p-4">
                        <TabsContent value="testcases" className="m-0 space-y-4">
                          <div className="space-y-4">
                            <div className="flex gap-2">
                              {problem.sample_test_cases.map((_, i) => (
                                <Button key={i} variant="outline" size="sm" className="h-7 bg-zinc-800 border-zinc-700 text-white text-[10px]">
                                  Case {i + 1}
                                </Button>
                              ))}
                            </div>
                            <div className="space-y-4">
                              {problem.sample_test_cases[0] && (
                                <>
                                  <div className="space-y-2">
                                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Input</p>
                                    <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300">
                                      {problem.sample_test_cases[0].input_data}
                                    </pre>
                                  </div>
                                  <div className="space-y-2">
                                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Expected Output</p>
                                    <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300">
                                      {problem.sample_test_cases[0].expected_output}
                                    </pre>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </TabsContent>

                        <TabsContent value="result" className="m-0 h-full">
                          {isSubmitting ? (
                            <div className="h-full flex flex-col items-center justify-center gap-4 py-8">
                              <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
                              <p className="text-zinc-500 text-sm animate-pulse">Executing code on secure engine...</p>
                            </div>
                          ) : submissionResult ? (
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
                                    <Clock className="h-4 w-4" />
                                    <span className="text-xs">{submissionResult.execution_time_ms}ms</span>
                                  </div>
                                  <div className="flex items-center gap-1.5 text-zinc-400">
                                    <Database className="h-4 w-4" />
                                    <span className="text-xs">{submissionResult.memory_used_mb}MB</span>
                                  </div>
                                </div>
                              </div>

                              {submissionResult.stderr_snippet && (
                                <div className="space-y-2">
                                  <p className="text-[10px] font-bold text-rose-500 uppercase tracking-widest">Error Output</p>
                                  <pre className="p-4 bg-rose-500/5 border border-rose-500/20 rounded-xl font-mono text-xs text-rose-200 overflow-x-auto">
                                    {submissionResult.stderr_snippet}
                                  </pre>
                                </div>
                              )}

                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Actual Output</p>
                                  <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300 min-h-[60px]">
                                    {submissionResult.actual_output || "No output"}
                                  </pre>
                                </div>
                                <div className="space-y-2">
                                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Expected Output</p>
                                  <pre className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-300 min-h-[60px]">
                                    {submissionResult.expected_output || "N/A"}
                                  </pre>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="h-full flex items-center justify-center text-zinc-600 text-sm italic py-12">
                              Run your code to see results
                            </div>
                          )}
                        </TabsContent>
                      </div>
                    </div>
                  </Tabs>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      </main>
    </div>
  );
}

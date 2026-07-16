"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  listProblemsApiProblemsGet as listProblemsProblemsGet,
  getTopicsApiTopicsGet as getTopicsTopicsGet,
  type ProblemListResponse,
  type TopicResponse,
  type Difficulty
} from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import {
  Search,
  ChevronRight,
  Filter,
  CheckCircle2,
  Zap,
  BarChart3
} from "lucide-react";
import { cn } from "@/lib/utils";
import Navbar from "@/components/Navbar";

export default function ProblemsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ProblemsContent />
    </Suspense>
  );
}

function ProblemsContent() {
  const searchParams = useSearchParams();
  const topicParam = searchParams.get("topic");
  const [problems, setProblems] = useState<ProblemListResponse[]>([]);
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [difficultyFilter, setDifficultyFilter] = useState<Difficulty | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function fetchData() {
      try {
        const [probsRes, topicsRes] = await Promise.all([
          listProblemsProblemsGet({
            query: {
              difficulty: difficultyFilter === "all" ? undefined : difficultyFilter,
              topics: topicParam ? [topicParam] : undefined,
              size: 50
            }
          }),
          getTopicsTopicsGet()
        ]);

        setProblems(probsRes.data?.items || []);
        setTopics(topicsRes.data || []);
      } catch (err) {
        console.error("Failed to fetch problems", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [difficultyFilter, topicParam]);

  const difficultyColors = {
    easy: "text-brand-500 bg-brand-500/10 border-brand-500/20",
    medium: "text-amber-500 bg-amber-500/10 border-amber-500/20",
    hard: "text-destructive bg-destructive/10 border-destructive/20",
  };

  const filteredProblems = (problems || []).filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-screen w-full">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-[280px] shrink-0 border-r-2 border-border-dark flex-col overflow-y-auto hidden md:block" style={{ background: "var(--navbar-bg)" }}>
          {/* Difficulty Section */}
          <div className="p-5 border-b border-border-dark">
            <h3 className="text-[15px] font-medium text-text-primary mb-4 flex items-center gap-2">
              <Filter className="h-4 w-4 text-text-muted" />
              Difficulty
            </h3>
            <div className="flex flex-col gap-0.5">
              {["all", "easy", "medium", "hard"].map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficultyFilter(d as any)}
                  className={cn(
                    "cursor-pointer flex items-center justify-between px-3 py-1 rounded-lg transition-all text-[13px] font-[430] tracking-[-0.26px] hover-langfuse",
                    difficultyFilter === d
                      ? "text-brand-500"
                      : "text-text-tertiary hover:text-text-secondary"
                  )}
                >
                  <span className="capitalize">{d}</span>
                  {difficultyFilter === d && <CheckCircle2 className="h-3.5 w-3.5" />}
                </button>
              ))}
            </div>
          </div>

          {/* Topics Section */}
          <div className="p-5 border-b border-border-dark">
            <h3 className="text-[15px] font-medium text-text-primary mb-4 flex items-center gap-2">
              <Zap className="h-4 w-4 text-text-muted" />
              Topics
              {topicParam && (
                <Link href="/problems" className="ml-auto text-[10px] text-brand-500 hover:underline font-normal">
                  Clear
                </Link>
              )}
            </h3>
            <div className="flex flex-col gap-0.5">
              {topics.map((t) => (
                <Link
                  key={t.id}
                  href={`/problems?topic=${t.slug}`}
                  className={cn(
                    "flex items-center justify-between px-3 py-1 rounded-lg transition-all text-[13px] font-[430] tracking-[-0.26px] hover-langfuse",
                    topicParam === t.slug
                      ? "text-brand-500"
                      : "text-text-tertiary hover:text-text-secondary"
                  )}
                >
                  <span>{t.name}</span>
                </Link>
              ))}
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-10 bg-grid">
          <div className="max-w-4xl mx-auto space-y-8 bg-background">
            {/* Hero Section */}
            <div className="relative mb-12 border border-border-primary/50  z-0">

              {/* Corner markers */}
              <div className="absolute -top-px -left-px w-2.5 h-2.5 border-t border-l border-border-dark" />
              <div className="absolute -top-px -right-px w-2.5 h-2.5 border-t border-r border-border-dark" />
              <div className="absolute -bottom-px -left-px w-2.5 h-2.5 border-b border-l border-border-dark" />
              <div className="absolute -bottom-px -right-px w-2.5 h-2.5 border-b border-r border-border-dark" />

              {/* Main Content */}
              <div className="pt-10 pb-10 px-6 sm:px-12 flex flex-col items-center justify-center text-center">
                <h1 className="text-5xl sm:text-[64px] font-medium tracking-tight text-text-primary mb-6 flex flex-col gap-2 items-center leading-[1.1]">
                  <span className="relative inline-block px-3 z-0">
                    <span className="absolute inset-0 h-12 top-[20%] bottom-[10%] bg-brand-200 dark:bg-transparent rounded-sm z-[-1]" />
                    <span className="text-text-primary">Pick Your Challenge</span>
                  </span>
                </h1>

                <p className="max-w-[700px] text-[14px] font-[430] text-text-secondary leading-relaxed">
                  Sharpen your coding skills with our curated collection of problems.
                  From algorithmic fundamentals to complex system designs.
                </p>
              </div>

              {/* Separator with T-joints */}
              <div className="relative w-full h-px bg-border-primary/50">
                {/* Left T-joint */}
                <div className="absolute -left-px top-1/2 -translate-y-1/2 flex items-center">
                  <div className="w-px h-3 bg-border-dark" />
                  <div className="w-2 h-px bg-border-dark" />
                </div>
                {/* Right T-joint */}
                <div className="absolute -right-px top-1/2 -translate-y-1/2 flex items-center">
                  <div className="w-2 h-px bg-border-dark" />
                  <div className="w-px h-3 bg-border-dark" />
                </div>
              </div>

              {/* Problems List Area */}
              <div className="space-y-6 px-6 sm:px-12 pb-12 mt-8 w-full">
                {/* Search Bar */}
                <div className="relative group">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-text-muted group-focus-within:text-brand-500 transition-colors" />
                  <Input
                    placeholder="Search problems by name or ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-surface-secondary border-border-primary pl-12 h-14 rounded-2xl focus:ring-brand-500/50 focus:border-brand-500 transition-all text-text-secondary"
                  />
                </div>

                <div className="relative">
                  {isLoading ? (
                    <div className="p-12 flex items-center justify-center">
                      <div className="flex flex-col items-center gap-4">
                        <div className="h-10 w-10 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
                        <p className="text-text-muted text-sm font-medium">Loading challenges...</p>
                      </div>
                    </div>
                  ) : filteredProblems.length > 0 ? (
                    <div className="flex flex-col gap-1">
                      {filteredProblems.map((problem) => (
                        <Link
                          key={problem.id}
                          href={`/problems/${problem.id}`}
                          className="flex items-center justify-between p-5 transition-all group hover-langfuse"
                        >
                          <div className="flex items-center gap-6">
                            <div>
                              <h4 className="text-text-primary font-semibold group-hover:text-brand-400 transition-colors">
                                {problem.title}
                              </h4>
                              <div className="flex gap-3 mt-1.5">
                                {problem.topics?.map(topic => (
                                  <span key={topic.id} className="text-[10px] text-text-muted font-medium">#{topic.name}</span>
                                ))}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-6">
                            <div className={cn(
                              "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border",
                              difficultyColors[problem.difficulty as keyof typeof difficultyColors]
                            )}>
                              {problem.difficulty}
                            </div>
                            <ChevronRight className="h-5 w-5 text-text-muted group-hover:text-brand-500 group-hover:translate-x-1 transition-all" />
                          </div>
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="p-20 text-center">
                      <BarChart3 className="h-12 w-12 text-text-muted mx-auto mb-4" />
                      <h3 className="text-lg font-bold text-text-primary mb-1">No problems found</h3>
                      <p className="text-text-tertiary">Try adjusting your filters or search query.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

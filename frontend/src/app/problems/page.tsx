"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  listProblemsProblemsGet,
  getTopicsTopicsGet,
  type ProblemListResponse,
  type TopicResponse,
  type Difficulty
} from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Search,
  ChevronRight,
  Filter,
  CheckCircle2,
  Circle,
  Trophy,
  Zap,
  BarChart3
} from "lucide-react";
import { cn } from "@/lib/utils";

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
    easy: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
    medium: "text-amber-500 bg-amber-500/10 border-amber-500/20",
    hard: "text-rose-500 bg-rose-500/10 border-rose-500/20",
  };

  const filteredProblems = (problems || []).filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto px-4 py-12 max-w-6xl">
      {/* Hero Section */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">Pick Your Challenge</h1>
        <p className="text-zinc-500 text-lg max-w-2xl">
          Sharpen your coding skills with our curated collection of problems.
          From algorithmic fundamentals to complex system designs.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Difficulty
            </h3>
            <div className="flex flex-col gap-2">
              {["all", "easy", "medium", "hard"].map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficultyFilter(d as any)}
                  className={cn(
                    "flex items-center justify-between px-4 py-2.5 rounded-xl border transition-all text-sm font-medium",
                    difficultyFilter === d
                      ? "bg-emerald-600/10 border-emerald-500/50 text-emerald-500"
                      : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300"
                  )}
                >
                  <span className="capitalize">{d}</span>
                  {difficultyFilter === d && <CheckCircle2 className="h-4 w-4" />}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Topics
              {topicParam && (
                <Link href="/problems" className="ml-auto text-[10px] text-emerald-500 hover:underline">
                  Clear
                </Link>
              )}
            </h3>
            <div className="flex flex-wrap gap-2">
              {topics.map((t) => (
                <Link
                  key={t.id}
                  href={`/problems?topic=${t.slug}`}
                  className={cn(
                    "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                    topicParam === t.slug
                      ? "bg-emerald-600/10 border-emerald-500/50 text-emerald-500"
                      : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300"
                  )}
                >
                  {t.name}
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Problems List */}
        <div className="lg:col-span-3 space-y-6">
          {/* Search Bar */}
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-zinc-600 group-focus-within:text-emerald-500 transition-colors" />
            <Input
              placeholder="Search problems by name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-zinc-900 border-zinc-800 pl-12 h-14 rounded-2xl focus:ring-emerald-500/50 focus:border-emerald-500 transition-all text-zinc-300"
            />
          </div>

          <div className="bg-[#0f0f0f] border border-zinc-800/50 rounded-3xl overflow-hidden shadow-xl">
            {isLoading ? (
              <div className="p-12 flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                  <div className="h-10 w-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                  <p className="text-zinc-500 text-sm font-medium">Loading challenges...</p>
                </div>
              </div>
            ) : filteredProblems.length > 0 ? (
              <div className="divide-y divide-zinc-800/50">
                {filteredProblems.map((problem) => (
                  <Link
                    key={problem.id}
                    href={`/problems/${problem.id}`}
                    className="flex items-center justify-between p-5 hover:bg-zinc-800/30 transition-all group"
                  >
                    <div className="flex items-center gap-6">
                      <div>
                        <h4 className="text-white font-semibold group-hover:text-emerald-400 transition-colors">
                          {problem.title}
                        </h4>
                        <div className="flex gap-3 mt-1.5">
                          {problem.topics?.map(topic => (
                            <span key={topic.id} className="text-[10px] text-zinc-500 font-medium">#{topic.name}</span>
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
                      <ChevronRight className="h-5 w-5 text-zinc-800 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-20 text-center">
                <BarChart3 className="h-12 w-12 text-zinc-800 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-white mb-1">No problems found</h3>
                <p className="text-zinc-500">Try adjusting your filters or search query.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

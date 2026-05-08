"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyEmailApiAuthVerifyGet } from "@/lib/api-client";
import { Button, buttonVariants } from "@/components/ui/button";
import { Loader2, CheckCircle2, XCircle, Mail, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "react-hot-toast";
import Link from "next/link";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email...");

  useEffect(() => {
    async function verify() {
      if (!token) {
        setStatus("error");
        setMessage("Invalid or missing verification token.");
        return;
      }

      try {
        const res = await verifyEmailApiAuthVerifyGet({
          query: { token }
        });

        if (res.error) {
          setStatus("error");
          setMessage(res.error.detail?.[0]?.msg || "Verification failed. The link may have expired.");
        } else {
          setStatus("success");
          setMessage("Email verified successfully! You can now sign in.");
          toast.success("Email verified!");
          // Optional: redirect after some delay
          setTimeout(() => router.push("/auth"), 3000);
        }
      } catch (err) {
        setStatus("error");
        setMessage("An unexpected error occurred.");
      }
    }

    verify();
  }, [token, router]);

  return (
    <div className="flex min-h-screen w-full bg-[#050505] relative overflow-hidden flex-col items-center justify-center p-6">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-full">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-zinc-900/40 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md bg-[#0f0f0f] border border-zinc-800/50 p-8 rounded-3xl shadow-2xl backdrop-blur-sm text-center">
        <div className="flex flex-col items-center gap-6">
          <div className={`p-4 rounded-2xl ${
            status === "loading" ? "bg-zinc-800 text-zinc-400" :
            status === "success" ? "bg-emerald-600/20 text-emerald-500" :
            "bg-rose-600/20 text-rose-500"
          }`}>
            {status === "loading" && <Loader2 className="h-10 w-10 animate-spin" />}
            {status === "success" && <CheckCircle2 className="h-10 w-10" />}
            {status === "error" && <XCircle className="h-10 w-10" />}
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-white">
              {status === "loading" ? "Verifying..." : 
               status === "success" ? "Verified!" : 
               "Verification Failed"}
            </h1>
            <p className="text-zinc-400 text-sm leading-relaxed">
              {message}
            </p>
          </div>

          {status === "success" && (
            <Link 
              href="/auth" 
              className={cn(buttonVariants({ className: "w-full bg-emerald-600 hover:bg-emerald-700 text-white h-11 rounded-xl font-bold mt-4" }))}
            >
              Sign In Now
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          )}

          {status === "error" && (
            <Link 
              href="/auth" 
              className={cn(buttonVariants({ variant: "outline", className: "w-full bg-transparent border-zinc-800 hover:bg-zinc-900 rounded-xl h-11 text-zinc-300 mt-4" }))}
            >
              Back to Sign In
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen w-full bg-[#050505] flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-emerald-500 animate-spin" />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}

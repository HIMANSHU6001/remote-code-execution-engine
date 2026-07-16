"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Mail, Lock, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "react-hot-toast";
import Image from "next/image";
import Link from "next/link";

/** Thin rule with small T-joint ticks where it meets the container edges. */
function SectionDivider() {
  return (
    <div className="relative w-full h-px bg-border-primary">
      <div className="absolute -left-px top-1/2 -translate-y-1/2 flex items-center">
        <div className="w-px h-3 bg-text-secondary" />
        <div className="w-2 h-px bg-text-secondary" />
      </div>
      <div className="absolute -right-px top-1/2 -translate-y-1/2 flex items-center">
        <div className="w-2 h-px bg-text-secondary" />
        <div className="w-px h-3 bg-text-secondary" />
      </div>
    </div>
  );
}

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { signup, loginWithGoogle, loginWithGithub } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await signup({ email, password });
      toast.success("Check your email for verification code", {
        duration: 6000,
      });
      router.push("/auth/signin");
    } catch (err: any) {
      setError(err.message || "An error occurred");
      toast.error(err.message || "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center px-4 py-12 font-sans">
      <div className="corner-accents relative w-full max-w-[440px] border border-border-dark/50 bg-background">
        {/* Main content */}
        <div className="px-8 sm:px-12 py-10 flex flex-col items-center text-center ">
          <div className="w-20 h-20 flex items-center justify-center">
            <img
              src="/codespace_logo.svg"
              alt="CodeSpace Logo"
              width={72}
              height={72}
              className="hidden dark:block"
            />

            <img
              src="/codespace_logo_light.svg"
              alt="CodeSpace Logo"
              width={72}
              height={72}
              className="block dark:hidden"
            />
          </div>

          <span className="relative inline-block px-2 mb-3">
            <span className="absolute inset-0 top-[6%] bottom-[10%] bg-brand-200 -z-10" />
            <span className="text-3xl sm:text-4xl font-bold tracking-tight text-text-primary">
              CodeSpace
            </span>
          </span>

          <p className="text-text-tertiary text-[14px] max-w-[280px] leading-relaxed mb-8">
            Level up, one problem at a time.
          </p>

          <form onSubmit={handleSubmit} className="w-full space-y-5 text-left">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-sm text-center">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[13px] font-semibold text-text-secondary">
                  Email address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="bg-surface-primary border shadow-none pl-10 h-[46px] focus-visible:ring-1 focus-visible:ring-brand-500 rounded-none text-text-primary placeholder:text-text-muted transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-semibold text-text-secondary">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                  <Input
                    type="password"
                    placeholder="Create a strong password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="bg-surface-primary border shadow-none pl-10 h-[46px] focus-visible:ring-1 focus-visible:ring-brand-500 rounded-none text-text-primary placeholder:text-text-muted transition-colors"
                  />
                </div>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full cursor-pointer bg-brand-600 hover:bg-brand-700 text-white h-[46px] rounded-none font-semibold transition-colors mt-2"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <span>Create account</span>
                </>
              )}
            </Button>
          </form>



          <div className="my-8 w-full flex items-center gap-3">
            <div className="h-px flex-1 bg-border-primary" />
            <span className="text-[11px] uppercase text-text-muted font-semibold tracking-wider">
              Or continue with
            </span>
            <div className="h-px flex-1 bg-border-primary" />
          </div>

          <div className="grid grid-cols-2 gap-3 w-full">
            <Button
              type="button"
              variant="outline"
              onClick={async () => {
                setError(null);
                setIsLoading(true);
                try {
                  await loginWithGithub();
                  router.push("/problems");
                } catch (err: any) {
                  setError(err.message || "GitHub login failed");
                } finally {
                  setIsLoading(false);
                }
              }}
              disabled={isLoading}
              className="border border-border-primary bg-transparent hover:bg-hover-bg rounded-none h-11 text-text-secondary font-semibold hover-langfuse"
            >
              <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M12 .297c-6.63 0-12 5.373-12 12 0 5.302 3.438 9.8 8.205 11.385.6.11 0.82-.264.82-.59c0-.288-.01-1.04-.015-2.04-3.337.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77 0 1.235 1.07 1.235 2.381 0 4.603-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.294 0 .324.214.704.822.592C18.566 22.092 22 17.592 22 12.297c0-6.627-5.373-12-12-12"
                />
              </svg>
              GitHub
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={async () => {
                setError(null);
                setIsLoading(true);
                try {
                  await loginWithGoogle();
                  router.push("/problems");
                } catch (err: any) {
                  setError(err.message || "Google login failed");
                } finally {
                  setIsLoading(false);
                }
              }}
              disabled={isLoading}
              className="border border-border-primary bg-transparent hover:bg-hover-bg rounded-none h-11 text-text-secondary font-semibold hover-langfuse"
            >
              <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Google
            </Button>
          </div>
        </div>

        <SectionDivider />

        {/* Footer */}
        <div className="px-6 py-5 text-center">
          <Link
            href="/auth/signin"
            className="text-[13px] text-text-tertiary transition-colors"
          >
            Already have an account?{" "}
            <span className="text-text-primary hover:text-emerald-500 font-medium underline underline-offset-4 decoration-border-dark">
              Sign in
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
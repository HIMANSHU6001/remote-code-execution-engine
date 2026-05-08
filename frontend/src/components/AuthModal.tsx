"use client";

import React, { useState } from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const AuthModal = () => {
  const [mode, setMode] = useState<"signin" | "register">("signin");

  return (
    <Dialog>
      <DialogTrigger 
        render={
          <Button variant="outline" size="sm" className="border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300">
            Sign In
          </Button>
        }
      />

      <DialogContent className="sm:max-w-[425px] bg-[#121212] border-zinc-800 text-zinc-300">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-white">
            {mode === "signin" ? "Sign In" : "Create Account"}
          </DialogTitle>
          <DialogDescription className="text-zinc-500">
            {mode === "signin" 
              ? "Welcome back to CodeSpace. Please enter your details." 
              : "Join CodeSpace to start solving problems and tracking your progress."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-zinc-400">Email</label>
            <Input 
              type="email" 
              placeholder="name@example.com" 
              className="bg-black border-zinc-800 focus:ring-emerald-500"
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-zinc-400">Password</label>
            <Input 
              type="password" 
              placeholder="••••••••" 
              className="bg-black border-zinc-800 focus:ring-emerald-500"
            />
          </div>
          <Button className="bg-emerald-600 hover:bg-emerald-700 text-white mt-2">
            {mode === "signin" ? "Sign In" : "Register"}
          </Button>
        </div>
        <div className="flex justify-center text-sm">
          <button 
            onClick={() => setMode(mode === "signin" ? "register" : "signin")}
            className="text-emerald-500 hover:underline"
          >
            {mode === "signin" ? "Don't have an account? Register" : "Already have an account? Sign In"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default AuthModal;

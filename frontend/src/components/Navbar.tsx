"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LogOut, User, Menu, X, Sun, Moon } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";
import Image from "next/image";

const Navbar = () => {
  const { isAuthenticated, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  return (
    <nav
      className="sticky top-0 z-50 w-full border-b-2 border-border-dark backdrop-blur-xl"
      style={{ background: "var(--navbar-bg)" }}
    >
      <div className="container mx-auto px-4 flex h-14 items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/problems" className="flex items-center gap-2 group">
            <Image
              src="/codespace_logo.svg"
              alt="CodeSpace Logo"
              width={32}
              height={32}
              className="group-hover:scale-110 transition-transform hidden dark:block"
            />
            <Image
              src="/codespace_logo_light.svg"
              alt="CodeSpace Logo"
              width={32}
              height={32}
              className="group-hover:scale-110 transition-transform block dark:hidden"
            />
            <span className="font-bold text-lg tracking-tight text-text-primary">CodeSpace</span>
          </Link>
        </div>

        <div className="flex items-center gap-3 ">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="relative w-8 h-8 flex items-center justify-center bg-transparent cursor-pointer hover-langfuse"
            aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
          >
            <Sun
              className={cn(
                "h-[18px] w-[18px] absolute transition-all duration-300",
                isDark
                  ? "rotate-0 scale-100 text-amber-400"
                  : "rotate-90 scale-0 text-amber-400"
              )}
            />
            <Moon
              className={cn(
                "h-[18px] w-[18px] absolute transition-all duration-300",
                isDark
                  ? "-rotate-90 scale-0 text-text-muted"
                  : "rotate-0 scale-100 text-text-muted"
              )}
            />
          </button>

          <div className="flex items-center gap-4 ml-2">
            <button
              onClick={logout}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity group p-1.5 hover-langfuse cursor-pointer"
            >
              <LogOut className="h-[18px] w-[18px] text-text-secondary group-hover:text-text-primary transition-colors" />
              <span className="hidden sm:inline text-[15px] font-medium tracking-tight text-xs">Logout</span>
            </button>
          </div>


          {/* Mobile Toggle */}
          <button
            className="md:hidden text-text-tertiary"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

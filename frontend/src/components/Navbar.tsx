"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LogOut, User, Menu, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import Image from "next/image";

const Navbar = () => {
  const { isAuthenticated, logout } = useAuth();
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const navLinks = [
    { name: "Problems", href: "/problems" },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-[#0f0f0f]/80 backdrop-blur-xl supports-backdrop-filter:bg-[#0f0f0f]/60">
      <div className="container mx-auto px-4 flex h-14 items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/problems" className="flex items-center gap-2 group">
            <Image
              src="/codespace_logo.svg"
              alt="CodeSpace Logo"
              width={32}
              height={32}
              className="group-hover:scale-110 transition-transform"
            />
            <span className="font-bold text-lg tracking-tight text-white">CodeSpace</span>
          </Link>

          {/* Desktop Links */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-emerald-500",
                  pathname === link.href ? "text-emerald-500" : "text-zinc-400"
                )}
              >
                {link.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-zinc-400 hover:text-red-400 gap-2 font-medium"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/auth">
                <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white">
                  Sign In
                </Button>
              </Link>
              <Link href="/auth">
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg px-4">
                  Join Now
                </Button>
              </Link>
            </div>
          )}

          {/* Mobile Toggle */}
          <button
            className="md:hidden text-zinc-400"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-[#0f0f0f] border-b border-zinc-800 p-4 space-y-4 animate-in slide-in-from-top duration-200">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className={cn(
                "block text-lg font-medium transition-colors",
                pathname === link.href ? "text-emerald-500" : "text-zinc-400"
              )}
            >
              {link.name}
            </Link>
          ))}
          {!isAuthenticated && (
            <div className="pt-4 border-t border-zinc-800 flex flex-col gap-3">
              <Link href="/auth" onClick={() => setIsMobileMenuOpen(false)}>
                <Button variant="outline" className="w-full border-zinc-800 text-zinc-300">Sign In</Button>
              </Link>
              <Link href="/auth" onClick={() => setIsMobileMenuOpen(false)}>
                <Button className="w-full bg-emerald-600 text-white">Join Now</Button>
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};

export default Navbar;

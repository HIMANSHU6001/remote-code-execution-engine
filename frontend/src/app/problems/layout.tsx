import Navbar from "@/components/Navbar";

export default function ProblemsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col h-screen w-full bg-surface-primary">
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}

import ChatInterface from '@/components/ChatInterface';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-slate-50">
      <header className="sticky top-0 z-10 flex h-16 items-center border-b border-slate-200 bg-white/80 px-4 md:px-6 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 shadow-md">
            <span className="text-white text-lg">⚡</span>
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-800">
            InsightX <span className="font-medium text-slate-400 mx-1">/</span> <span className="font-medium text-indigo-600">BRAIN-DS</span>
          </span>
        </div>
      </header>
      <div className="flex-1 relative max-h-[calc(100vh-4rem)]">
        <ChatInterface />
      </div>
    </main>
  );
}

import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-gray-50 dark:bg-black">
      <main className="flex flex-col items-center gap-8 text-center px-6">
        <h1 className="text-5xl font-bold tracking-tight">
          Naql<span className="text-blue-500">.ai</span>
        </h1>
        <p className="max-w-lg text-lg text-gray-600 dark:text-gray-400">
          Next-generation autonomous logistics platform for Egypt.
          AI-powered dispatching, real-time fleet tracking, and automated
          Cartas pricing.
        </p>
        <div className="flex gap-4">
          <Link
            href="/dashboard"
            className="rounded-full bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Open Dashboard
          </Link>
          <a
            href="https://github.com/ibrahimhady131-cloud/BIG-DEV"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-gray-300 px-6 py-3 text-sm font-medium transition-colors hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-900"
          >
            View Source
          </a>
        </div>
      </main>
    </div>
  );
}

export function LoadingFallback() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600 dark:text-gray-400">Loading ManeYantra...</p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
          API: {import.meta.env.VITE_API_URL || "http://localhost:8000"}
        </p>
      </div>
    </div>
  );
}

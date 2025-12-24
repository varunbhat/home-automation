import { useDeviceEvents } from "../hooks/useDeviceEvents";
import { Activity, Wifi, WifiOff, Trash2 } from "lucide-react";

export function EventLog() {
  const { events, connected, connect, disconnect, clearEvents } = useDeviceEvents({
    autoConnect: false, // Disabled to prevent duplicate SSE connections
  });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Live Events
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            ({events.length})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearEvents}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
            title="Clear events"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={connected ? disconnect : connect}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
              connected
                ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                : "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300"
            }`}
          >
            {connected ? (
              <>
                <Wifi className="w-4 h-4" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                Disconnected
              </>
            )}
          </button>
        </div>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
            No events yet. {connected ? "Waiting for updates..." : "Connect to see events."}
          </div>
        ) : (
          events.map((event, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg border-l-4 ${
                event.type === "state"
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                  : event.type === "error"
                  ? "border-red-500 bg-red-50 dark:bg-red-900/20"
                  : event.type === "discovery"
                  ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                  : event.type === "heartbeat"
                  ? "border-gray-500 bg-gray-50 dark:bg-gray-900/20 opacity-50"
                  : "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold uppercase text-gray-700 dark:text-gray-300">
                      {event.type}
                    </span>
                    {event.device_id && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {event.device_id}
                      </span>
                    )}
                  </div>
                  {event.data ? (
                    <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  ) : null}
                </div>
                <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap ml-2">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

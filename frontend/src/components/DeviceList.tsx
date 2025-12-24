import { useEffect, useState } from "react";
import { RefreshCw, Filter } from "lucide-react";
import { api } from "../lib/api";
import type { Device, DeviceType } from "../types/api";
import { DeviceCard } from "./DeviceCard";
import { useDeviceEvents } from "../hooks/useDeviceEvents";

export function DeviceList() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    type?: DeviceType;
    room?: string;
    online?: boolean;
  }>({});

  // Real-time updates via SSE with exponential backoff
  const { connected, reconnectAttempts, error: sseError } = useDeviceEvents({
    autoConnect: true,
    maxReconnectAttempts: 5,
    initialReconnectDelay: 1000,
    onEvent: (event) => {
      if (event.type === "state" && event.device_id) {
        console.log("[DeviceList] Updating device state:", event.device_id, event.data);
        // Update device state in real-time
        setDevices((prev) =>
          prev.map((d) =>
            d.info.id === event.device_id && event.data
              ? { ...d, state: event.data as Device["state"] }
              : d
          )
        );
      }
    },
  });

  const loadDevices = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log("Loading devices from API...");
      const response = await api.listDevices(filter);
      console.log("Loaded devices:", response.devices.length);
      setDevices(response.devices);
    } catch (error) {
      console.error("Failed to load devices:", error);
      setError(error instanceof Error ? error.message : "Failed to load devices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();
  }, [filter]);

  const rooms = [...new Set(devices.map((d) => d.info.room).filter(Boolean))];
  const types = [...new Set(devices.map((d) => d.info.type))];

  return (
    <div className="space-y-6">
      {/* Header & Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Devices
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {devices.length} devices • {connected ? "🟢 Live" : reconnectAttempts > 0 ? `🟡 Reconnecting (${reconnectAttempts}/5)` : "🔴 Offline"}
              {sseError && !connected && reconnectAttempts === 0 && ` - ${sseError}`}
            </p>
          </div>
          <button
            onClick={loadDevices}
            disabled={loading}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <Filter className="w-4 h-4" />
            <span>Filter:</span>
          </div>

          <select
            value={filter.type || ""}
            onChange={(e) =>
              setFilter({ ...filter, type: (e.target.value as DeviceType) || undefined })
            }
            className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm border-0"
          >
            <option value="">All Types</option>
            {types.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>

          <select
            value={filter.room || ""}
            onChange={(e) =>
              setFilter({ ...filter, room: e.target.value || undefined })
            }
            className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm border-0"
          >
            <option value="">All Rooms</option>
            {rooms.map((room) => (
              <option key={room} value={room}>
                {room}
              </option>
            ))}
          </select>

          <select
            value={filter.online === undefined ? "" : filter.online ? "online" : "offline"}
            onChange={(e) =>
              setFilter({
                ...filter,
                online:
                  e.target.value === "" ? undefined : e.target.value === "online",
              })
            }
            className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm border-0"
          >
            <option value="">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>

          {(filter.type || filter.room || filter.online !== undefined) && (
            <button
              onClick={() => setFilter({})}
              className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Device Grid */}
      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <p className="text-red-600 dark:text-red-400 font-semibold mb-2">Failed to load devices</p>
          <p className="text-sm text-red-500 dark:text-red-300 mb-4">{error}</p>
          <button
            onClick={loadDevices}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
          >
            Retry
          </button>
        </div>
      ) : loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : devices.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No devices found
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {devices.map((device) => (
            <DeviceCard
              key={device.info.id}
              device={device}
              onUpdate={(updated) =>
                setDevices((prev) =>
                  prev.map((d) => (d.info.id === updated.info.id ? updated : d))
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

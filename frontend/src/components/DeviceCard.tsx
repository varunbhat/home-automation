import { useState } from "react";
import { Power, Lightbulb, Plug, Camera, Lock, Thermometer, Loader2 } from "lucide-react";
import type { Device, DeviceCommand } from "../types/api";
import { api } from "../lib/api";

interface DeviceCardProps {
  device: Device;
  onUpdate?: (device: Device) => void;
}

const DEVICE_ICONS = {
  light: Lightbulb,
  plug: Plug,
  camera: Camera,
  lock: Lock,
  thermostat: Thermometer,
  switch: Power,
  sensor: Thermometer,
  motion_sensor: Thermometer,
  door_sensor: Lock,
  unknown: Power,
};

export function DeviceCard({ device, onUpdate }: DeviceCardProps) {
  const [loading, setLoading] = useState(false);
  const [localState, setLocalState] = useState(device.state);

  const Icon = DEVICE_ICONS[device.info.type] || Power;
  const isOnline = localState.online;
  const isOn = localState.on ?? false;

  const executeCommand = async (command: DeviceCommand) => {
    setLoading(true);
    try {
      const result = await api.executeCommand(device.info.id, command);
      if (result.success && result.state) {
        setLocalState(result.state);
        if (onUpdate) {
          onUpdate({ ...device, state: result.state });
        }
      }
    } catch (error) {
      console.error("Failed to execute command:", error);
    } finally {
      setLoading(false);
    }
  };

  const togglePower = () => {
    executeCommand({
      command: isOn ? "turn_off" : "turn_on",
    });
  };

  const setBrightness = (brightness: number) => {
    executeCommand({
      command: "set_brightness",
      params: { brightness },
    });
  };

  const hasBrightness = device.info.capabilities.includes("brightness");
  const brightness = localState.brightness ?? 100;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 transition-all ${
        isOnline ? "" : "opacity-50"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`p-3 rounded-lg ${
              isOn
                ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
            }`}
          >
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {device.info.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {device.info.room || device.info.type}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {loading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
          <div
            className={`w-2 h-2 rounded-full ${
              isOnline ? "bg-green-500" : "bg-red-500"
            }`}
          />
        </div>
      </div>

      {/* Controls */}
      {device.info.capabilities.includes("on_off") && (
        <div className="space-y-3">
          <button
            onClick={togglePower}
            disabled={!isOnline || loading}
            className={`w-full py-2 px-4 rounded-lg font-medium transition-colors ${
              isOn
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isOn ? "Turn Off" : "Turn On"}
          </button>

          {hasBrightness && isOn && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                <span>Brightness</span>
                <span>{brightness}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                disabled={!isOnline || loading}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
              />
            </div>
          )}
        </div>
      )}

      {/* Device Info */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
          {device.info.manufacturer && (
            <div>
              <span className="font-medium">Brand:</span> {device.info.manufacturer}
            </div>
          )}
          {device.info.model && (
            <div>
              <span className="font-medium">Model:</span> {device.info.model}
            </div>
          )}
          {localState.battery !== undefined && (
            <div>
              <span className="font-medium">Battery:</span> {localState.battery}%
            </div>
          )}
          {localState.temperature !== undefined && localState.temperature !== null && (
            <div>
              <span className="font-medium">Temp:</span> {localState.temperature.toFixed(1)}°C
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

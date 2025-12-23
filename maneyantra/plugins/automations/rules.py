"""Simple rule engine plugin for automations."""

import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

from maneyantra.core.plugin import PluginBase, PluginMetadata, PluginType
from maneyantra.core.rabbitmq_bus import RabbitMQEventBus


class RuleEnginePlugin(PluginBase):
    """
    Simple rule engine for home automation.

    Rules are defined in YAML files with the format:
    ```yaml
    rules:
      - id: turn_on_light_on_motion
        name: Turn on lights when motion detected
        trigger:
          topic: device/+/state
          condition:
            field: motion
            operator: eq
            value: true
        actions:
          - command:
              topic: device/living_room_light/command
              payload:
                command: turn_on
    ```
    """

    def __init__(
        self,
        plugin_id: str,
        config: Dict,
        event_bus: RabbitMQEventBus,
    ):
        metadata = PluginMetadata(
            name="Rule Engine",
            version="0.1.0",
            plugin_type=PluginType.AUTOMATION,
            description="Simple rule-based automation engine",
            capabilities=["rules", "conditions", "actions"],
        )

        super().__init__(plugin_id, metadata, config, event_bus)

        self.rules: List[Dict] = []
        self._subscriptions = []

    async def initialize(self) -> None:
        """Initialize the rule engine."""
        # Load rules from config
        rules_dir = self.get_config("rules_dir", "./config/rules")
        await self._load_rules(rules_dir)

        self._logger.info(f"Loaded {len(self.rules)} rules")

    async def _load_rules(self, rules_dir: str) -> None:
        """Load rules from directory."""
        rules_path = Path(rules_dir)

        if not rules_path.exists():
            self._logger.warning(f"Rules directory not found: {rules_dir}")
            return

        # Load all YAML files in rules directory
        for rule_file in rules_path.glob("*.yaml"):
            try:
                with open(rule_file) as f:
                    data = yaml.safe_load(f)

                rules = data.get("rules", [])
                self.rules.extend(rules)

                self._logger.info(f"Loaded {len(rules)} rules from {rule_file.name}")

            except Exception as e:
                self._logger.error(f"Error loading rules from {rule_file}: {e}")

    async def start(self) -> None:
        """Start the rule engine."""
        # Subscribe to topics mentioned in rules
        for rule in self.rules:
            trigger = rule.get("trigger", {})
            topic = trigger.get("topic")

            if topic:
                await self.event_bus.subscribe(
                    topic,
                    lambda t, p, r=rule: asyncio.create_task(self._handle_trigger(r, t, p)),
                )

        self._logger.info("Rule engine started")

    async def stop(self) -> None:
        """Stop the rule engine."""
        self._logger.info("Rule engine stopped")

    async def _handle_trigger(self, rule: Dict, topic: str, payload: Dict) -> None:
        """Handle a rule trigger."""
        try:
            rule_id = rule.get("id", "unknown")
            self._logger.debug(f"Evaluating rule: {rule_id}")

            # Check trigger condition
            trigger = rule.get("trigger", {})
            condition = trigger.get("condition")

            if condition and not self._evaluate_condition(condition, payload):
                return

            # Trigger matched, execute actions
            self._logger.info(f"Rule triggered: {rule.get('name', rule_id)}")

            await self.event_bus.publish(
                f"automation.{rule_id}.trigger",
                {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name"),
                    "trigger_topic": topic,
                    "trigger_payload": payload,
                },
            )

            # Execute actions
            actions = rule.get("actions", [])
            for action in actions:
                await self._execute_action(action, payload)

        except Exception as e:
            self._logger.error(f"Error handling rule trigger: {e}", exc_info=True)

    def _evaluate_condition(self, condition: Dict, payload: Dict) -> bool:
        """Evaluate a condition against payload."""
        field = condition.get("field")
        operator = condition.get("operator", "eq")
        value = condition.get("value")

        # Extract field value from payload (supports nested fields with dot notation)
        current = payload
        for part in field.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return False

        # Evaluate operator
        if operator == "eq":
            return current == value
        elif operator == "ne":
            return current != value
        elif operator == "gt":
            return current > value
        elif operator == "gte":
            return current >= value
        elif operator == "lt":
            return current < value
        elif operator == "lte":
            return current <= value
        elif operator == "in":
            return current in value
        elif operator == "contains":
            return value in current
        else:
            self._logger.warning(f"Unknown operator: {operator}")
            return False

    async def _execute_action(self, action: Dict, trigger_payload: Dict) -> None:
        """Execute an action."""
        try:
            # Command action - publish to MQTT
            if "command" in action:
                command = action["command"]
                topic = command.get("topic")
                payload = command.get("payload", {})

                # Template substitution (simple)
                payload = self._substitute_variables(payload, trigger_payload)

                await self.event_bus.publish(topic, payload)

                self._logger.debug(f"Executed command on {topic}")

            # Delay action
            elif "delay" in action:
                delay_seconds = action["delay"]
                await asyncio.sleep(delay_seconds)

            else:
                self._logger.warning(f"Unknown action type: {action}")

        except Exception as e:
            self._logger.error(f"Error executing action: {e}", exc_info=True)

    def _substitute_variables(self, payload: Any, context: Dict) -> Any:
        """Simple variable substitution in payload."""
        if isinstance(payload, dict):
            return {k: self._substitute_variables(v, context) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self._substitute_variables(item, context) for item in payload]
        elif isinstance(payload, str) and payload.startswith("$"):
            # Simple variable substitution: $field.subfield
            var_path = payload[1:].split(".")
            value = context
            for part in var_path:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return payload
            return value
        else:
            return payload

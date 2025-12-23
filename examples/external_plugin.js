#!/usr/bin/env node

/**
 * Example external plugin in Node.js using RabbitMQ
 *
 * This demonstrates how to create a plugin in ANY language
 * by connecting directly to the RabbitMQ broker using AMQP.
 *
 * Install: npm install amqplib
 * Run: node external_plugin.js
 */

const amqp = require('amqplib');

// Configuration
const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672';
const EXCHANGE_NAME = 'maneyantra';
const PLUGIN_ID = 'external_nodejs_plugin';

// State
let heartbeatCounter = 0;
let channel = null;
let connection = null;

async function main() {
  try {
    console.log('🏠 ManeYantra External Plugin (Node.js)');
    console.log(`📡 Connecting to RabbitMQ at ${RABBITMQ_URL}...`);

    // Connect to RabbitMQ
    connection = await amqp.connect(RABBITMQ_URL);
    channel = await connection.createChannel();

    // Declare the topic exchange
    await channel.assertExchange(EXCHANGE_NAME, 'topic', {
      durable: true,
    });

    // Create a queue for this plugin
    const { queue } = await channel.assertQueue('', {
      exclusive: true, // Delete when connection closes
    });

    console.log(`✅ Connected to RabbitMQ`);

    // Subscribe to topics
    await subscribe(queue, 'system.#', handleSystemEvent);
    await subscribe(queue, 'device.*.state', handleDeviceState);
    await subscribe(queue, `plugin.${PLUGIN_ID}.command`, handlePluginCommand);

    console.log('📡 Subscribed to routing keys');

    // Publish plugin status
    await publishPluginStatus('running', { message: 'Plugin connected' });

    // Start heartbeat
    setInterval(async () => {
      heartbeatCounter++;
      await publishHeartbeat();
    }, 30000); // Every 30 seconds

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

async function subscribe(queue, routingKey, handler) {
  const fullRoutingKey = `${EXCHANGE_NAME}.${routingKey}`;

  await channel.bindQueue(queue, EXCHANGE_NAME, fullRoutingKey);

  await channel.consume(queue, async (msg) => {
    if (msg) {
      try {
        const payload = JSON.parse(msg.content.toString());
        const routingKey = msg.fields.routingKey.replace(`${EXCHANGE_NAME}.`, '');

        await handler(routingKey, payload);

      } catch (error) {
        console.error('Error processing message:', error);
      }
    }
  }, { noAck: true });
}

async function handleSystemEvent(routingKey, payload) {
  const eventType = routingKey.split('.').pop();
  console.log(`🔔 System event: ${eventType}`);

  if (eventType === 'stop') {
    console.log('⏸️  System stopping, shutting down plugin...');
    await publishPluginStatus('stopped');
    await channel.close();
    await connection.close();
    process.exit(0);
  }
}

async function handleDeviceState(routingKey, payload) {
  const parts = routingKey.split('.');
  const deviceId = parts[parts.length - 2];
  const state = payload.state || {};

  if (state.motion === true) {
    console.log(`🚶 Motion detected on device: ${deviceId}`);

    // Example: Publish a notification
    await publish('service.notify', {
      title: 'Motion Detected',
      message: `Motion detected on ${deviceId}`,
      priority: 'normal',
    });
  }
}

async function handlePluginCommand(routingKey, payload) {
  const command = payload.command;
  console.log(`⚡ Command received: ${command}`);

  if (command === 'status') {
    await publishPluginStatus('running', {
      heartbeat_counter: heartbeatCounter,
      uptime: process.uptime(),
    });
  }
}

async function publish(routingKey, payload) {
  const message = {
    timestamp: new Date().toISOString(),
    ...payload,
  };

  const fullRoutingKey = `${EXCHANGE_NAME}.${routingKey}`;

  await channel.publish(
    EXCHANGE_NAME,
    fullRoutingKey,
    Buffer.from(JSON.stringify(message)),
    {
      persistent: true,
      contentType: 'application/json',
    }
  );
}

async function publishPluginStatus(status, details = {}) {
  await publish(`plugin.${PLUGIN_ID}.status`, {
    status,
    details,
  });
}

async function publishHeartbeat() {
  await publish(`plugin.${PLUGIN_ID}.heartbeat`, {
    counter: heartbeatCounter,
    status: 'healthy',
    memory: process.memoryUsage(),
    uptime: process.uptime(),
  });

  console.log(`💓 Heartbeat #${heartbeatCounter}`);
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n⚠️  Shutting down...');
  await publishPluginStatus('stopped');
  if (channel) await channel.close();
  if (connection) await connection.close();
  process.exit(0);
});

// Start
main();

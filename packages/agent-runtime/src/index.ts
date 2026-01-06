export { AgentWrapper } from './agent-wrapper.js';
export { IPCChannel } from './ipc-channel.js';
export * from './agents/index.js';
export * from './types.js';

// Main entry point when running as a process
import { AgentWrapper } from './agent-wrapper.js';

const agentType = process.env.AGENT_TYPE;
const agentId = process.env.AGENT_ID;
const backendUrl = process.env.BACKEND_URL || 'ws://localhost:8000';

if (agentType && agentId) {
  const wrapper = new AgentWrapper({
    agentType,
    agentId,
    backendUrl,
  });

  wrapper.start().catch((err) => {
    console.error('Failed to start agent:', err);
    process.exit(1);
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    console.log('Received SIGTERM, shutting down...');
    await wrapper.stop();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    console.log('Received SIGINT, shutting down...');
    await wrapper.stop();
    process.exit(0);
  });
}

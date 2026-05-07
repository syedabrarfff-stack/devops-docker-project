require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const aiRouter = require('./routes/ai-router');
const agentsRouter = require('./routes/agents');
const connectorsRouter = require('./routes/connectors');
const workflowsRouter = require('./routes/workflows');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));
app.use(express.json({ limit: '10mb' }));

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'operational',
    system: 'JARVIS',
    version: '1.0.0',
    uptime: Math.floor(process.uptime()),
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
  });
});

// System stats
app.get('/api/stats', (req, res) => {
  const { MODELS } = require('./config/models');
  const { CONNECTORS, AGENT_TEAMS } = require('./config/connectors');

  const configuredModels = Object.values(MODELS).filter(m => process.env[m.envKey]).length;
  const connectedServices = CONNECTORS.filter(c => c.status === 'connected').length;
  const activeAgents = AGENT_TEAMS.filter(t => t.status === 'active').reduce((s, t) => s + t.agents, 0);

  res.json({
    models: { total: Object.keys(MODELS).length, configured: configuredModels },
    connectors: { total: CONNECTORS.length, connected: connectedServices },
    agents: {
      teams: AGENT_TEAMS.length,
      active: AGENT_TEAMS.filter(t => t.status === 'active').length,
      totalAgents: AGENT_TEAMS.reduce((s, t) => s + t.agents, 0),
      activeAgents,
    },
    system: {
      uptime: Math.floor(process.uptime()),
      memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
      node: process.version,
    },
  });
});

app.use('/api', aiRouter);
app.use('/api/agents', agentsRouter);
app.use('/api/connectors', connectorsRouter);
app.use('/api/workflows', workflowsRouter);

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error', message: err.message });
});

app.listen(PORT, () => {
  console.log(`\n⚡ JARVIS Backend — Online`);
  console.log(`🌐 Port: ${PORT}`);
  console.log(`⚡ Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 Health: http://localhost:${PORT}/health\n`);
});

module.exports = app;

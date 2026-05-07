const express = require('express');
const router = express.Router();
const { CONNECTORS } = require('../config/connectors');

// GET /api/connectors — list all connectors with status
router.get('/', (req, res) => {
  const connected = CONNECTORS.filter(c => c.status === 'connected');
  const disconnected = CONNECTORS.filter(c => c.status === 'disconnected');

  res.json({
    connectors: CONNECTORS,
    stats: {
      total: CONNECTORS.length,
      connected: connected.length,
      disconnected: disconnected.length,
      totalTools: connected.reduce((sum, c) => sum + c.tools, 0),
    },
    categories: [...new Set(CONNECTORS.map(c => c.category))],
  });
});

// GET /api/connectors/:id — get specific connector
router.get('/:id', (req, res) => {
  const connector = CONNECTORS.find(c => c.id === req.params.id);
  if (!connector) {
    return res.status(404).json({ error: 'Connector not found' });
  }
  res.json(connector);
});

module.exports = router;

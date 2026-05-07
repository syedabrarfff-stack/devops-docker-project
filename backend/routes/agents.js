const express = require('express');
const router = express.Router();
const { AGENT_TEAMS } = require('../config/connectors');

// Runtime task tracking
const taskLog = [];

// GET /api/agents — list all agent teams
router.get('/', (req, res) => {
  const teams = AGENT_TEAMS.map(t => ({
    ...t,
    tasks: taskLog.filter(l => l.teamId === t.id && l.status !== 'done').length,
  }));
  res.json({
    teams,
    totalAgents: AGENT_TEAMS.reduce((sum, t) => sum + t.agents, 0),
    activeTeams: AGENT_TEAMS.filter(t => t.status === 'active').length,
  });
});

// POST /api/agents/dispatch — dispatch a task to an agent team
router.post('/dispatch', (req, res) => {
  const { teamId, task, priority = 'normal' } = req.body;
  if (!teamId || !task) {
    return res.status(400).json({ error: 'teamId and task are required' });
  }

  const team = AGENT_TEAMS.find(t => t.id === teamId);
  if (!team) {
    return res.status(404).json({ error: `Team ${teamId} not found` });
  }

  const taskEntry = {
    id: `task_${Date.now()}`,
    teamId,
    teamName: team.name,
    task,
    priority,
    status: 'queued',
    createdAt: new Date().toISOString(),
  };
  taskLog.push(taskEntry);

  // Simulate task processing
  setTimeout(() => {
    taskEntry.status = 'in_progress';
  }, 500);
  setTimeout(() => {
    taskEntry.status = 'done';
    taskEntry.completedAt = new Date().toISOString();
  }, 3000);

  res.json({
    success: true,
    task: taskEntry,
    message: `Task dispatched to ${team.name}`,
  });
});

// GET /api/agents/tasks — get task log
router.get('/tasks', (req, res) => {
  res.json({
    tasks: taskLog.slice(-50).reverse(),
    total: taskLog.length,
  });
});

module.exports = router;

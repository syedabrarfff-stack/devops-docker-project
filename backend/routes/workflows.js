const express = require('express');
const router = express.Router();
const fetch = require('node-fetch');
const { routeModel, MODELS } = require('../config/models');

// POST /api/workflows/notify-slack
router.post('/notify-slack', async (req, res) => {
  const { title, body } = req.body;
  const webhook = process.env.SLACK_WEBHOOK_URL;
  if (!webhook) return res.json({ skipped: true, reason: 'SLACK_WEBHOOK_URL not set' });

  try {
    await fetch(webhook, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `*${title}*`,
        attachments: [{
          color: '#00d4ff',
          text: body,
          footer: 'JARVIS Command Center',
          footer_icon: 'https://cdn-icons-png.flaticon.com/512/4616/4616938.png',
          ts: Math.floor(Date.now() / 1000),
        }],
      }),
    });
    res.json({ sent: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/workflows/run — run a workflow server-side
router.post('/run', async (req, res) => {
  const { workflowId, context = '', apiKey } = req.body;
  if (!workflowId) return res.status(400).json({ error: 'workflowId required' });

  const prompts = buildPrompts(context);
  const prompt = prompts[workflowId];
  if (!prompt) return res.status(404).json({ error: `Unknown workflow: ${workflowId}` });

  // Try to call AI
  const modelKey = routeModel('general');
  const model = MODELS[modelKey];
  const key = process.env[model.envKey] || apiKey;

  if (!key) {
    return res.json({ result: demoResult(workflowId, context), demo: true, workflowId });
  }

  try {
    let response;
    if (model.provider === 'anthropic') {
      const Anthropic = require('@anthropic-ai/sdk');
      const client = new Anthropic({ apiKey: key });
      const result = await client.messages.create({
        model: model.id,
        max_tokens: 3000,
        system: 'You are JARVIS, the autonomous AI assistant for Captain Syed Abrar. Be professional, strategic, and concise.',
        messages: [{ role: 'user', content: prompt }],
      });
      response = result.content[0].text;
    } else if (model.provider === 'openai') {
      const OpenAI = require('openai');
      const client = new OpenAI({ apiKey: key });
      const result = await client.chat.completions.create({
        model: model.id,
        messages: [
          { role: 'system', content: 'You are JARVIS, the autonomous AI assistant for Captain Syed Abrar.' },
          { role: 'user', content: prompt },
        ],
        max_tokens: 3000,
      });
      response = result.choices[0].message.content;
    } else {
      response = demoResult(workflowId, context);
    }

    // Notify Slack
    const webhook = process.env.SLACK_WEBHOOK_URL;
    if (webhook) {
      fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `✅ *JARVIS Workflow Complete: ${workflowId}*`,
          attachments: [{ color: '#00ff88', text: response.substring(0, 500), footer: 'JARVIS' }],
        }),
      }).catch(() => {});
    }

    res.json({ result: response, demo: false, workflowId, model: modelKey });
  } catch (err) {
    res.status(500).json({ error: err.message, workflowId });
  }
});

// GET /api/workflows — list all workflows
router.get('/', (req, res) => {
  res.json({
    workflows: [
      { id: 'morning-briefing', name: 'Morning Briefing', icon: '☀️', steps: 5 },
      { id: 'social-post', name: 'Social Media Post', icon: '📱', steps: 5 },
      { id: 'sales-outreach', name: 'Sales Outreach', icon: '💼', steps: 5 },
      { id: 'content-pipeline', name: 'Content Pipeline', icon: '✍️', steps: 5 },
      { id: 'finance-report', name: 'Finance Report', icon: '💰', steps: 5 },
    ],
  });
});

function buildPrompts(context) {
  const date = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  const base = `You are JARVIS, the autonomous AI assistant for Captain Syed Abrar. Today is ${date}, ${time}.`;

  return {
    'morning-briefing': `${base} Deliver a concise, energetic morning briefing. Include: today's date, motivational opening, 5 prioritised tasks, suggested schedule, productivity tip, close with "Ready for your commands, Captain."`,
    'social-post': `${base} Generate a complete social media content package for: "${context || 'AI automation business'}". Create Twitter/X (280 chars), LinkedIn (150 words), Instagram with hashtags, Facebook post. Include visual concept suggestions.`,
    'sales-outreach': `${base} Create a complete B2B sales outreach package targeting: "${context || 'SaaS startup founders'}". Include ICP, 3-email sequence, LinkedIn message template, objection handling, CRM pipeline stages.`,
    'content-pipeline': `${base} Create a complete content piece for: "${context || 'AI automation'}". Include SEO blog post (600 words), Notion structure, meta description, social teaser, email newsletter version.`,
    'finance-report': `${base} Generate a professional financial report and KPI framework for an AI services business. Include MRR/ARR targets, Stripe metrics to track, Zoho Books categories, expense breakdown, growth KPIs with targets, and a Slack-ready weekly summary format.`,
  };
}

function demoResult(id, context) {
  return `[JARVIS Demo — ${id}]\nContext: "${context}"\n\nThis is demo mode. Add your API key (ANTHROPIC_API_KEY or OPENAI_API_KEY) to .env to enable live workflow execution.\n\nThe workflow engine is ready and will execute fully with live API keys.`;
}

module.exports = router;

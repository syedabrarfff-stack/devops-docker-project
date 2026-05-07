const express = require('express');
const router = express.Router();
const { MODELS, routeModel } = require('../config/models');

// Detect task type from prompt
function detectTaskType(prompt) {
  const p = prompt.toLowerCase();
  if (/\b(code|function|bug|debug|script|api|class|algorithm|sql|python|javascript|typescript)\b/.test(p)) return 'code';
  if (/\b(write|blog|article|story|copy|content|essay|caption)\b/.test(p)) return 'writing';
  if (/\b(research|analyze|study|report|data|statistics|trend)\b/.test(p)) return 'research';
  if (/\b(math|calculate|equation|formula|solve|integral|derivative)\b/.test(p)) return 'math';
  if (/\b(image|picture|photo|generate|draw|design|visual)\b/.test(p)) return 'image';
  if (/\b(voice|speak|say|audio|tts|synthesize)\b/.test(p)) return 'voice';
  if (/[一-鿿]/.test(p)) return 'chinese';
  if (/\b(reason|think|logic|problem|plan|strategy|decision)\b/.test(p)) return 'reasoning';
  return 'general';
}

// POST /api/chat — route to AI model and get response
router.post('/chat', async (req, res) => {
  const { message, modelKey, autoRoute = true, conversationHistory = [] } = req.body;

  if (!message) {
    return res.status(400).json({ error: 'message is required' });
  }

  const selectedKey = autoRoute
    ? routeModel(detectTaskType(message))
    : (modelKey || 'claude-sonnet');

  const model = MODELS[selectedKey];
  if (!model) {
    return res.status(400).json({ error: `Unknown model: ${selectedKey}` });
  }

  const apiKey = process.env[model.envKey];
  if (!apiKey) {
    return res.json({
      response: `[DEMO MODE] ${model.name} would respond here. Set ${model.envKey} in .env to enable live responses.\n\nYour message: "${message}"\n\nTask type detected: ${detectTaskType(message)}\nRouted to: ${model.name} (${model.provider})`,
      model: selectedKey,
      modelName: model.name,
      provider: model.provider,
      taskType: detectTaskType(message),
      demo: true,
    });
  }

  try {
    let response;

    if (model.provider === 'anthropic') {
      const Anthropic = require('@anthropic-ai/sdk');
      const client = new Anthropic({ apiKey });
      const messages = [
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await client.messages.create({
        model: model.id,
        max_tokens: 2048,
        system: 'You are JARVIS, an advanced AI assistant. Be concise, helpful, and precise.',
        messages,
      });
      response = result.content[0].text;

    } else if (model.provider === 'openai' && model.id !== 'dall-e-3' && model.id !== 'whisper-1') {
      const OpenAI = require('openai');
      const client = new OpenAI({ apiKey });
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant. Be concise, helpful, and precise.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await client.chat.completions.create({
        model: model.id,
        messages,
        max_tokens: 2048,
      });
      response = result.choices[0].message.content;

    } else if (model.provider === 'google') {
      const { GoogleGenerativeAI } = require('@google/generative-ai');
      const genAI = new GoogleGenerativeAI(apiKey);
      const gemini = genAI.getGenerativeModel({ model: model.id });
      const result = await gemini.generateContent(message);
      response = result.response.text();

    } else if (model.provider === 'deepseek') {
      const fetch = require('node-fetch');
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({ model: model.id, messages, max_tokens: 2048 }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'groq') {
      const fetch = require('node-fetch');
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({ model: model.id, messages, max_tokens: 2048 }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'mistral') {
      const fetch = require('node-fetch');
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await fetch('https://api.mistral.ai/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({ model: model.id, messages, max_tokens: 2048 }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'moonshot') {
      const fetch = require('node-fetch');
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await fetch('https://api.moonshot.cn/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({ model: model.id, messages, max_tokens: 2048 }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'zhipuai') {
      const fetch = require('node-fetch');
      const messages = [
        { role: 'system', content: 'You are JARVIS, an advanced AI assistant.' },
        ...conversationHistory,
        { role: 'user', content: message }
      ];
      const result = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({ model: model.id, messages, max_tokens: 2048 }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'minimax') {
      const fetch = require('node-fetch');
      const result = await fetch(`https://api.minimaxi.chat/v1/text/chatcompletion_v2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({
          model: model.id,
          messages: [{ role: 'user', content: message }],
          max_tokens: 2048,
        }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else if (model.provider === 'qwen') {
      const fetch = require('node-fetch');
      const result = await fetch('https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: model.id,
          input: { messages: [{ role: 'user', content: message }] },
          parameters: { max_tokens: 2048 },
        }),
      });
      const data = await result.json();
      response = data.output?.text || 'No response';

    } else if (model.provider === 'nvidia') {
      const fetch = require('node-fetch');
      const result = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
        body: JSON.stringify({
          model: model.id,
          messages: [{ role: 'user', content: message }],
          max_tokens: 2048,
        }),
      });
      const data = await result.json();
      response = data.choices?.[0]?.message?.content || 'No response';

    } else {
      response = `[${model.name}] API integration pending for provider: ${model.provider}`;
    }

    res.json({
      response,
      model: selectedKey,
      modelName: model.name,
      provider: model.provider,
      taskType: detectTaskType(message),
      demo: false,
    });

  } catch (err) {
    res.status(500).json({
      error: err.message,
      model: selectedKey,
      modelName: model.name,
    });
  }
});

// GET /api/models — list all available models
router.get('/models', (req, res) => {
  const modelList = Object.entries(MODELS).map(([key, m]) => ({
    key,
    name: m.name,
    provider: m.provider,
    color: m.color,
    icon: m.icon,
    strengths: m.strengths,
    contextWindow: m.contextWindow,
    hasKey: !!(process.env[m.envKey]),
  }));
  res.json({ models: modelList, total: modelList.length });
});

module.exports = router;

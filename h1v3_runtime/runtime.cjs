const express = require("express");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const chokidar = require("chokidar");

const AGENT_ROOT = path.join(process.env.HOME, ".h1v3", "agents");
const app = express();
app.use(express.json());

let agents = {};

// Load all agents from ~/.h1v3/agents
function loadAgents() {
  agents = {};
  if (!fs.existsSync(AGENT_ROOT)) return;

  const agentNames = fs.readdirSync(AGENT_ROOT);
  for (const name of agentNames) {
    const agentDir = path.join(AGENT_ROOT, name);
    const manifestPath = path.join(agentDir, "agent.json");
    const agentFile = path.join(agentDir, "agent.js");
    const toolsDir = path.join(agentDir, "tools");

    if (!fs.existsSync(manifestPath) || !fs.existsSync(agentFile)) continue;

    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    const agent = require(agentFile);

    // Load tools
    let tools = {};
    if (fs.existsSync(toolsDir)) {
      const toolFiles = fs.readdirSync(toolsDir);
      for (const f of toolFiles) {
        const toolName = f.replace(".js", "");
        tools[toolName] = require(path.join(toolsDir, f));
      }
    }

    agents[name] = { manifest, agent, tools };
    console.log(`Loaded agent: ${name}`);
  }
}

// Watch only agent.json, agent.js, and tools/*.js
chokidar.watch([
  path.join(AGENT_ROOT, "**/agent.json"),
  path.join(AGENT_ROOT, "**/agent.js"),
  path.join(AGENT_ROOT, "**/tools/*.js")
]).on("all", () => {
  console.log("Reloading agents...");
  loadAgents();
});

// Call Ollama
async function callOllama(messages, model) {
  const res = await axios.post("http://localhost:11434/api/chat", {
    model,
    messages,
    stream: false
  });
  return res.data;
}

// Agent endpoint
app.post("/agent/:name", async (req, res) => {
  const name = req.params.name;
  const agent = agents[name];
  if (!agent) return res.status(404).json({ error: "Agent not found" });

  const model = agent.manifest.model || "gemma4:e2b";

  let messages = [
    { role: "system", content: agent.manifest.system },
    { role: "user", content: req.body.input }
  ];

  while (true) {
    const response = await callOllama(messages, model);
    let msg = response.message;

    // Try to parse JSON tool calls inside strings (Gemma behavior)
    try {
      const parsed = JSON.parse(msg.content);
      if (parsed.tool) {
        msg = parsed;
      }
    } catch (e) {
      // Not JSON, ignore
    }

    // Tool call?
    if (msg.tool) {
      const tool = agent.tools[msg.tool];
      if (!tool) {
        messages.push({
          role: "assistant",
          content: `Tool ${msg.tool} not found`
        });
        continue;
      }

      const result = await tool.run(msg.arguments);

      // CRITICAL FIX: include the tool name so Gemma knows how to continue
      messages.push({
        role: "tool",
        name: msg.tool,
        content: JSON.stringify(result)
      });

      continue;
    }

    // Final answer
    return res.json({ output: msg.content });
  }
});

loadAgents();
app.listen(3928, () => console.log("h1v3 runtime listening on 3928"));

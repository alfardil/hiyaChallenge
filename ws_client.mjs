import dotenv from "dotenv";
dotenv.config();
import fs from "node:fs";
import WebSocket from "ws";
import express from "express";

const WS_URL = "wss://challenge.hiya-sandbox.com/v1/university-recruiting";
const API_KEY = process.env.API_KEY;
const X_USER = process.env.X_USER;
const OUTFILE = "messages.jsonl";

fs.writeFileSync(OUTFILE, "");

if (!API_KEY || !X_USER) {
  console.error("Missing env vars. Set API_KEY and X_USER.");
  process.exit(1);
}

const out = fs.createWriteStream(OUTFILE, { flags: "a" });

const app = express();
app.use(express.json());

let activeWs = null;
let pingInterval;

function connect() {
  const ws = new WebSocket(WS_URL, {
    headers: {
      "API-Key": API_KEY,
      "X-User": X_USER,
    },
    origin: "https://challenge.hiya-sandbox.com",
    perMessageDeflate: false,
  });

  ws.on("open", () => {
    console.log("Connected");
    // expose this connection to the HTTP endpoint
    activeWs = ws;
    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.ping();
    }, 25000);
  });

  ws.on("message", (data) => {
    const text = data.toString();
    console.log(text);

    try {
      const obj = JSON.parse(text);
      out.write(JSON.stringify(obj) + "\n");
    } catch {
      out.write(JSON.stringify({ raw: text }) + "\n");
    }
  });

  ws.on("close", (code, reasonBuf) => {
    clearInterval(pingInterval);
    const reason = reasonBuf?.toString() || "";
    console.error(`Closed (code=${code}${reason ? `, reason=${reason}` : ""})`);
    out.end();
    activeWs = null;
  });

  ws.on("error", (err) => {
    console.error("Error:", err.message || err);
  });

  return ws;
}

const HTTP_PORT = 3000;

app.post("/response", (req, res) => {
  const { text } = req.body;
  const msg = { type: "Response", text };

  try {
    activeWs.send(JSON.stringify(msg));
    return res.status(200).json({ sent: true, message: msg });
  } catch (err) {
    return res.status(500).json({ error: String(err) });
  }
});

app.listen(HTTP_PORT, () => {
  console.log(
    `HTTP endpoint listening on http://localhost:${HTTP_PORT}/response`
  );
  connect();
});

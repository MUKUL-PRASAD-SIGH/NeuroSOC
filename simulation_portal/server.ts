import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import cors from 'cors';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const port = 3000;

  app.use(cors());
  app.use(express.json());

  // Mock database for verdicts
  const verdicts: Record<string, any> = {
    'system-user': {
      snnScore: 0.12,
      lnnClass: 'BENIGN',
      xgBoostClass: 'BENIGN',
      behavioralDelta: 0.05,
      confidence: 0.98,
      verdict: 'TRUSTED'
    }
  };

  let currentVerdict = verdicts['system-user'];

  // API Routes
  app.post('/api/bank/login', (req, res) => {
    const { email } = req.body;
    console.log(`[Bank] Login attempt for: ${email}`);
    
    // Simple logic for simulation
    const verdict = email.toLowerCase().includes('hacker') ? 'HACKER' : 'TRUSTED';
    
    currentVerdict = {
      snnScore: verdict === 'HACKER' ? 0.89 : 0.08,
      lnnClass: verdict,
      xgBoostClass: verdict,
      behavioralDelta: verdict === 'HACKER' ? 0.75 : 0.02,
      confidence: 0.94,
      verdict: verdict
    };
    
    res.json({ success: true, user_id: email || 'anonymous', verdict });
  });

  app.post('/api/behavioral', (req, res) => {
    const { user_id, events } = req.body;
    console.log(`[NeuroShield] Received ${events?.length || 0} events for ${user_id}`);
    res.json({ status: 'received' });
  });

  app.post('/api/bank/honeypot-hit', (req, res) => {
    console.warn(`[SECURITY] Honeypot hit detected!`);
    res.json({ status: 'flagged' });
  });

  app.post('/api/bank/web-attack-detected', (req, res) => {
    console.warn(`[SECURITY] SQL Injection or web attack detected!`);
    res.json({ status: 'blocked' });
  });

  app.get('/api/verdicts/current', (req, res) => {
    res.json(currentVerdict);
  });

  app.get('/api/verdicts/:userId', (req, res) => {
    res.json(currentVerdict);
  });

  // Vite integration
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
  });
}

startServer();

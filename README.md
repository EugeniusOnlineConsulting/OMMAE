OMMAE HQ — Mohawk Medibles command center.

Agent drafts content, acquisition leads, team tasks, and realtime incidents. Humans approve before anything posts, outreaches, or deploys.

```bash
pip install -r backend/requirements.txt
OMMAE_STORE_PATH=/tmp/ommae.json python backend/main.py
```

Open http://localhost:8080/admin

- Staging / Approved: video HITL
- Acquisition: lead outreach HITL
- Team: members, roles, agent-drafted tasks
- Incidents: Gloris local diagnosis + Cursor Bridge (premium Codex/OpenAI is optional; 401 falls back locally)
- Logs: HQ activity

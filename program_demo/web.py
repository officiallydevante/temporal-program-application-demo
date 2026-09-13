"""Run with: uvicorn program_demo.web:app --reload

The form + live status page. This is the browser-facing half of the demo —
submitting the form starts a workflow; the status page polls get_status and
exposes a real "Withdraw" button wired to the withdraw_application signal.
"""

from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from temporalio.client import Client

from program_demo.shared import ApplicationInput, TASK_QUEUE
from program_demo.workflow import ProgramApplicationWorkflow

load_dotenv()

TRACKS = ["Video Editing", "Cinematography", "Motion Graphics", "Production Sound"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.temporal_client = await Client.connect("localhost:7233")
    yield


app = FastAPI(lifespan=lifespan)

PAGE_STYLE = """
<style>
  body { background:#0b0b0c; color:#e4e4e6; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         max-width:560px; margin:64px auto; padding:0 20px; }
  h1 { font-size:22px; letter-spacing:-0.02em; }
  label { display:block; margin:18px 0 6px; font-size:13px; color:#9a9aa1; }
  input, select, textarea { width:100%; box-sizing:border-box; padding:10px 12px; background:#18181b;
         border:1px solid #2e2e33; border-radius:8px; color:#e4e4e6; font-size:14px; }
  textarea { min-height:90px; resize:vertical; }
  button { margin-top:24px; padding:12px 22px; background:#0047FF; color:#fff; border:none;
         border-radius:999px; font-size:14px; font-weight:600; cursor:pointer; }
  button.secondary { background:transparent; border:1px solid #48484f; color:#c7c7cb; }
  button:disabled { opacity:0.5; cursor:default; }
  .status { font-family:'JetBrains Mono',ui-monospace,monospace; font-size:13px; color:#60A5FA;
         padding:14px 16px; background:#111113; border:1px solid #2e2e33; border-radius:8px; margin:20px 0; }
</style>
"""


@app.get("/", response_class=HTMLResponse)
async def form_page() -> str:
    options = "".join(f'<option value="{t}">{t}</option>' for t in TRACKS)
    return f"""<!doctype html><html><head><title>Program Application</title>{PAGE_STYLE}</head><body>
      <h1>Apply to the program</h1>
      <form method="post" action="/apply">
        <label>Name</label><input name="name" required />
        <label>Email</label><input name="email" type="email" required />
        <label>Track</label><select name="track">{options}</select>
        <label>Why do you want to join?</label><textarea name="motivation"></textarea>
        <button type="submit">Submit application</button>
      </form>
    </body></html>"""


@app.post("/apply")
async def apply(
    name: str = Form(...),
    email: str = Form(...),
    track: str = Form(...),
    motivation: str = Form(""),
) -> RedirectResponse:
    application_id = f"application-{uuid4()}"
    application = ApplicationInput(
        application_id=application_id, name=name, email=email, track=track, motivation=motivation
    )
    await app.state.temporal_client.start_workflow(
        ProgramApplicationWorkflow.run,
        application,
        id=application_id,
        task_queue=TASK_QUEUE,
    )
    return RedirectResponse(url=f"/status/{application_id}", status_code=303)


@app.get("/status/{workflow_id}", response_class=HTMLResponse)
async def status_page(workflow_id: str) -> str:
    return f"""<!doctype html><html><head><title>Application status</title>{PAGE_STYLE}</head><body>
      <h1>Your application</h1>
      <div class="status" id="status">loading…</div>
      <button class="secondary" id="withdraw">Withdraw my application</button>
      <script>
        const statusEl = document.getElementById('status');
        const withdrawBtn = document.getElementById('withdraw');
        const TERMINAL = ['accepted', 'withdrawn'];

        async function poll() {{
          const res = await fetch('/status/{workflow_id}/json');
          const data = await res.json();
          statusEl.textContent = data.status;
          if (TERMINAL.includes(data.status)) {{
            withdrawBtn.disabled = true;
          }} else {{
            setTimeout(poll, 2000);
          }}
        }}

        withdrawBtn.addEventListener('click', async () => {{
          withdrawBtn.disabled = true;
          await fetch('/withdraw/{workflow_id}', {{ method: 'POST' }});
        }});

        poll();
      </script>
    </body></html>"""


@app.get("/status/{workflow_id}/json")
async def status_json(workflow_id: str) -> JSONResponse:
    handle = app.state.temporal_client.get_workflow_handle(workflow_id)
    status = await handle.query(ProgramApplicationWorkflow.get_status)
    return JSONResponse({"status": status})


@app.post("/withdraw/{workflow_id}")
async def withdraw(workflow_id: str) -> JSONResponse:
    handle = app.state.temporal_client.get_workflow_handle(workflow_id)
    await handle.signal(ProgramApplicationWorkflow.withdraw_application)
    return JSONResponse({"ok": True})

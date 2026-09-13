"""HTML email templates. Visual style mirrors studio22-productions/src/lib/resend.ts's
dark-card templates (bg #0f0e0d, card #1a1815, border #2a2723, accent #0047FF,
JetBrains Mono eyebrow) so the demo's emails look authentically "Studio 22" —
this is a standalone copy for the demo, not a shared module with the production repo.
"""


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_acceptance_email(name: str, track: str) -> str:
    safe_name = _escape(name)
    safe_track = _escape(track)
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#0f0e0d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e8e6e0;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#0f0e0d;padding:40px 20px;">
      <tr><td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:#1a1815;border-radius:12px;border:1px solid #2a2723;">
          <tr><td style="padding:32px 36px 28px;">
            <div style="font-family:'JetBrains Mono',Menlo,monospace;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:#0047FF;margin-bottom:24px;">Studio 22 Productions</div>
            <h1 style="font-size:24px;line-height:1.3;font-weight:700;margin:0 0 14px;color:#ffffff;letter-spacing:-0.02em;">You're in, {safe_name}.</h1>
            <p style="font-size:15px;line-height:1.55;color:#b8b4ac;margin:0 0 24px;">
              You've been accepted into the <strong style="color:#e8e6e0;">{safe_track}</strong> track. We'll be in touch shortly
              with next steps — glad to have you.
            </p>
            <hr style="border:none;border-top:1px solid #2a2723;margin:28px 0;" />
            <p style="font-size:13px;line-height:1.6;color:#b8b4ac;margin:0;">Reply to this email anytime with questions.</p>
            <p style="font-size:13px;line-height:1.6;color:#b8b4ac;margin:14px 0 0;">— Devante<br /><span style="color:#7a766e;font-size:12px;">Studio 22 Productions</span></p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


def render_withdrawal_email(name: str) -> str:
    safe_name = _escape(name)
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#0f0e0d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e8e6e0;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#0f0e0d;padding:40px 20px;">
      <tr><td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:#1a1815;border-radius:12px;border:1px solid #2a2723;">
          <tr><td style="padding:32px 36px 28px;">
            <div style="font-family:'JetBrains Mono',Menlo,monospace;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:#0047FF;margin-bottom:24px;">Studio 22 Productions</div>
            <h1 style="font-size:22px;line-height:1.3;font-weight:700;margin:0 0 14px;color:#ffffff;letter-spacing:-0.02em;">Got it, {safe_name} — you're withdrawn.</h1>
            <p style="font-size:15px;line-height:1.55;color:#b8b4ac;margin:0 0 24px;">
              Your application has been withdrawn per your request. No further action needed — you're welcome to apply again anytime.
            </p>
            <hr style="border:none;border-top:1px solid #2a2723;margin:28px 0;" />
            <p style="font-size:13px;line-height:1.6;color:#b8b4ac;margin:14px 0 0;">— Devante<br /><span style="color:#7a766e;font-size:12px;">Studio 22 Productions</span></p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

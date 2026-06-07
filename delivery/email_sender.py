import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config.settings import GMAIL_USER, GMAIL_APP_PASSWORD, REPORT_RECIPIENT

logger = logging.getLogger(__name__)

SENTIMENT_COLOR = {
    "BULLISH": "#1D9E75",
    "BEARISH": "#E24B4A",
    "MIXED":   "#BA7517",
    "NEUTRAL": "#888780",
}


def _sentiment_badge(sentiment: str) -> str:
    color = SENTIMENT_COLOR.get(sentiment, "#888780")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:600;background:{color}20;color:{color};'
        f'border:1px solid {color}40">{sentiment}</span>'
    )


def _arrow(val):
    return "▲" if val >= 0 else "▼"


def _build_html(context: dict) -> str:
    run_date         = context.get("run_date", str(date.today()))
    overall_summary  = context.get("overall_summary", "")
    overall_sentiment= context.get("overall_sentiment", "NEUTRAL")
    holdings         = context.get("holdings", [])
    citations        = context.get("citations", [])
    ps               = context.get("portfolio_summary", {})

    total_invested   = ps.get("total_invested", 0)
    total_current    = ps.get("total_current", 0)
    total_pnl        = ps.get("total_pnl", 0)
    total_pnl_pct    = ps.get("total_pnl_pct", 0)
    port_color       = "#1D9E75" if total_pnl >= 0 else "#E24B4A"

    # ── Portfolio summary cards ───────────────────────────────
    summary_cards = f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:4px">
      <tr>
        <td style="padding:16px;text-align:center;background:#f9f9f9;border-radius:8px;border:1px solid #eee">
          <div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.05em">Invested</div>
          <div style="font-size:20px;font-weight:700;color:#111;margin-top:4px">₹{total_invested:,.0f}</div>
        </td>
        <td style="width:16px"></td>
        <td style="padding:16px;text-align:center;background:#f9f9f9;border-radius:8px;border:1px solid #eee">
          <div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.05em">Current Value</div>
          <div style="font-size:20px;font-weight:700;color:#111;margin-top:4px">₹{total_current:,.0f}</div>
        </td>
        <td style="width:16px"></td>
        <td style="padding:16px;text-align:center;background:{port_color}10;border-radius:8px;border:1px solid {port_color}30">
          <div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.05em">Total P&L</div>
          <div style="font-size:20px;font-weight:700;color:{port_color};margin-top:4px">
            {_arrow(total_pnl)} ₹{abs(total_pnl):,.0f}
          </div>
          <div style="font-size:12px;color:{port_color}">{total_pnl_pct:+.2f}%</div>
        </td>
      </tr>
    </table>
    """

    # ── Holdings rows ─────────────────────────────────────────
    holding_rows = ""
    for h in holdings:
        sentiments = [a.get("sentiment", "NEUTRAL") for a in h.get("articles", [])]
        dominant   = max(set(sentiments), key=sentiments.count) if sentiments else "NEUTRAL"

        pnl_color = "#1D9E75" if h["pnl"] >= 0 else "#E24B4A"
        day_color = "#1D9E75" if h["day_change_pct"] >= 0 else "#E24B4A"

        holding_rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0">
          <td style="padding:14px 12px">
            <div style="font-weight:700;font-size:14px">{h['ticker']}</div>
            <div style="font-size:11px;color:#999;margin-top:2px">{h['company_name']}</div>
            <div style="font-size:11px;color:#bbb">{h.get('sector','')}</div>
          </td>
          <td style="padding:14px 12px">
            <div style="font-size:13px;font-weight:600">₹{h['current_price']:,.2f}</div>
            <div style="font-size:11px;color:{day_color};margin-top:2px">
              {_arrow(h['day_change_pct'])} ₹{abs(h['day_change']):.2f} ({h['day_change_pct']:+.2f}%) today
            </div>
            <div style="font-size:11px;color:#bbb;margin-top:2px">
              Bought @ ₹{h['buy_price']:,.2f} × {int(h['qty'])} qty
            </div>
          </td>
          <td style="padding:14px 12px">
            <div style="font-size:12px;color:#777">Invested</div>
            <div style="font-size:13px;font-weight:600">₹{h['invested_value']:,.0f}</div>
            <div style="font-size:12px;color:#777;margin-top:4px">Current</div>
            <div style="font-size:13px;font-weight:600">₹{h['current_value']:,.0f}</div>
          </td>
          <td style="padding:14px 12px">
            <div style="font-size:18px;font-weight:700;color:{pnl_color}">
              {_arrow(h['pnl'])} ₹{abs(h['pnl']):,.0f}
            </div>
            <div style="font-size:12px;color:{pnl_color}">{h['pnl_pct']:+.2f}% overall</div>
          </td>
          <td style="padding:14px 12px">{_sentiment_badge(dominant)}</td>
        </tr>
        <tr>
          <td colspan="5" style="padding:8px 12px 16px;font-size:12px;color:#555;
              border-bottom:2px solid #f0f0f0;line-height:1.6">
            {h.get('summary', '')}
          </td>
        </tr>
        """

    # ── Citation links ────────────────────────────────────────
    citation_links = ""
    for c in citations[:10]:
        s_color = SENTIMENT_COLOR.get(c.get("sentiment", "NEUTRAL"), "#888780")
        citation_links += (
            f'<a href="{c["url"]}" style="display:inline-block;margin:4px 6px 4px 0;'
            f'padding:4px 12px;border-radius:20px;font-size:11px;text-decoration:none;'
            f'background:{s_color}15;color:{s_color};border:1px solid {s_color}30">'
            f'{c["source_name"]} &rarr; {c["title"][:50]}...</a>'
        )

    ov_color = SENTIMENT_COLOR.get(overall_sentiment, "#888780")

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
      <div style="max-width:700px;margin:32px auto;background:#fff;
                  border-radius:12px;overflow:hidden;border:1px solid #e5e5e5">

        <!-- Header -->
        <div style="padding:24px 32px;border-bottom:1px solid #eee">
          <div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;
                      letter-spacing:0.06em">Portfolio Intelligence Report</div>
          <div style="font-size:22px;font-weight:700;color:#111">{run_date}</div>
          <div style="margin-top:8px">{_sentiment_badge(overall_sentiment)}</div>
        </div>

        <!-- Portfolio summary cards -->
        <div style="padding:24px 32px;border-bottom:1px solid #eee">
          <div style="font-size:12px;color:#999;margin-bottom:12px;text-transform:uppercase;
                      letter-spacing:0.05em">Portfolio Overview</div>
          {summary_cards}
        </div>

        <!-- Overall AI summary -->
        <div style="padding:20px 32px;background:#fafafa;border-bottom:1px solid #eee">
          <div style="font-size:12px;color:#999;margin-bottom:8px;text-transform:uppercase;
                      letter-spacing:0.05em">AI Summary</div>
          <div style="font-size:14px;color:#333;line-height:1.7">{overall_summary}</div>
        </div>

        <!-- Holdings table -->
        <div style="padding:20px 32px">
          <div style="font-size:12px;color:#999;margin-bottom:12px;text-transform:uppercase;
                      letter-spacing:0.05em">Holdings</div>
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr style="background:#f5f5f5">
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;font-weight:600;text-transform:uppercase">Stock</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;font-weight:600;text-transform:uppercase">Price</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;font-weight:600;text-transform:uppercase">Value</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;font-weight:600;text-transform:uppercase">P&L</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;font-weight:600;text-transform:uppercase">Sentiment</th>
              </tr>
            </thead>
            <tbody>{holding_rows}</tbody>
          </table>
        </div>

        <!-- Sources -->
        <div style="padding:20px 32px;background:#fafafa;border-top:1px solid #eee">
          <div style="font-size:12px;color:#999;margin-bottom:10px;text-transform:uppercase;
                      letter-spacing:0.05em">Sources</div>
          {citation_links if citation_links else '<span style="font-size:12px;color:#aaa">No news articles found today</span>'}
        </div>

        <!-- Footer -->
        <div style="padding:16px 32px;border-top:1px solid #eee">
          <div style="font-size:11px;color:#bbb">
            Generated by portfolio-intelligence &middot; Powered by NVIDIA NIM
          </div>
        </div>

      </div>
    </body>
    </html>
    """


def send_report(context: dict):
    run_date         = context.get("run_date", str(date.today()))
    overall_sentiment= context.get("overall_sentiment", "NEUTRAL")
    ps               = context.get("portfolio_summary", {})
    total_pnl        = ps.get("total_pnl", 0)
    pnl_arrow        = "▲" if total_pnl >= 0 else "▼"

    subject = f"Portfolio Report {run_date} | {pnl_arrow} ₹{abs(total_pnl):,.0f} | {overall_sentiment}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = REPORT_RECIPIENT

    html = _build_html(context)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, REPORT_RECIPIENT, msg.as_string())
        logger.info(f"Report email sent to {REPORT_RECIPIENT}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise
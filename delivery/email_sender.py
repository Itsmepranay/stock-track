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


def _build_html(context: dict) -> str:
    run_date = context.get("run_date", str(date.today()))
    overall_summary = context.get("overall_summary", "")
    overall_sentiment = context.get("overall_sentiment", "NEUTRAL")
    holdings = context.get("holdings", [])
    citations = context.get("citations", [])

    # Holdings table rows
    holding_rows = ""
    for h in holdings:
        sentiments = [a.get("sentiment","NEUTRAL") for a in h.get("articles",[])]
        dominant = max(set(sentiments), key=sentiments.count) if sentiments else "NEUTRAL"
        chg_color = "#1D9E75" if h["change_pct"] >= 0 else "#E24B4A"
        pnl_color = "#1D9E75" if h["pnl"] >= 0 else "#E24B4A"
        holding_rows += f"""
        <tr>
          <td style="padding:10px 12px;font-weight:600;font-size:13px">{h['ticker']}</td>
          <td style="padding:10px 12px;font-size:13px;color:#444">{h['company_name']}</td>
          <td style="padding:10px 12px;font-size:13px">₹{h['current_price']:,.2f}</td>
          <td style="padding:10px 12px;font-size:13px;color:{chg_color}">{h['change_pct']:+.2f}%</td>
          <td style="padding:10px 12px;font-size:13px;color:{pnl_color}">₹{h['pnl']:,.0f}</td>
          <td style="padding:10px 12px">{_sentiment_badge(dominant)}</td>
        </tr>
        <tr>
          <td colspan="6" style="padding:8px 12px 16px;font-size:12px;color:#555;
              border-bottom:1px solid #eee;line-height:1.6">{h.get('summary','')}</td>
        </tr>
        """

    # Citation links
    citation_links = ""
    for c in citations[:10]:
        s_color = SENTIMENT_COLOR.get(c.get("sentiment","NEUTRAL"), "#888780")
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
      <div style="max-width:680px;margin:32px auto;background:#fff;
                  border-radius:12px;overflow:hidden;border:1px solid #e5e5e5">

        <div style="padding:24px 32px;border-bottom:1px solid #eee">
          <div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;
                      letter-spacing:0.06em">Portfolio intelligence report</div>
          <div style="font-size:22px;font-weight:700;color:#111">{run_date}</div>
          <div style="margin-top:8px">{_sentiment_badge(overall_sentiment)}</div>
        </div>

        <div style="padding:20px 32px;background:#fafafa;border-bottom:1px solid #eee">
          <div style="font-size:12px;color:#999;margin-bottom:8px;text-transform:uppercase;
                      letter-spacing:0.05em">Overall summary</div>
          <div style="font-size:14px;color:#333;line-height:1.7">{overall_summary}</div>
        </div>

        <div style="padding:20px 32px">
          <div style="font-size:12px;color:#999;margin-bottom:12px;text-transform:uppercase;
                      letter-spacing:0.05em">Holdings</div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="background:#f5f5f5">
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">Ticker</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">Company</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">Price</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">Day</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">P&L</th>
                <th style="padding:8px 12px;text-align:left;font-size:11px;color:#999;
                            font-weight:600;text-transform:uppercase">Sentiment</th>
              </tr>
            </thead>
            <tbody>{holding_rows}</tbody>
          </table>
        </div>

        <div style="padding:20px 32px;background:#fafafa;border-top:1px solid #eee">
          <div style="font-size:12px;color:#999;margin-bottom:10px;text-transform:uppercase;
                      letter-spacing:0.05em">Sources</div>
          {citation_links if citation_links else '<span style="font-size:12px;color:#aaa">No news articles found today</span>'}
        </div>

        <div style="padding:16px 32px;border-top:1px solid #eee">
          <div style="font-size:11px;color:#bbb">
            Generated by portfolio-intelligence &middot; Powered by Gemini 1.5 Flash
          </div>
        </div>
      </div>
    </body>
    </html>
    """


def send_report(context: dict):
    """Send the daily HTML report via Gmail."""
    run_date = context.get("run_date", str(date.today()))
    overall_sentiment = context.get("overall_sentiment", "NEUTRAL")
    subject = f"Portfolio report {run_date} — {overall_sentiment}"

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
{
  "current_day": 19,
  "next_day": 20,
  "phase": "morning_complete",
  "last_run": "2026-06-07T03:05:00+05:30",
  "blog_prs": {
    "ai_learning": {
      "pr_url": "https://github.com/AkshantVats/Profile/pull/23",
      "live_url": "https://akshantvats.github.io/Profile/blog/series/ai-learning/day-20-prompt-engineering-infra-optimization.html",
      "status": "live",
      "day": 20
    },
    "experience": {
      "pr_url": "https://github.com/AkshantVats/Profile/pull/22",
      "live_url": "https://akshantvats.github.io/Profile/blog/series/experience/day-20-route-consumer-lag-keda.html",
      "status": "live",
      "day": 20
    }
  },
  "code_pr": {
    "url": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/9",
    "status": "open_draft",
    "day": 20,
    "ci": "passing"
  },
  "day_19": {
    "phase": "morning_complete",
    "code_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/7",
    "code_pr_status": "open_draft_awaiting_merge"
  },
  "oss_polish_pr": null,
  "email_sent": false,
  "morning_email_sent": false,
  "feedback_applied": false,
  "covers_status": "pillow_generated",
  "pre_push_issues": "AI Learning: sibling post 404 pre-deployment (resolved after both merged) + Twitter 403 (bot block false positive). All real HTML checks passed.",
  "## Email Errors": [
    {
      "timestamp": "2026-06-06T22:25:00+05:30",
      "error": "gmail_send.sh exit 22 — Gmail OAuth token invalid_grant: Token has been expired or revoked."
    },
    {
      "timestamp": "2026-06-06T23:00:00+05:30",
      "error": "11pm polish agent: gmail_send.sh exit 22 — Gmail OAuth token invalid_grant. Could not send code PRs not merged notification."
    },
    {
      "timestamp": "2026-06-07T03:05:00+05:30",
      "error": "3am retry agent: gmail_send.sh exit 22 — Gmail OAuth token invalid_grant (persistent across 3 runs). Email body ready at /tmp/email-body.html for manual send. GMAIL CREDENTIALS NEED REFRESH — see action_required below."
    }
  ],
  "action_required": {
    "priority": "HIGH",
    "item": "Gmail OAuth refresh token has been permanently revoked (invalid_grant across 3 runs since 10pm IST). Morning email for Day 20 has NOT been sent. To fix: (1) Re-authorize the Gmail OAuth app at Google Cloud Console, (2) Get a new refresh_token, (3) Update GMAIL_REFRESH_TOKEN in akshant-agent/.agent/credentials.env, (4) The next scheduled run will retry the email automatically.",
    "day20_summary": "Day 20 complete: 2 blogs live, code PR #9 open (CI passing). PR #7 (Day 19) and PR #9 (Day 20) both await merge. Merge PR #9 to advance to Day 21.",
    "manual_email_subject": "Day 20 ✅ — Prompt Engineering as Infra Optimization + Route Consumer Lag",
    "manual_email_links": {
      "ai_blog": "https://akshantvats.github.io/Profile/blog/series/ai-learning/day-20-prompt-engineering-infra-optimization.html",
      "experience_blog": "https://akshantvats.github.io/Profile/blog/series/experience/day-20-route-consumer-lag-keda.html",
      "code_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/9",
      "ai_blog_pr": "https://github.com/AkshantVats/Profile/pull/23",
      "experience_blog_pr": "https://github.com/AkshantVats/Profile/pull/22"
    }
  },
  "3am_check": {
    "timestamp": "2026-06-07T03:05:00+05:30",
    "day19_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/7",
    "day19_pr_state": "open_draft",
    "day20_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/9",
    "day20_pr_state": "open_draft",
    "day20_pr_ci": "passing (2/2 checks green)",
    "email_retry": "failed_invalid_grant",
    "action": "logged_error_awaiting_credential_refresh"
  },
  "11pm_polish_check": {
    "timestamp": "2026-06-06T23:00:00+05:30",
    "day19_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/7",
    "day19_pr_state": "open_draft",
    "day20_pr": "https://github.com/AkshantVats/ebpf-llm-tracer/pull/9",
    "day20_pr_state": "open_draft",
    "action": "polish_skipped_prs_not_merged"
  }
}

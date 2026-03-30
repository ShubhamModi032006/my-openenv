emails = [
    {
        "id": "email_1",
        "sender": "vip.customer@bigcorp.com",
        "subject": "System is down! Critical!",
        "body": "Our production servers are failing because of your API. Needs immediate attention.",
        "timestamp": "2023-10-27T10:00:00Z",
        "metadata": {
            "expected_priority": "high",
            "expected_department": "support",
            "expected_final_action": "escalate",
            "expected_reply_keywords": ["sorry", "api", "servers", "immediate", "investigating"]
        }
    },
    {
        "id": "email_2",
        "sender": "newlead@startup.io",
        "subject": "Pricing inquiry for Enterprise plan",
        "body": "Hi, we are looking to upgrade to the enterprise plan. Can we get a quote for 500 users?",
        "timestamp": "2023-10-27T10:15:00Z",
        "metadata": {
            "expected_priority": "medium",
            "expected_department": "sales",
            "expected_final_action": "archive",
            "expected_reply_keywords": ["quote", "500", "users", "enterprise", "plan"]
        }
    },
    {
        "id": "email_3",
        "sender": "john.doe@gmail.com",
        "subject": "Job application - Software Engineer",
        "body": "Hi, I have attached my resume for the Software Engineer position. Let me know if you need more info.",
        "timestamp": "2023-10-27T11:00:00Z",
        "metadata": {
            "expected_priority": "low",
            "expected_department": "hr",
            "expected_final_action": "archive",
            "expected_reply_keywords": ["application", "resume", "software", "engineer", "review"]
        }
    },
    {
        "id": "email_4",
        "sender": "marketing.tools@vendorco.com",
        "subject": "Unlock 20% more leads with our new tool!",
        "body": "Hi there! I wanted to check if your team uses lead scraping. We just launched a tool that saves 5 hours a week.",
        "timestamp": "2023-10-27T11:45:00Z",
        "metadata": {
            "expected_priority": "low",
            "expected_department": "sales",
            "expected_final_action": "archive",
            "expected_reply_keywords": ["no", "thank you", "unsubscribe", "not interested"]
        }
    },
    {
        "id": "email_5",
        "sender": "sarah.management@bigcorp.com",
        "subject": "URGENT: Employee misconduct report",
        "body": "I need to speak with an HR representative immediately regarding a severe code of conduct violation on the sales floor.",
        "timestamp": "2023-10-27T12:00:00Z",
        "metadata": {
            "expected_priority": "high",
            "expected_department": "hr",
            "expected_final_action": "escalate",
            "expected_reply_keywords": ["misconduct", "hr", "speak", "immediately", "violation", "confidential"]
        }
    },
    {
        "id": "email_6",
        "sender": "billing@cloudhost.com",
        "subject": "Invoice Overdue - Account Suspension Notice",
        "body": "Your invoice #8821 for $4,500 is 15 days overdue. Please remit payment immediately to avoid service suspension.",
        "timestamp": "2023-10-27T13:00:00Z",
        "metadata": {
            "expected_priority": "high",
            "expected_department": "support",
            "expected_final_action": "escalate",
            "expected_reply_keywords": ["invoice", "payment", "overdue", "suspension", "forwarding"]
        }
    },
    {
        "id": "email_7",
        "sender": "dev.team@internal.org",
        "subject": "Weekly sprint planning sync",
        "body": "Just a reminder that our weekly cross-team sprint sync is moved to Thursday at 2 PM. Please update your calendars.",
        "timestamp": "2023-10-27T14:20:00Z",
        "metadata": {
            "expected_priority": "low",
            "expected_department": "hr",
            "expected_final_action": "archive",
            "expected_reply_keywords": ["noted", "calendar", "thursday", "sync", "updated"]
        }
    },
    {
        "id": "email_8",
        "sender": "press@techblog.net",
        "subject": "Interview request regarding your recent Series B",
        "body": "Hi team, we are covering your recent funding round. Do you have 15 minutes for a quick founder interview tomorrow?",
        "timestamp": "2023-10-27T15:10:00Z",
        "metadata": {
            "expected_priority": "medium",
            "expected_department": "sales",
            "expected_final_action": "escalate",
            "expected_reply_keywords": ["interview", "series b", "press", "founder", "schedule"]
        }
    },
    {
        "id": "email_9",
        "sender": "intern@university.edu",
        "subject": "Question about summer internship dates",
        "body": "Good morning. Could you confirm if the summer internship program starts on June 1st or June 15th?",
        "timestamp": "2023-10-27T16:00:00Z",
        "metadata": {
            "expected_priority": "low",
            "expected_department": "hr",
            "expected_final_action": "archive",
            "expected_reply_keywords": ["internship", "start", "june", "program"]
        }
    },
    {
        "id": "email_10",
        "sender": "partner@integration.co",
        "subject": "API Deprecation Warning",
        "body": "We are deprecating the v1 endpoints in 30 days. Please ensure your systems migration to v2 is completed.",
        "timestamp": "2023-10-27T17:30:00Z",
        "metadata": {
            "expected_priority": "high",
            "expected_department": "support",
            "expected_final_action": "escalate",
            "expected_reply_keywords": ["v2", "migration", "deprecation", "endpoints", "team"]
        }
    }
]

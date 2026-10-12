"""Explicit opt-in fictional demonstration records; never used for production signup."""

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.crm import service
from app.modules.crm.models import Lead, now


def seed_demo(db: Session, user: Any) -> None:
    existing = db.scalar(
        select(Lead.id).where(
            Lead.org_id == user.org_id, Lead.name == "Aditi Mehta", Lead.tags.contains("demo")
        )
    )
    if existing:
        return
    accounts = []
    for name, industry, city in [
        ("Northstar Logistics", "Logistics", "Mumbai"),
        ("Bluebird Technologies", "Software", "Bengaluru"),
        ("Greenfield Foods", "Food distribution", "Pune"),
        ("Riverstone Manufacturing", "Manufacturing", "Ahmedabad"),
        ("Cloudline Services", "Professional services", "Hyderabad"),
    ]:
        accounts.append(
            service.create(
                db,
                user,
                "parties",
                {
                    "name": name,
                    "industry": industry,
                    "city": city,
                    "tags": ["demo"],
                    "notes": "Fictional demonstration account.",
                },
            )
        )
    contacts = []
    for index, name in enumerate(
        ["Aditi Mehta", "Rohan Shah", "Priya Nair", "Kabir Patel", "Neha Rao"]
    ):
        contacts.append(
            service.create(
                db,
                user,
                "contacts",
                {
                    "name": name,
                    "email": f"demo.contact{index}@example.com",
                    "company": accounts[index].name,
                    "party_id": accounts[index].id,
                    "title": [
                        "Operations Director",
                        "VP of Sales",
                        "Founder",
                        "Procurement Head",
                        "Customer Success Lead",
                    ][index],
                    "tags": ["demo"],
                },
            )
        )
    today = now().date()
    for index, name in enumerate(
        [
            "Aditi Mehta",
            "Vikram Kapoor",
            "Meera Iyer",
            "Arjun Desai",
            "Sana Khan",
            "Nikhil Joshi",
            "Tara Menon",
            "Dev Malhotra",
        ]
    ):
        service.create(
            db,
            user,
            "leads",
            {
                "name": name,
                "email": f"demo.lead{index}@example.com",
                "company": [
                    "Evergreen Retail",
                    "Orbit Systems",
                    "Vertex Trading",
                    "Brightway Consulting",
                ][index % 4],
                "source": ["Website", "Referral", "LinkedIn", "Event"][index % 4],
                "status": ["New", "Contacted", "Qualified", "New"][index % 4],
                "value": str((index + 1) * 25000),
                "score": 40 + index * 7,
                "next_follow_up": (today + timedelta(days=index - 2)).isoformat(),
                "tags": ["demo"],
                "notes": "Fictional lead for exploring the CRM. Replace with your own records.",
            },
        )
    pipeline = service.pipelines(db, user)[0]
    stages = pipeline["stages"]
    for index, name in enumerate(
        [
            "Fleet operations rollout",
            "Revenue team onboarding",
            "Distribution expansion",
            "Annual support renewal",
            "Customer engagement platform",
            "Regional sales workspace",
            "Enterprise onboarding",
        ]
    ):
        account = accounts[index % len(accounts)]
        deal = service.create(
            db,
            user,
            "deals",
            {
                "name": name,
                "party_id": account.id,
                "contact_id": contacts[index % len(contacts)].id,
                "amount": str([280000, 450000, 175000, 320000, 620000, 240000, 180000][index]),
                "stage_id": stages[index % 4]["id"],
                "expected_close_date": (today + timedelta(days=7 + index * 4)).isoformat(),
                "tags": ["demo"],
            },
        )
        if index == 5:
            service.modify(db, user, "deals", deal.id, {"status": "won"})
        elif index == 6:
            service.modify(
                db,
                user,
                "deals",
                deal.id,
                {"status": "lost", "lost_reason": "Project postponed to next financial year."},
            )
    for index, name in enumerate(
        [
            "Follow up with Aditi",
            "Send revised proposal",
            "Northstar discovery call",
            "Review onboarding requirements",
            "Prepare quarterly account review",
            "Confirm renewal meeting",
        ]
    ):
        service.create(
            db,
            user,
            "activities",
            {
                "name": name,
                "type": ["task", "task", "call", "meeting", "task", "meeting"][index],
                "priority": "high" if index < 2 else "medium",
                "due_date": (today + timedelta(days=index - 1)).isoformat(),
                "entity_type": "parties",
                "entity_id": accounts[index % 5].id,
                "tags": ["demo"],
            },
        )
    for index, name in enumerate(
        [
            "Unable to add a new team member",
            "Invoice export formatting question",
            "Need help configuring notifications",
            "Request for account training",
        ]
    ):
        service.create(
            db,
            user,
            "tickets",
            {
                "name": name,
                "party_id": accounts[index].id,
                "contact_id": contacts[index].id,
                "priority": ["high", "medium", "low", "medium"][index],
                "status": ["Open", "New", "Pending", "Resolved"][index],
                "category": ["Access", "Billing", "Configuration", "Training"][index],
                "description": "Fictional support request for demonstrating the workspace.",
                "tags": ["demo"],
            },
        )
    service.create(
        db,
        user,
        "campaigns",
        {
            "name": "October partner outreach",
            "status": "active",
            "type": "email",
            "budget": "50000",
            "spent": "12500",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
            "tags": ["demo"],
            "notes": "Fictional campaign. No messages have been sent.",
        },
    )
    db.flush()

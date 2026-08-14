import os

import resend
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import ReturnDocument

load_dotenv()

MONGODB_URI = os.environ["MONGODB_URI"]
resend.api_key = os.environ["RESEND_API_KEY"]

client = MongoClient(MONGODB_URI)
db = client.get_default_database("portfolio")
stats_collection = db["stats"]
subscribers_collection = db["subscribers"]

STATS_ID = "global"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubscribeRequest(BaseModel):
    email: str


WELCOME_EMAIL_HTML = """\
<div style="background:#07080a;padding:40px 20px;font-family:'JetBrains Mono',Menlo,Consolas,monospace;">
  <div style="max-width:520px;margin:0 auto;background:#0b0d10;border:1px solid rgba(255,255,255,0.08);border-radius:16px;overflow:hidden;">
    <div style="padding:32px 32px 0 32px;">
      <div style="font-size:13px;letter-spacing:2px;color:#34d399;text-transform:uppercase;margin-bottom:12px;">
        AU<span style="color:#34d399;">.</span>dev &mdash; Newsletter
      </div>
      <h1 style="font-family:'Space Grotesk',Helvetica,Arial,sans-serif;color:#ffffff;font-size:26px;line-height:1.3;margin:0 0 16px 0;">
        Welcome to the loop 👋
      </h1>
      <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:0 0 20px 0;">
        You're officially subscribed to <strong style="color:#e2e8f0;">The Full-Stack AI Playbook</strong> &mdash;
        bi-weekly deep dives into production-grade AI architecture: the patterns, trade-offs, and
        failure modes that don't show up in the docs.
      </p>
      <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:0 0 28px 0;">
        First up, <strong style="color:#e2e8f0;">Issue #01: Stop Building Naive RAG</strong> &mdash;
        the three production-grade architectural patterns that separate fragile prototypes from
        systems that actually ship.
      </p>
      <a href="https://saianirudvarma.github.io/issue-01.html"
         style="display:inline-block;background:#34d399;color:#07080a;font-weight:600;font-size:14px;
                padding:12px 24px;border-radius:8px;text-decoration:none;margin-bottom:32px;">
        Read Issue #01 &rarr;
      </a>
    </div>
    <div style="border-top:1px solid rgba(255,255,255,0.08);padding:20px 32px;">
      <p style="color:#475569;font-size:12px;line-height:1.6;margin:0;">
        Sent to you because you subscribed at saianirudvarma.github.io. &mdash; Anirud Uppalapati
      </p>
    </div>
  </div>
</div>
"""


def _get_or_create_stats():
    stats = stats_collection.find_one({"_id": STATS_ID})
    if stats is None:
        stats = {"_id": STATS_ID, "likes": 0, "views": 0}
        stats_collection.insert_one(stats)
    return stats


@app.get("/api/stats")
def get_stats():
    stats = _get_or_create_stats()
    return {"likes": stats["likes"], "views": stats["views"]}


@app.post("/api/like")
def like():
    stats = stats_collection.find_one_and_update(
        {"_id": STATS_ID},
        {"$inc": {"likes": 1}, "$setOnInsert": {"views": 0}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return {"likes": stats["likes"]}


@app.post("/api/view")
def view():
    stats = stats_collection.find_one_and_update(
        {"_id": STATS_ID},
        {"$inc": {"views": 1}, "$setOnInsert": {"likes": 0}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return {"views": stats["views"]}


@app.post("/api/subscribe")
def subscribe(payload: SubscribeRequest):
    email = payload.email.lower()

    if subscribers_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Already subscribed!")

    subscribers_collection.insert_one({"email": email})

    resend.Emails.send(
        {
            "from": "onboarding@resend.dev",
            "to": email,
            "subject": "You're in — welcome to The Full-Stack AI Playbook 🚀",
            "html": WELCOME_EMAIL_HTML,
        }
    )

    return {"message": "Subscribed successfully!"}

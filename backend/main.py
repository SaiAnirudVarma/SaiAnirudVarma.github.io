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
            "subject": "Welcome to the newsletter!",
            "html": "<p>Thanks for subscribing — you're on the list.</p>",
        }
    )

    return {"message": "Subscribed successfully!"}

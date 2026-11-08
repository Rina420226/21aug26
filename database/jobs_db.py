"""Persistent checkpoints so long jobs (indexing, broadcast) survive a restart and can be resumed."""
from datetime import datetime
from database.ia_filterdb import db

col = db.jobs
RESUMABLE = ("running", "paused")


async def save_job(job_id, **fields):
    fields["updated"] = datetime.utcnow()
    await col.update_one({"_id": job_id}, {"$set": fields}, upsert=True)


async def get_job(job_id):
    return await col.find_one({"_id": job_id})


async def finish_job(job_id):
    await col.delete_one({"_id": job_id})


async def list_unfinished():
    return [j async for j in col.find({"status": {"$in": list(RESUMABLE)}}).sort("updated", -1).limit(20)]

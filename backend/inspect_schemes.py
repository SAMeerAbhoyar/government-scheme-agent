import asyncio
from sqlalchemy import select
from app.ingestion.run import get_working_session_maker
from app.models.scheme import Scheme

async def main():
    session_maker = await get_working_session_maker()
    async with session_maker() as db:
        res = await db.execute(select(Scheme))
        schemes = res.scalars().all()
        print(f"Total schemes in DB: {len(schemes)}")
        for s in schemes:
            print(f"- ID: {s.id} | Name: {s.name} | Status: {s.status}")
            print(f"  Rules: {s.eligibility_rules}")

if __name__ == "__main__":
    asyncio.run(main())

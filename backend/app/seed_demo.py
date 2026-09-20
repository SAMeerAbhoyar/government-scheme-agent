import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import Base, engine as pg_engine, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, Profile
from app.models.scheme import Scheme, SchemeChunk, SchemeVersion
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import MockEmbedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SeedDemo")

DEMO_USERS = [
    {
        "name": "Demo Admin",
        "email": "admin@demo.gov.in",
        "password": "Admin@123",
        "role": "admin",
        "profile": {}
    },
    {
        "name": "Rahul Sharma",
        "email": "rahul.student@demo.gov.in",
        "password": "User@123",
        "role": "user",
        "profile": {
            "age": 21,
            "gender": "male",
            "state": "Maharashtra",
            "district": "Pune",
            "education_level": "Undergraduate",
            "course": "B.Tech Engineering",
            "annual_income": 120000.0,
            "social_category": "SC",
            "disability": False,
            "bpl_card": False
        }
    },
    {
        "name": "Ramesh Patil",
        "email": "ramesh.farmer@demo.gov.in",
        "password": "User@123",
        "role": "user",
        "profile": {
            "age": 45,
            "gender": "male",
            "state": "Maharashtra",
            "district": "Nashik",
            "occupation": "Farmer",
            "annual_income": 180000.0,
            "social_category": "General",
            "land_holding_acres": 3.5,
            "bpl_card": False
        }
    },
    {
        "name": "Anita Deshmukh",
        "email": "anita.women@demo.gov.in",
        "password": "User@123",
        "role": "user",
        "profile": {
            "age": 32,
            "gender": "female",
            "state": "Maharashtra",
            "district": "Nagpur",
            "occupation": "Self-Employed",
            "annual_income": 95000.0,
            "social_category": "OBC",
            "bpl_card": True,
            "minority": False
        }
    }
]

DEMO_SCHEMES = [
    {
        "name": "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna",
        "department": "Higher and Technical Education",
        "category": "Education",
        "state": "Maharashtra",
        "benefits": "50% tuition fee and exam fee reimbursement for professional engineering and medical courses.",
        "source_url": "https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData?ID=1001",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 0.98,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=30),
        "eligibility_rules": {
            "rules": [
                {"field": "state", "op": "eq", "value": "Maharashtra"},
                {"field": "annual_income", "op": "lte", "value": 800000},
                {"field": "education_level", "op": "in", "value": ["Undergraduate", "Postgraduate"]}
            ]
        }
    },
    {
        "name": "PM Kisan Samman Nidhi",
        "department": "Ministry of Agriculture & Farmers Welfare",
        "category": "Agriculture",
        "state": "Central",
        "benefits": "Direct income support of Rs. 6,000 per year in 3 equal installments of Rs. 2,000.",
        "source_url": "https://pmkisan.gov.in",
        "application_url": "https://pmkisan.gov.in/RegistrationForm.aspx",
        "status": "active",
        "extraction_confidence": 0.99,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "rules": [
                {"field": "occupation", "op": "eq", "value": "Farmer"},
                {"field": "land_holding_acres", "op": "lte", "value": 5.0}
            ]
        }
    },
    {
        "name": "Majhi Kanya Bhagyeshree Scheme",
        "department": "Women and Child Development",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "benefits": "Financial assistance of Rs. 50,000 deposited in bank account in the name of the girl child.",
        "source_url": "https://womenchild.maharashtra.gov.in",
        "application_url": "https://womenchild.maharashtra.gov.in/apply",
        "status": "active",
        "extraction_confidence": 0.95,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "rules": [
                {"field": "state", "op": "eq", "value": "Maharashtra"},
                {"field": "gender", "op": "eq", "value": "female"},
                {"field": "annual_income", "op": "lte", "value": 750000}
            ]
        }
    },
    {
        "name": "Post-Matric Scholarship for SC Students (Maharashtra)",
        "department": "Social Justice and Special Assistance",
        "category": "Education",
        "state": "Maharashtra",
        "benefits": "100% tuition and maintenance allowance for SC students.",
        "source_url": "https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData?ID=1005",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 0.97,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=15),
        "eligibility_rules": {
            "rules": [
                {"field": "state", "op": "eq", "value": "Maharashtra"},
                {"field": "social_category", "op": "eq", "value": "SC"},
                {"field": "annual_income", "op": "lte", "value": 250000}
            ]
        }
    },
    {
        "name": "PMAY - Pradhan Mantri Awas Yojana (Urban)",
        "department": "Ministry of Housing and Urban Affairs",
        "category": "Housing",
        "state": "Central",
        "benefits": "Interest subsidy up to Rs 2.67 Lakhs on home loans for EWS/LIG families.",
        "source_url": "https://pmaymis.gov.in",
        "application_url": "https://pmaymis.gov.in",
        "status": "active",
        "extraction_confidence": 0.96,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "rules": [
                {"field": "bpl_card", "op": "eq", "value": True},
                {"field": "annual_income", "op": "lte", "value": 300000}
            ]
        }
    }
]

async def seed_demo():
    logger.info("Initializing DB connection for seeding...")
    session_maker = AsyncSessionLocal
    try:
        async with pg_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        logger.info("Postgres unavailable. Falling back to local SQLite 'scheme_agent.db'...")
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///scheme_agent.db", future=True)
        async with sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        session_maker = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)

    chunker = DocumentChunker()
    embedder = MockEmbedder()

    async with session_maker() as db:
        # Seed Demo Users
        for udata in DEMO_USERS:
            stmt = select(User).where(User.email == udata["email"])
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                user = User(
                    name=udata["name"],
                    email=udata["email"],
                    password_hash=get_password_hash(udata["password"]),
                    role=udata["role"]
                )
                db.add(user)
                await db.flush()

                if udata["profile"]:
                    prof = Profile(user_id=user.id, **udata["profile"])
                    db.add(prof)

                logger.info(f"Seeded User: {udata['name']} ({udata['email']}) - Role: {udata['role']}")

        # Seed Demo Schemes
        for sdata in DEMO_SCHEMES:
            stmt = select(Scheme).where(Scheme.name == sdata["name"])
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                scheme = Scheme(**sdata)
                db.add(scheme)
                await db.flush()

                # Add version
                version = SchemeVersion(
                    scheme_id=scheme.id,
                    content_hash="seed_demo_hash_v1",
                    extracted_json=sdata["eligibility_rules"]
                )
                db.add(version)

                # Add chunks & embeddings
                chunks = chunker.chunk_scheme(str(scheme.id), sdata, sdata["source_url"])
                for ch in chunks:
                    vec = await embedder.get_embedding(ch["text"])
                    chunk_obj = SchemeChunk(
                        scheme_id=scheme.id,
                        section=ch["section"],
                        text=ch["text"],
                        source_url=ch["source_url"],
                        embedding=vec
                    )
                    db.add(chunk_obj)

                logger.info(f"Seeded Scheme: {sdata['name']} (State: {sdata['state']}, Category: {sdata['category']})")

        await db.commit()
        logger.info("\n✅ Demo Seeding Complete! Pre-loaded 4 users (1 Admin + 3 Citizens) and 5 active schemes.")

if __name__ == "__main__":
    asyncio.run(seed_demo())

import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import Base, engine as pg_engine, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, Profile
from app.models.scheme import Scheme, SchemeChunk, SchemeVersion
from app.rag.embeddings import MockEmbedder
from app.services.matching import match_scheme_against_profile

logger = logging.getLogger(__name__)

SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL")
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD")

def get_demo_users() -> List[Dict[str, Any]]:
    users = []
    if SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD:
        users.append({
            "name": "Demo Admin",
            "email": SEED_ADMIN_EMAIL.strip(),
            "password": SEED_ADMIN_PASSWORD.strip(),
            "role": "admin",
            "profile": {}
        })

    users.extend([
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
                "rural_urban": "urban",
                "education_level": "Undergraduate",
                "course": "B.Tech Engineering",
                "occupation": "Student",
                "annual_income": 120000.0,
                "social_category": "SC",
                "disability": False,
                "minority": False,
                "bpl_card": False,
                "land_holding_acres": 0.0,
                "marital_status": "single"
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
                "rural_urban": "rural",
                "occupation": "Farmer",
                "annual_income": 85000.0,
                "social_category": "General",
                "bpl_card": False,
                "disability": False,
                "minority": False,
                "land_holding_acres": 2.5,
                "marital_status": "married"
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
                "rural_urban": "urban",
                "occupation": "Self-Employed",
                "annual_income": 95000.0,
                "social_category": "OBC",
                "bpl_card": True,
                "disability": False,
                "minority": False,
                "land_holding_acres": 0.0,
                "marital_status": "married"
            }
        },
        {
            "name": "Eknath Kulkarni",
            "email": "eknath.senior@demo.gov.in",
            "password": "User@123",
            "role": "user",
            "profile": {
                "age": 68,
                "gender": "male",
                "state": "Maharashtra",
                "district": "Shatara",
                "rural_urban": "rural",
                "occupation": "Retired",
                "annual_income": 45000.0,
                "social_category": "General",
                "bpl_card": True,
                "disability": False,
                "minority": False,
                "land_holding_acres": 0.5,
                "marital_status": "widowed"
            }
        }
    ])
    return users

DEMO_USERS = get_demo_users()

DEMO_SCHEMES = [
    # -------------------------------------------------------------
    # 5 Existing Seed Schemes
    # -------------------------------------------------------------
    {
        "name": "Rajarshi Chhatrapati Shahu Maharaj Shikshan Shulkh Shishyavrutti Yojna",
        "department": "Higher and Technical Education",
        "category": "Education",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. 50% tuition fee and exam fee reimbursement for professional engineering and medical courses.",
        "benefits": "50% tuition fee and exam fee reimbursement for professional engineering and medical courses.",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=30),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 800000.0, "source_quote": None, "verified": False},
                {"field": "education_level", "op": "in", "value": ["Undergraduate", "Postgraduate"], "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM Kisan Samman Nidhi",
        "department": "Ministry of Agriculture & Farmers Welfare",
        "category": "Agriculture",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Direct income support of Rs. 6,000 per year in 3 equal installments of Rs. 2,000.",
        "benefits": "Direct income support of Rs. 6,000 per year in 3 equal installments of Rs. 2,000.",
        "source_url": "https://pmkisan.gov.in",
        "application_url": "https://pmkisan.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "land_holding_acres", "op": "<=", "value": 5.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Majhi Kanya Bhagyeshree Scheme",
        "department": "Women and Child Development",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Financial assistance of Rs. 50,000 deposited in bank account in the name of the girl child.",
        "benefits": "Financial assistance of Rs. 50,000 deposited in bank account in the name of the girl child.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 750000.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Post-Matric Scholarship for SC Students (Maharashtra)",
        "department": "Social Justice and Special Assistance",
        "category": "Education",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. 100% tuition and maintenance allowance for SC students.",
        "benefits": "100% tuition and maintenance allowance for SC students.",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=15),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "social_category", "op": "==", "value": "SC", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 250000.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PMAY - Pradhan Mantri Awas Yojana (Urban)",
        "department": "Ministry of Housing and Urban Affairs",
        "category": "Housing",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Interest subsidy up to Rs 2.67 Lakhs on home loans for EWS/LIG families.",
        "benefits": "Interest subsidy up to Rs 2.67 Lakhs on home loans for EWS/LIG families.",
        "source_url": "https://pmaymis.gov.in",
        "application_url": "https://pmaymis.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "all_of": [
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 300000.0, "source_quote": None, "verified": False}
            ]
        }
    },

    # -------------------------------------------------------------
    # 25 New Curated Schemes
    # -------------------------------------------------------------
    # FARMERS (1-6)
    {
        "name": "Namo Shetkari Mahasanman Nidhi Yojana",
        "department": "Department of Agriculture",
        "category": "Agriculture",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Additional yearly income support for eligible farmers.",
        "benefits": "Additional yearly income support for eligible farmers.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "land_holding_acres", "op": ">", "value": 0.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Kisan Credit Card",
        "department": "Ministry of Agriculture & Farmers Welfare",
        "category": "Agriculture",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Short-term crop credit at concessional interest.",
        "benefits": "Short-term crop credit at concessional interest.",
        "source_url": "https://myscheme.gov.in",
        "application_url": "https://myscheme.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "all_of": [
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 18, "source_quote": None, "verified": False},
                {"field": "age", "op": "<=", "value": 75, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM Fasal Bima Yojana",
        "department": "Ministry of Agriculture & Farmers Welfare",
        "category": "Agriculture",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Crop insurance against yield loss at low premium.",
        "benefits": "Crop insurance against yield loss at low premium.",
        "source_url": "https://pmfby.gov.in",
        "application_url": "https://pmfby.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "all_of": [
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM-KUSUM",
        "department": "Ministry of New and Renewable Energy",
        "category": "Agriculture",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Subsidy for solar pumps and solar power on farmland.",
        "benefits": "Subsidy for solar pumps and solar power on farmland.",
        "source_url": "https://pmkusum.mnre.gov.in",
        "application_url": "https://pmkusum.mnre.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=75),
        "eligibility_rules": {
            "all_of": [
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "land_holding_acres", "op": ">", "value": 0.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Magel Tyala Shettale (Farm Pond)",
        "department": "Department of Agriculture",
        "category": "Agriculture",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Subsidy for building a farm pond.",
        "benefits": "Subsidy for building a farm pond.",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "land_holding_acres", "op": ">", "value": 0.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Dr. Babasaheb Ambedkar Krushi Swavalamban Yojana",
        "department": "Department of Agriculture",
        "category": "Agriculture",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Subsidy for irrigation facilities and farm development.",
        "benefits": "Subsidy for irrigation facilities and farm development.",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "occupation", "op": "==", "value": "Farmer", "source_quote": None, "verified": False},
                {"field": "social_category", "op": "==", "value": "SC", "source_quote": None, "verified": False}
            ]
        }
    },

    # GIRLS AND WOMEN (7-12)
    {
        "name": "Sukanya Samriddhi Yojana",
        "department": "Ministry of Women and Child Development",
        "category": "Social Welfare",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. High-interest savings account for a girl's education and marriage.",
        "benefits": "High-interest savings account for a girl's education and marriage.",
        "source_url": "https://indiapost.gov.in",
        "application_url": "https://indiapost.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=120),
        "eligibility_rules": {
            "all_of": [
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "age", "op": "<=", "value": 10, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Lek Ladki Yojana",
        "department": "Women and Child Development",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Staged payments from birth to age 18.",
        "benefits": "Staged payments from birth to age 18.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "age", "op": "<=", "value": 18, "source_quote": None, "verified": False},
                {
                    "any_of": [
                        {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False},
                        {"field": "annual_income", "op": "<=", "value": 100000.0, "source_quote": None, "verified": False}
                    ]
                }
            ]
        }
    },
    {
        "name": "Mukhyamantri Majhi Ladki Bahin Yojana",
        "department": "Women and Child Development",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Monthly financial assistance.",
        "benefits": "Monthly financial assistance.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=30),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 21, "source_quote": None, "verified": False},
                {"field": "age", "op": "<=", "value": 65, "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 250000.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM Ujjwala Yojana",
        "department": "Ministry of Petroleum and Natural Gas",
        "category": "Social Welfare",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Free LPG connection.",
        "benefits": "Free LPG connection.",
        "source_url": "https://pmuy.gov.in",
        "application_url": "https://pmuy.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "all_of": [
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 18, "source_quote": None, "verified": False},
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM Matru Vandana Yojana",
        "department": "Ministry of Women and Child Development",
        "category": "Social Welfare",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Cash incentive for pregnant and lactating mothers.",
        "benefits": "Cash incentive for pregnant and lactating mothers.",
        "source_url": "https://myscheme.gov.in",
        "application_url": "https://myscheme.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 19, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "AICTE Pragati Scholarship for Girls",
        "department": "Ministry of Education",
        "category": "Education",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Yearly scholarship for technical education.",
        "benefits": "Yearly scholarship for technical education.",
        "source_url": "https://scholarships.gov.in",
        "application_url": "https://scholarships.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "all_of": [
                {"field": "gender", "op": "==", "value": "female", "source_quote": None, "verified": False},
                {"field": "education_level", "op": "in", "value": ["Diploma", "Undergraduate"], "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 800000.0, "source_quote": None, "verified": False}
            ]
        }
    },

    # SCHOLARSHIPS (13-17)
    {
        "name": "Central Sector Scholarship for College and University Students",
        "department": "Ministry of Education",
        "category": "Education",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Yearly scholarship for meritorious students.",
        "benefits": "Yearly scholarship for meritorious students.",
        "source_url": "https://scholarships.gov.in",
        "application_url": "https://scholarships.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=30),
        "eligibility_rules": {
            "all_of": [
                {"field": "education_level", "op": "==", "value": "Undergraduate", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 450000.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM YASASVI Scholarship for OBC/EBC/DNT Students",
        "department": "Ministry of Social Justice and Empowerment",
        "category": "Education",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Scholarship for education.",
        "benefits": "Scholarship for education.",
        "source_url": "https://scholarships.gov.in",
        "application_url": "https://scholarships.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=40),
        "eligibility_rules": {
            "all_of": [
                {"field": "social_category", "op": "==", "value": "OBC", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 250000.0, "source_quote": None, "verified": False},
                {"field": "education_level", "op": "in", "value": ["School", "Undergraduate"], "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Post-Matric Scholarship for ST Students",
        "department": "Ministry of Tribal Affairs",
        "category": "Education",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Fee reimbursement and maintenance allowance.",
        "benefits": "Fee reimbursement and maintenance allowance.",
        "source_url": "https://scholarships.gov.in",
        "application_url": "https://scholarships.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=50),
        "eligibility_rules": {
            "all_of": [
                {"field": "social_category", "op": "==", "value": "ST", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 250000.0, "source_quote": None, "verified": False},
                {"field": "education_level", "op": "in", "value": ["Undergraduate", "Postgraduate"], "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "National Means-cum-Merit Scholarship",
        "department": "Ministry of Education",
        "category": "Education",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Yearly scholarship to prevent dropouts.",
        "benefits": "Yearly scholarship to prevent dropouts.",
        "source_url": "https://scholarships.gov.in",
        "application_url": "https://scholarships.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "education_level", "op": "==", "value": "School", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 350000.0, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Dr. Punjabrao Deshmukh Vastigruh Nirvah Bhatta Yojana",
        "department": "Higher and Technical Education",
        "category": "Education",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Hostel and maintenance allowance for students.",
        "benefits": "Hostel and maintenance allowance for students.",
        "source_url": "https://mahadbt.maharashtra.gov.in",
        "application_url": "https://mahadbt.maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=45),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "education_level", "op": "in", "value": ["Diploma", "Undergraduate", "Postgraduate"], "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 800000.0, "source_quote": None, "verified": False}
            ]
        }
    },

    # OLD PEOPLE (18-21)
    {
        "name": "Indira Gandhi National Old Age Pension Scheme",
        "department": "Ministry of Rural Development",
        "category": "Social Welfare",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Monthly old-age pension.",
        "benefits": "Monthly old-age pension.",
        "source_url": "https://nsap.nic.in",
        "application_url": "https://nsap.nic.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "all_of": [
                {"field": "age", "op": ">=", "value": 60, "source_quote": None, "verified": False},
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Shravanbal Seva Rajya Nivruttivetan Yojana",
        "department": "Social Justice and Special Assistance",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Monthly pension.",
        "benefits": "Monthly pension.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 65, "source_quote": None, "verified": False},
                {
                    "any_of": [
                        {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False},
                        {"field": "annual_income", "op": "<=", "value": 21000.0, "source_quote": None, "verified": False}
                    ]
                }
            ]
        }
    },
    {
        "name": "Sanjay Gandhi Niradhar Anudan Yojana",
        "department": "Social Justice and Special Assistance",
        "category": "Social Welfare",
        "state": "Maharashtra",
        "description": "Demo summary - confirm on the official portal. Monthly assistance.",
        "benefits": "Monthly assistance.",
        "source_url": "https://maharashtra.gov.in",
        "application_url": "https://maharashtra.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=60),
        "eligibility_rules": {
            "all_of": [
                {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": None, "verified": False},
                {"field": "annual_income", "op": "<=", "value": 21000.0, "source_quote": None, "verified": False},
                {
                    "any_of": [
                        {"field": "disability", "op": "==", "value": True, "source_quote": None, "verified": False},
                        {"field": "marital_status", "op": "==", "value": "widowed", "source_quote": None, "verified": False}
                    ]
                }
            ]
        }
    },
    {
        "name": "Ayushman Vay Vandana",
        "department": "Ministry of Health and Family Welfare",
        "category": "Health",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Health insurance cover for senior citizens.",
        "benefits": "Health insurance cover for senior citizens.",
        "source_url": "https://pmjay.gov.in",
        "application_url": "https://pmjay.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=120),
        "eligibility_rules": {
            "all_of": [
                {"field": "age", "op": ">=", "value": 70, "source_quote": None, "verified": False}
            ]
        }
    },

    # POOR PEOPLE (22-25)
    {
        "name": "Ayushman Bharat PM-JAY",
        "department": "Ministry of Health and Family Welfare",
        "category": "Health",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Health cover per family per year at empanelled hospitals.",
        "benefits": "Health cover per family per year at empanelled hospitals.",
        "source_url": "https://pmjay.gov.in",
        "application_url": "https://pmjay.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=120),
        "eligibility_rules": {
            "all_of": [
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "Antyodaya Anna Yojana",
        "department": "Ministry of Consumer Affairs, Food and Public Distribution",
        "category": "Social Welfare",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Subsidised foodgrain every month.",
        "benefits": "Subsidised foodgrain every month.",
        "source_url": "https://myscheme.gov.in",
        "application_url": "https://myscheme.gov.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=90),
        "eligibility_rules": {
            "all_of": [
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "MGNREGA",
        "department": "Ministry of Rural Development",
        "category": "Employment",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Guaranteed 100 days of wage employment.",
        "benefits": "Guaranteed 100 days of wage employment.",
        "source_url": "https://nrega.nic.in",
        "application_url": "https://nrega.nic.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=180),
        "eligibility_rules": {
            "all_of": [
                {"field": "rural_urban", "op": "==", "value": "rural", "source_quote": None, "verified": False},
                {"field": "age", "op": ">=", "value": 18, "source_quote": None, "verified": False}
            ]
        }
    },
    {
        "name": "PM Awas Yojana - Gramin",
        "department": "Ministry of Rural Development",
        "category": "Housing",
        "state": "Central",
        "description": "Demo summary - confirm on the official portal. Assistance to build a pucca house.",
        "benefits": "Assistance to build a pucca house.",
        "source_url": "https://pmayg.nic.in",
        "application_url": "https://pmayg.nic.in",
        "status": "active",
        "extraction_confidence": 1.0,
        "last_verified": None,
        "deadline_date": datetime.now(timezone.utc) + timedelta(days=120),
        "eligibility_rules": {
            "all_of": [
                {"field": "rural_urban", "op": "==", "value": "rural", "source_quote": None, "verified": False},
                {"field": "bpl_card", "op": "==", "value": True, "source_quote": None, "verified": False}
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
        logger.info("Postgres unavailable. Using local SQLite 'scheme_agent.db'...")
        sqlite_engine = create_async_engine("sqlite+aiosqlite:///scheme_agent.db", echo=settings.SQL_ECHO, future=True)
        async with sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_maker = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)

    embedder = MockEmbedder()

    async with session_maker() as db:
        # Check and clear legacy corrupted profiles if encrypted with old key
        try:
            stmt_test = select(Profile)
            await db.execute(stmt_test)
        except Exception as e_crypto:
            logger.warning(f"Clearing corrupted legacy profiles from DB: {e_crypto}")
            await db.execute(delete(Profile))
            await db.execute(delete(User))
            await db.commit()

        # 1. Delete junk scheme "Go to pmkisan.gov.in" if present
        stmt_junk = select(Scheme).where(Scheme.name == "Go to pmkisan.gov.in")
        res_junk = await db.execute(stmt_junk)
        junk_schemes = res_junk.scalars().all()
        for js in junk_schemes:
            logger.info(f"Removing junk scheme '{js.name}' ({js.id})")
            await db.delete(js)
        await db.commit()

        # 2. Seed / Upsert Demo Users Idempotently
        for udata in DEMO_USERS:
            stmt = select(User).where(User.email == udata["email"])
            res = await db.execute(stmt)
            existing_user = res.scalar_one_or_none()

            if existing_user:
                existing_user.name = udata["name"]
                existing_user.role = udata["role"]
                existing_user.password_hash = get_password_hash(udata["password"])
                user = existing_user
            else:
                user = User(
                    name=udata["name"],
                    email=udata["email"],
                    password_hash=get_password_hash(udata["password"]),
                    role=udata["role"]
                )
                db.add(user)
                await db.flush()

            # Upsert Profile
            if udata["profile"]:
                stmt_prof = select(Profile).where(Profile.user_id == user.id)
                res_prof = await db.execute(stmt_prof)
                existing_prof = res_prof.scalar_one_or_none()
                if existing_prof:
                    for k, v in udata["profile"].items():
                        setattr(existing_prof, k, v)
                else:
                    prof = Profile(user_id=user.id, **udata["profile"])
                    db.add(prof)

            logger.info(f"Seeded User: {udata['name']} ({udata['email']}) - Role: {udata['role']}")

        # 3. Seed / Upsert Demo Schemes Idempotently
        for sdata in DEMO_SCHEMES:
            stmt = select(Scheme).where(Scheme.name == sdata["name"])
            res = await db.execute(stmt)
            existing_scheme = res.scalar_one_or_none()

            if existing_scheme:
                existing_scheme.description = sdata["description"]
                existing_scheme.department = sdata["department"]
                existing_scheme.category = sdata["category"]
                existing_scheme.state = sdata["state"]
                existing_scheme.benefits = sdata["benefits"]
                existing_scheme.eligibility_rules = sdata["eligibility_rules"]
                existing_scheme.source_url = sdata["source_url"]
                existing_scheme.application_url = sdata["application_url"]
                existing_scheme.status = sdata["status"]
                existing_scheme.extraction_confidence = sdata["extraction_confidence"]
                existing_scheme.last_verified = sdata["last_verified"]
                existing_scheme.deadline_date = sdata["deadline_date"]

                # Clear existing chunks and versions
                await db.execute(delete(SchemeChunk).where(SchemeChunk.scheme_id == existing_scheme.id))
                await db.execute(delete(SchemeVersion).where(SchemeVersion.scheme_id == existing_scheme.id))
                await db.flush()
                scheme = existing_scheme
            else:
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

            # Add chunks (eligibility, benefits, overview) without calling LLM
            chunks_data = [
                {"section": "eligibility", "text": f"Eligibility for {scheme.name}: {sdata['description']}"},
                {"section": "benefits", "text": f"Benefits of {scheme.name}: {scheme.benefits}"},
                {"section": "overview", "text": f"{scheme.name} ({scheme.category}, {scheme.state}) offered by {scheme.department}. Official portal: {scheme.source_url}"}
            ]
            for ch in chunks_data:
                vec = await embedder.get_embedding(ch["text"])
                chunk_obj = SchemeChunk(
                    scheme_id=scheme.id,
                    section=ch["section"],
                    text=ch["text"],
                    source_url=scheme.source_url,
                    embedding=vec
                )
                db.add(chunk_obj)

            logger.info(f"Seeded Scheme: {sdata['name']} (State: {sdata['state']}, Category: {sdata['category']})")

        await db.commit()

        # 4. Verification and Summary Report
        total_schemes_stmt = select(func.count(Scheme.id)).where(Scheme.status == "active")
        total_schemes = (await db.execute(total_schemes_stmt)).scalar()

        category_counts_stmt = select(Scheme.category, func.count(Scheme.id)).where(Scheme.status == "active").group_by(Scheme.category)
        cat_counts = (await db.execute(category_counts_stmt)).all()

        print("\n" + "=" * 65)
        print("      SEED DEMO VERIFICATION SUMMARY")
        print("=" * 65)
        print(f"  Total Active Schemes in DB: {total_schemes} (Expected: 30)")
        print("\n  Schemes Breakdown by Category:")
        for cat, cnt in cat_counts:
            print(f"    - {cat:20s}: {cnt}")

        # Fetch all active schemes for Mode 2 evaluation
        all_schemes = (await db.execute(select(Scheme).where(Scheme.status == "active"))).scalars().all()

        # Fetch user profiles
        all_users = (await db.execute(select(User))).scalars().all()

        print("\n" + "=" * 65)
        print("      DEMO USERS MODE 2 MATCH EVALUATION SUMMARY")
        print("=" * 65)

        for u in all_users:
            stmt_p = select(Profile).where(Profile.user_id == u.id)
            p_obj = (await db.execute(stmt_p)).scalar_one_or_none()

            profile_dict = {}
            if p_obj:
                for col in Profile.__table__.columns:
                    if col.name not in ("id", "user_id"):
                        val = getattr(p_obj, col.name)
                        if val is not None:
                            profile_dict[col.name] = val

            counts = {"potentially_relevant": 0, "cannot_determine": 0, "not_matching": 0}
            match_details = []

            for s in all_schemes:
                m = match_scheme_against_profile(profile_dict, s)
                counts[m.status] += 1
                unmatched_info = ", ".join(m.missing_fields) if m.missing_fields else "All criteria passed"
                match_details.append((m.status, s.name, unmatched_info))

            print(f"\nUser: {u.name} ({u.email}) [Role: {u.role.upper()}]")
            print(f"  Status Summary: Potentially Relevant: {counts['potentially_relevant']} | Cannot Determine: {counts['cannot_determine']} | Not Matching: {counts['not_matching']}")
            print("  Detailed Scheme Evaluations:")
            for m_status, s_name, detail_reason in match_details:
                print(f"    [{m_status:20s}] {s_name:55s} | Reason: {detail_reason}")

        print("=" * 65 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_demo())

from typing import List, Dict, Any
import json

class DocumentChunker:
    def chunk_scheme(self, scheme_id: str, scheme_data: Dict[str, Any], source_url: str) -> List[Dict[str, Any]]:
        chunks = []

        # 1. Eligibility section
        rules = scheme_data.get("eligibility_rules")
        rules_str = json.dumps(rules) if isinstance(rules, dict) else str(rules or "")
        eligibility_text = f"Scheme: {scheme_data.get('name', '')}. Eligibility Rules: {rules_str}"
        chunks.append({
            "scheme_id": scheme_id,
            "section": "eligibility",
            "text": eligibility_text,
            "source_url": source_url
        })

        # 2. Benefits section
        benefits = scheme_data.get("benefits", "")
        if benefits:
            benefits_text = f"Scheme: {scheme_data.get('name', '')}. Benefits: {benefits}"
            chunks.append({
                "scheme_id": scheme_id,
                "section": "benefits",
                "text": benefits_text,
                "source_url": source_url
            })

        # 3. Documents section
        docs = scheme_data.get("documents")
        docs_str = ", ".join(docs) if isinstance(docs, list) else str(docs or "")
        if docs_str:
            docs_text = f"Scheme: {scheme_data.get('name', '')}. Required Documents: {docs_str}"
            chunks.append({
                "scheme_id": scheme_id,
                "section": "documents",
                "text": docs_text,
                "source_url": source_url
            })

        # 4. Other section (description + application process)
        desc = scheme_data.get("description", "")
        app_proc = scheme_data.get("application_process", "")
        other_text = f"Scheme: {scheme_data.get('name', '')}. Description: {desc}. Application Process: {app_proc}"
        chunks.append({
            "scheme_id": scheme_id,
            "section": "other",
            "text": other_text,
            "source_url": source_url
        })

        return chunks

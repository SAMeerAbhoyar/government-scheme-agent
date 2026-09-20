import os
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

class APIClientError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class APIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code in (200, 201):
            return response.json()
        elif response.status_code == 401:
            raise APIClientError("Session expired or unauthorized. Please log in again.", status_code=401)
        elif response.status_code == 403:
            raise APIClientError("Access forbidden. Admin role required.", status_code=403)
        elif response.status_code == 404:
            raise APIClientError("Resource not found.", status_code=404)
        elif response.status_code == 422:
            try:
                data = response.json()
                detail = data.get("detail", "Validation error.")
                if isinstance(detail, list):
                    msg = "; ".join([f"{item.get('loc', [])}: {item.get('msg', '')}" for item in detail if isinstance(item, dict)])
                    raise APIClientError(f"Validation Error: {msg}", status_code=422)
                raise APIClientError(f"Validation Error: {detail}", status_code=422)
            except APIClientError:
                raise
            except Exception:
                raise APIClientError("Unprocessable entity.", status_code=422)
        else:
            try:
                data = response.json()
                msg = data.get("detail", f"Server error ({response.status_code})")
            except Exception:
                msg = f"Server error ({response.status_code})"
            raise APIClientError(msg, status_code=response.status_code)

    def login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/login"
        payload = {"email": email, "password": password}
        try:
            res = httpx.post(url, json=payload, timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Unable to connect to backend server: {str(e)}", status_code=503)

    def signup(self, name: str, email: str, password: str, consent: bool) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/signup"
        payload = {"name": name, "email": email, "password": password, "consent": consent}
        try:
            res = httpx.post(url, json=payload, timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Unable to connect to backend server: {str(e)}", status_code=503)

    def get_me(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/me"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_profile(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/profile"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def update_profile(self, token: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/profile"
        try:
            res = httpx.put(url, json=profile_data, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def submit_profile_answers(self, token: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/profile/answers"
        try:
            res = httpx.post(url, json=answers, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def discover_query(self, token: str, prompt: str) -> Dict[str, Any]:
        url = f"{self.base_url}/discover/query"
        payload = {"prompt": prompt}
        try:
            res = httpx.post(url, json=payload, headers=self._get_headers(token), timeout=25.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def discover_profile(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/discover/profile"
        payload = {}
        try:
            res = httpx.post(url, json=payload, headers=self._get_headers(token), timeout=25.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def save_scheme(self, token: str, scheme_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/saved/{scheme_id}"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def unsave_scheme(self, token: str, scheme_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/saved/{scheme_id}"
        try:
            res = httpx.delete(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_saved_schemes(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/saved"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_search_history(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/history"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_notifications(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/notifications"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def mark_notification_read(self, token: str, notification_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/notifications/{notification_id}/read"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def mark_all_notifications_read(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/notifications/read-all"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def submit_feedback(self, token: str, recommendation_id: str, useful: bool, comment: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/feedback"
        payload = {"recommendation_id": recommendation_id, "useful": useful, "comment": comment}
        try:
            res = httpx.post(url, json=payload, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_admin_overview(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/admin/overview"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_admin_unverified(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/unverified"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def verify_admin_scheme(self, token: str, scheme_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/admin/schemes/{scheme_id}/verify"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def edit_admin_scheme_rules(self, token: str, scheme_id: str, rules_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/admin/schemes/{scheme_id}/edit-rules"
        try:
            res = httpx.post(url, json=rules_data, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def reject_admin_scheme(self, token: str, scheme_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/admin/schemes/{scheme_id}/reject"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_admin_changes(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/changes"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_admin_source_health(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/source-health"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def get_admin_feedback(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/admin/feedback"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def trigger_admin_ingest_now(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/admin/ingest-now"
        try:
            res = httpx.post(url, headers=self._get_headers(token), timeout=60.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def export_account(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/account/export"
        try:
            res = httpx.get(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

    def delete_account(self, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/account"
        try:
            res = httpx.delete(url, headers=self._get_headers(token), timeout=10.0)
            return self._handle_response(res)
        except httpx.RequestError as e:
            raise APIClientError(f"Connection error: {str(e)}", status_code=503)

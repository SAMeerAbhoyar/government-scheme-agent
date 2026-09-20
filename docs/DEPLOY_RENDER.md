# Deploying to Render (Blueprint Deployment)

This guide provides step-by-step instructions to deploy the Automated Government Scheme Agent to [Render](https://render.com) as two distinct web services (Backend API and Gradio UI) from a single GitHub repository.

---

## Overview

The deployment uses Render's **Infrastructure as Code (Blueprint)** feature defined in [`render.yaml`](file:///c:/Users/Sameera%20Bhoyar/OneDrive/Desktop/FlexiProject/government-scheme-agent/render.yaml).

| Service | Type | Root Directory | Build Command | Start Command | Health Check |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **scheme-backend** | Web Service | `backend` | `pip install -r requirements.txt` | `bash ../scripts/start_backend.sh` | `/health` |
| **scheme-ui** | Web Service | `.` | `pip install -r ui/requirements.txt` | `python ui/app.py` | N/A |

---

## Prerequisites

1. A **Render account** (sign up at [render.com](https://render.com)).
2. A **GitHub repository** containing this codebase.
3. Cryptographic secret keys generated for your deployment:
   - **`JWT_SECRET_KEY`**: A secure random string (minimum 32 characters).
   - **`ENCRYPTION_KEY`**: A 32-byte URL-safe base64 Fernet key.

---

## Generating Required Secrets Locally

Run the following command in Python to generate both keys:

```bash
python -c "import secrets, cryptography.fernet; print('JWT_SECRET_KEY=' + secrets.token_hex(32)); print('ENCRYPTION_KEY=' + cryptography.fernet.Fernet.generate_key().decode())"
```

---

## Click-by-Click Deployment Steps

### Step 1: Connect Repository to Render Blueprint
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click the **New +** button in the top right corner and select **Blueprint**.
3. Connect your GitHub account (if not already connected) and select your repository: `government-scheme-agent`.
4. Give your Blueprint instance a name (e.g., `scheme-agent-production`).
5. Render will automatically parse `render.yaml` and detect two web services (`scheme-backend` and `scheme-ui`).

---

### Step 2: Configure Environment Variables

Render will prompt you to fill in all environment variables marked with `sync: false`.

#### A. Backend Service Environment Variables (`scheme-backend`)

| Variable Name | Description | Example / Instructions | Required? |
| :--- | :--- | :--- | :--- |
| `PYTHON_VERSION` | Python runtime version | `3.11.6` (automatically set by blueprint) | Yes |
| `ENVIRONMENT` | Application mode | `production` (automatically set by blueprint) | Yes |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | Paste generated hex string (>= 32 chars) | **Yes** |
| `ENCRYPTION_KEY` | Fernet key for encrypting user PII | Paste generated base64 Fernet key | **Yes** |
| `LLM_API_KEY` | Gemini API key for scheme matching/chat | Your Google AI Studio API key | Optional (defaults to mock if unset) |
| `SEED_ADMIN_EMAIL` | Initial admin user email | e.g. `admin@demo.gov.in` | Optional (skips admin if unset) |
| `SEED_ADMIN_PASSWORD` | Initial admin user password | e.g. `AdminSecurePassword#123` | Optional (skips admin if unset) |

---

#### B. UI Service Environment Variables (`scheme-ui`)

| Variable Name | Description | Example / Instructions | Required? |
| :--- | :--- | :--- | :--- |
| `PYTHON_VERSION` | Python runtime version | `3.11.6` (automatically set by blueprint) | Yes |
| `GRADIO_SERVER_NAME` | Host binding for Gradio | `0.0.0.0` (automatically set by blueprint) | Yes |
| `API_BASE_URL` | Full URL of backend service | `https://scheme-backend.onrender.com` | **Yes** |

> [!TIP]
> After `scheme-backend` finishes deploying, copy its public Render URL (e.g., `https://scheme-backend.onrender.com`) and paste it as the `API_BASE_URL` in the `scheme-ui` service environment settings.

---

### Step 3: Deploy & Verify

1. Click **Apply** to trigger the initial deployment.
2. Monitor build logs:
   - **`scheme-backend`**: Runs `alembic upgrade head`, seeds database via `python -m app.seed_demo`, and launches `uvicorn` on `$PORT`.
   - **`scheme-ui`**: Installs dependencies and launches Gradio UI on `$PORT`.
3. Verify Backend Health:
   - Open `https://<your-backend-url>.onrender.com/health` in your browser. It should return `{"status": "healthy"}`.
4. Verify UI Application:
   - Open `https://<your-ui-url>.onrender.com`.
   - Click one of the demo profile buttons (e.g., **Student (Rahul)**) to verify frontend-backend API integration.

---

## Maintenance & Redeployment

- **Database Persistence Notice**: The SQLite database file (`scheme_agent.db`) is recreated and re-seeded on service restarts/redeployments. This design is optimized for zero-configuration demo environments.
- **Manual Redeploy**: In the Render Dashboard, click **Manual Deploy** > **Deploy latest commit** on either service if needed.

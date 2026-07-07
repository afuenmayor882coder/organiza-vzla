# Organiza Vzla

**NGO Inventory & Financial Control Platform**

Organiza Vzla is a lightweight, zero-cost web application designed to help NGOs track physical inventory (donations of food, medicine, hygiene products, clothing, and more) and financial cash flows (income, expenses) following NIIF (IFRS) standards.

## Features

- **Donation Registration** — Log incoming donations by category, packaging format, and quantity, with optional expiration tracking.
- **Inventory Exits** — Record distributions to beneficiaries with full recipient and reason tracking.
- **NIIF Cash Flow** — Register financial transactions classified under NIIF categories (Operating, Investing, Financing) and import bank statements.
- **Dashboard** — Visual overview with alerts (expiring items, low stock), inventory charts, and cash-flow analysis.
- **Multi-Tenant** — Multiple organizations can use the same app; each sees only its own data.
- **Authentication** — Email/password login with Admin and User roles.

## Tech Stack

| Component | Technology |
|---|---|
| Frontend & UI | Streamlit (Python) |
| Database | MongoDB Atlas (Free Tier) |
| Hosting | Streamlit Community Cloud |
| Auth | streamlit-authenticator |

## Getting Started

1. Clone this repo.
2. Create a virtual environment and install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up a free MongoDB Atlas cluster and paste your connection string into `.streamlit/secrets.toml`.
4. Run the app locally:
   ```
   streamlit run app.py
   ```

## Deployment

The `main` branch is connected to Streamlit Community Cloud. Merging a pull request into `main` triggers an automatic re-deploy.

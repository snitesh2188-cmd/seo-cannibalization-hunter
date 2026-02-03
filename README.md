# seo-cannibalization-hunter
Find URL and Keyword cannibalisation based on GSC data. 

# 🚀 Enterprise SEO: Cannibalization Hunter

**Stop your website from eating its own lunch.**

This is a free, open-source Python tool designed for Enterprise SEOs. It uses the Google Search Console (GSC) API to identify **Keyword Cannibalization**—where multiple pages on your site compete for the same keywords, hurting your rankings and wasting crawl budget.

## 🎥 Video Tutorial
**[Coming Soon]**

---

## ✨ Features
* **100% Free:** No monthly subscriptions. Runs locally on your machine.
* **Enterprise Scale:** Analyzes up to 25,000 top queries.
* **Smart Filters:** Toggle between "Branded" and "Non-Branded" keywords.
* **History Tracking:** Automatically logs your progress to a CSV graph.
* **Interactive Dashboard:** Built with Streamlit for a clean, code-free UI.

---

## ⚙️ Installation Guide

### 1. Download the Code
Clone this repository or download the ZIP file and extract it to a folder (e.g., `seo-tools`).

### 2. Install Dependencies
Open your terminal, navigate to the folder, and run:

pip install -r requirements.txt

---

**Set Up Google Cloud Credentials**
### 1.Go to the Google Cloud Console.
### 2.Create a Project and Enable "Google Search Console API".
### 3.Create a Service Account (e.g., "seo-bot") and download the JSON key.
### 4.Rename the key to credentials.json and place it in the same folder as dashboard.py.
Important: Copy the bot's email (seo-bot@...) and add it as a User (Owner) in your Google Search Console property settings.

---

**## ⚙️ How to Run**

streamlit run dashboard.py

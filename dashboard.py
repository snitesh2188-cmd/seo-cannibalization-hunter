import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="GSC Enterprise SEO Tool", layout="wide")

st.title("🚀 Enterprise SEO: Cannibalization Tracker")
st.markdown("Analyze keyword conflicts and track your progress over time.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("1. API Settings")
property_uri = st.sidebar.text_input("GSC Property", value="sc-domain:growthops.asia", help="e.g. sc-domain:example.com")

# Country List (ISO-3 Codes)
country_map = {
    "Worldwide (No Filter)": None,
    "Singapore": "sgp",
    "Australia": "aus",
    "United States": "usa",
    "United Kingdom": "gbr",
    "India": "ind",
    "Malaysia": "mys",
    "Indonesia": "idn",
    "Philippines": "phl",
    "Thailand": "tha",
    "Vietnam": "vnm"
}
selected_country = st.sidebar.selectbox("Target Country", options=list(country_map.keys()))

st.sidebar.header("2. Analysis Filters")

# Timeline
time_option = st.sidebar.selectbox(
    "Date Range",
    ("Last 28 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months")
)

# Position Filter
max_position = st.sidebar.slider("Max Average Position", min_value=10, max_value=100, value=30, step=10, help="Only analyze keywords ranking better than this position.")

# Brand Logic
st.sidebar.subheader("Keyword Filtering")
brand_mode = st.sidebar.radio("Show me:", ("Non-Branded Only", "Branded Only", "All Keywords"))
branded_input = st.sidebar.text_area("Your Brand Terms (comma separated)", value="growthops, growth ops")

# --- DATE LOGIC ---
today = datetime.date.today()
end_date_str = today.strftime("%Y-%m-%d")

if time_option == "Last 28 Days":
    delta = 28
elif time_option == "Last 3 Months":
    delta = 90
elif time_option == "Last 6 Months":
    delta = 180
else:
    delta = 365

start_date = today - datetime.timedelta(days=delta)
start_date_str = start_date.strftime("%Y-%m-%d")

# --- HELPER FUNCTIONS ---

def get_clean_domain_name(uri):
    return uri.replace("sc-domain:", "").replace("https://", "").replace("/", "").replace("www.", "")

def fetch_gsc_data(site_url, start, end, country_code=None, keys_path='credentials.json'):
    try:
        creds = service_account.Credentials.from_service_account_file(
            keys_path, scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('searchconsole', 'v1', credentials=creds)
        
        request_body = {
            'startDate': start,
            'endDate': end,
            'dimensions': ['query', 'page'],
            'rowLimit': 25000, 
            'startRow': 0
        }

        if country_code:
            request_body['dimensionFilterGroups'] = [{
                'filters': [{
                    'dimension': 'country',
                    'operator': 'equals',
                    'expression': country_code
                }]
            }]
        
        response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
        
        if 'rows' not in response:
            return None
            
        data = []
        for row in response['rows']:
            data.append({
                'query': row['keys'][0],
                'url': row['keys'][1],
                'clicks': row['clicks'],
                'impressions': row['impressions'],
                'ctr': row['ctr'],
                'position': row['position']
            })
        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def process_cannibalization(df, brand_terms_str, mode, max_pos):
    # 1. Filter by Position
    df = df[df['position'] <= max_pos]
    
    # 2. Handle Brand Filtering
    if brand_terms_str:
        terms = [t.strip().lower() for t in brand_terms_str.split(',') if t.strip()]
        pattern = '|'.join(terms)
        
        if pattern:
            if mode == "Non-Branded Only":
                df = df[~df['query'].str.contains(pattern, case=False, regex=True)]
            elif mode == "Branded Only":
                df = df[df['query'].str.contains(pattern, case=False, regex=True)]
            
    if df.empty:
        return pd.DataFrame()

    # 3. Detect Cannibalization
    query_counts = df.groupby('query')['url'].nunique()
    cannibalized_queries = query_counts[query_counts > 1].index
    
    if len(cannibalized_queries) == 0:
        return pd.DataFrame()
        
    suspicious_df = df[df['query'].isin(cannibalized_queries)].copy()
    suspicious_df = suspicious_df.sort_values(by=['query', 'impressions'], ascending=[True, False])
    
    return suspicious_df

def save_historical_data(domain, mode, metrics):
    """Updates the history CSV smartly (Updates today's row if it exists, instead of appending duplicates)"""
    folder = "cannibalisation/history"
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    clean_mode = mode.replace(" ", "").lower()
    filename = f"{folder}/history-{domain}-{clean_mode}.csv"
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    new_row_data = {
        "Date": today_str,
        "Conflicted Keywords": metrics["keywords"],
        "Total URLs Involved": metrics["urls"],
        "Wasted Impressions": metrics["impressions"],
        "Potential Clicks (Est)": metrics["clicks_opportunity"]
    }
    
    if os.path.exists(filename):
        try:
            # 1. Read the existing history
            df_history = pd.read_csv(filename)
            
            # 2. Check if we already have a row for today
            if today_str in df_history['Date'].values:
                # UPDATE the existing row (so you don't get duplicates if you run 2x a day)
                idx = df_history.index[df_history['Date'] == today_str].tolist()[0]
                df_history.at[idx, "Conflicted Keywords"] = metrics["keywords"]
                df_history.at[idx, "Total URLs Involved"] = metrics["urls"]
                df_history.at[idx, "Wasted Impressions"] = metrics["impressions"]
                df_history.at[idx, "Potential Clicks (Est)"] = metrics["clicks_opportunity"]
            else:
                # APPEND a new row if today is new
                new_df = pd.DataFrame([new_row_data])
                df_history = pd.concat([df_history, new_df], ignore_index=True)
            
            # 3. Save the clean, updated table back to the file
            df_history.to_csv(filename, index=False)
            
        except Exception as e:
            st.error(f"⚠️ Error reading history file: {e}. Starting fresh.")
            df_new = pd.DataFrame([new_row_data])
            df_new.to_csv(filename, index=False)
    else:
        # Create new file if it doesn't exist
        df_new = pd.DataFrame([new_row_data])
        df_new.to_csv(filename, index=False)
    
    return filename

# --- MAIN APP LOGIC ---

# 1. GRAPHING SECTION (Shows strictly before processing if history exists)
clean_name = get_clean_domain_name(property_uri)
clean_mode = brand_mode.replace(" ", "").lower()
history_file = f"cannibalisation/history/history-{clean_name}-{clean_mode}.csv"

if os.path.exists(history_file):
    st.subheader(f"📈 Progress Over Time: {clean_name}")
    
    hist_df = pd.read_csv(history_file)
    hist_df['Date'] = pd.to_datetime(hist_df['Date'])
    hist_df = hist_df.set_index('Date') # Set date as X-axis
    
    # Multi-select for metrics
    available_metrics = ["Conflicted Keywords", "Total URLs Involved", "Wasted Impressions", "Potential Clicks (Est)"]
    selected_metrics = st.multiselect("Select Metrics to Visualize:", available_metrics, default=["Conflicted Keywords", "Potential Clicks (Est)"])
    
    if selected_metrics:
        st.line_chart(hist_df[selected_metrics])
    
    st.divider()

# 2. PROCESSING BUTTON
if st.sidebar.button("Start Processing"):
    with st.spinner(f'Connecting to GSC ({selected_country if selected_country else "Worldwide"})...'):
        
        if not os.path.exists('credentials.json'):
            st.error("❌ 'credentials.json' file not found!")
            st.stop()
            
        c_code = country_map[selected_country]
        raw_df = fetch_gsc_data(property_uri, start_date_str, end_date_str, country_code=c_code)
        
        if raw_df is not None and not raw_df.empty:
            
            report_df = process_cannibalization(raw_df, branded_input, brand_mode, max_position)
            
            if not report_df.empty:
                # Calculate Metrics
                uniq_keywords = report_df['query'].nunique()
                uniq_urls = report_df['url'].nunique()
                total_wasted_impressions = int(report_df['impressions'].sum())
                potential_clicks = int(total_wasted_impressions * 0.2) # 20% rule
                
                # Display Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Conflicted Keywords", uniq_keywords)
                c2.metric("Total URLs", uniq_urls)
                c3.metric("Wasted Impressions", f"{total_wasted_impressions:,}")
                c4.metric("Potential Clicks (+20% CTR)", f"{potential_clicks:,}")

                # Save to History
                save_historical_data(clean_name, brand_mode, {
                    "keywords": uniq_keywords,
                    "urls": uniq_urls,
                    "impressions": total_wasted_impressions,
                    "clicks_opportunity": potential_clicks
                })
                
                st.divider()
                st.subheader("🕵️ Detailed Cannibalization Report")
                
                st.dataframe(
                    report_df,
                    use_container_width=True,
                    column_config={
                        "url": st.column_config.LinkColumn("URL"), 
                        "clicks": st.column_config.NumberColumn("Clicks", format="%d"),
                        "impressions": st.column_config.NumberColumn("Impr.", format="%d"),
                        "ctr": st.column_config.NumberColumn("CTR", format="%.2f%%"),
                        "position": st.column_config.NumberColumn("Avg Pos", format="%.1f"),
                    },
                    hide_index=True
                )
                
                # Save Individual Report
                output_folder = "cannibalisation/output"
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                
                filename = f"{clean_name}-{clean_mode}-{today.strftime('%b-%Y')}.csv"
                full_path = os.path.join(output_folder, filename)
                report_df.to_csv(full_path, index=False)
                
                st.download_button(
                    label="⬇️ Download CSV Report",
                    data=report_df.to_csv(index=False).encode('utf-8'),
                    file_name=filename,
                    mime="text/csv"
                )
                
                st.success("✅ History updated! Refresh the page to see the new data point on the graph.")
                
            else:
                st.balloons()
                st.success(f"🎉 No cannibalization found for {brand_mode} (Pos < {max_position})!")
        else:
            st.warning("⚠️ No data returned. Check filters/permissions.")
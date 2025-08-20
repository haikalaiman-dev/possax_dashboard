import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import random
from datetime import datetime, timedelta
from mock_data import df_users, df_stores, df_subscriptions

st.set_page_config(page_title="📊 Admin Dashboard", layout="wide")

st.title("📊 Possax Admin Dashboard")


# ======================================================
# GLOBAL FILTERS (top of page)
# ======================================================
with st.popover("🔍 Filters"):
    c1, c2 = st.columns(2)

    # Expiry window (for expiring tab/analytics)
    expiry_window = c1.selectbox("Expiry Window", ["All", "7 days", "14 days", "30 days", "Expired"], index=0)
    
    # Date range (users: CreatedAt, stores: CreatedAt)
    min_date = min(df_users["CreatedAt"].min(), df_stores["CreatedAt"].min()).date()
    max_date = max(df_users["CreatedAt"].max(), df_stores["CreatedAt"].max()).date()
    date_range = c2.date_input("Date Range", [min_date, max_date])
    
    c3, c4, c5= st.columns(3)
    
    # City
    city_options = sorted(df_users["City"].unique().tolist())
    city_filter = c3.multiselect("City", city_options, default=city_options)
    
    # Subscription type (stores)
    sub_options = sorted(df_stores["SubscriptionType"].unique().tolist())
    sub_filter = c4.multiselect("Subscription Type", sub_options, default=sub_options)

    # User role
    role_options = sorted(df_users["Role"].unique().tolist())
    role_filter = c5.multiselect("User Role", role_options, default=role_options)

# Apply filters
users_f = df_users.copy()
stores_f = df_stores.copy()
subs_f = df_subscriptions.copy()

if len(date_range) == 2:
    start, end = [pd.to_datetime(d) for d in date_range]
    users_f = users_f[(users_f["CreatedAt"] >= start) & (users_f["CreatedAt"] <= end)]
    stores_f = stores_f[(stores_f["CreatedAt"] >= start) & (stores_f["CreatedAt"] <= end)]

if sub_filter:
    stores_f = stores_f[stores_f["SubscriptionType"].isin(sub_filter)]

if role_filter:
    users_f = users_f[users_f["Role"].isin(role_filter)]

if city_filter:
    users_f = users_f[users_f["City"].isin(city_filter)]

# Sync subs with filtered stores
subs_f = subs_f[subs_f["StoreID"].isin(stores_f["StoreID"])]

# ======================================================
# METRICS
# ======================================================
with st.container():
    with st.expander("⚡ Key Metrics", expanded=True):
        m1, m2, m3, m4, m5 = st.columns(5)

        total_users = len(users_f)
        total_stores = len(stores_f)
        total_pro_stores = (stores_f["SubscriptionType"] == "Pro").sum()
        total_basic_stores = (stores_f["SubscriptionType"] == "Basic").sum()
        total_income = subs_f[subs_f["Type"].isin(["Pro", "Basic"])]["AmountPaid"].sum()

        m1.metric("Total Users", f"{total_users:,}", "+12 users", border=True)
        m2.metric("Total Stores", f"{total_stores:,}", "+5 stores", border=True )
        m3.metric("Pro Stores", f"{total_pro_stores}", "+6 Pro Users", border=True)
        m4.metric("Basic Stores", f"{total_basic_stores}", "-4 Basic Users", border=True)
        m5.metric("Total Income (IDR)", f"{total_income:,.0f}","+155000",border=True)



tab1, tab2 = st.tabs(["📉 Charts & Infographics", "📋 Detailed Data"])

# ======================================================
# CHARTS & GRAPHICS
# ======================================================
with tab1:
    #with st.expander("📉 Charts & Infographics", expanded=True):

        # Trendline: users by subscription type (derived) over time
        # Group by month and UserSubscriptionType
        uf = users_f.copy()
        uf["Month"] = uf["CreatedAt"].dt.to_period("M").dt.to_timestamp()
        user_sub_trend = (
            uf.groupby(["Month", "UserSubscriptionType"])
            .size().reset_index(name="UserCount")
        )

        chart_user_sub_trend = (
            alt.Chart(user_sub_trend)
            .mark_line(point=True)
            .encode(
                x=alt.X("Month:T", title="Month"),
                y=alt.Y("UserCount:Q", title="Users"),
                color=alt.Color("UserSubscriptionType:N", title="Subscription"),
                tooltip=["Month:T", "UserSubscriptionType:N", "UserCount:Q"]
            )
            .properties(title="Users by Subscription Type Over Time")
        )

        # Trend: store count over time (by created)
        sf = stores_f.copy()
        sf["Month"] = sf["CreatedAt"].dt.to_period("M").dt.to_timestamp()
        store_trend = sf.groupby("Month").size().reset_index(name="StoreCount")
        chart_store_trend = (
            alt.Chart(store_trend)
            .mark_line(point=True)
            .encode(
                x=alt.X("Month:T", title="Month"),
                y=alt.Y("StoreCount:Q", title="Stores"),
                tooltip=["Month:T", "StoreCount:Q"]
            )
            .properties(title="Store Count Over Time")
        )

        # Trend: user count over time (by created)
        user_trend = uf.groupby("Month").size().reset_index(name="UserCount")
        chart_user_trend = (
            alt.Chart(user_trend)
            .mark_line(point=True)
            .encode(
                x=alt.X("Month:T", title="Month"),
                y=alt.Y("UserCount:Q", title="Users"),
                tooltip=["Month:T", "UserCount:Q"]
            )
            .properties(title="User Count Over Time")
        )

        c1, c2, c3 = st.columns(3)
        c1.altair_chart(chart_user_sub_trend, use_container_width=True)
        c2.altair_chart(chart_store_trend, use_container_width=True)
        c3.altair_chart(chart_user_trend, use_container_width=True)

        # Leaderboards in three columns with their own expanders
        l1, l2, l3 = st.columns(3)

        with l1:
            with st.expander("🏆 Top 10 Most Active Users", expanded=True):
                top_active = users_f.nlargest(10, "TotalTransactions")[["Name", "TotalTransactions"]]
                st.dataframe(top_active, use_container_width=True)

        with l2:
            with st.expander("🏙 Top 10 Cities by User Count", expanded=True):
                top_cities = (
                    users_f["City"].value_counts().head(10).reset_index()
                )
                top_cities.columns = ["City", "User Count"]
                st.dataframe(top_cities, use_container_width=True)

        with l3:
            with st.expander("🔗 Top 10 Referral Codes Used", expanded=True):
                top_refs = (
                    users_f["ReferralCode"].dropna().value_counts().head(10).reset_index()
                )
                top_refs.columns = ["Referral Code", "Usage Count"]
                st.dataframe(top_refs, use_container_width=True)

        # Pie charts
        p1, p2 = st.columns(2)
        with p1:
            pie_stores = (
                alt.Chart(stores_f)
                .mark_arc()
                .encode(theta="count()", color=alt.Color("SubscriptionType:N", title="Subscription"))
                .properties(title="Stores by Subscription Type")
            )
            st.altair_chart(pie_stores, use_container_width=True)

        with p2:
            pie_roles = (
                alt.Chart(users_f)
                .mark_arc()
                .encode(theta="count()", color=alt.Color("Role:N", title="Role"))
                .properties(title="Users by Role")
            )
            st.altair_chart(pie_roles, use_container_width=True)

        # Map of user locations
        st.markdown("#### 🗺️ User Locations")
        map_df = users_f.rename(columns={"Latitude": "lat", "Longitude": "lon"})
        st.map(map_df[["lat", "lon"]])

# ======================================================
# ADMIN: CREATE SUBSCRIPTION TRANSACTION (st.dialog)
# ======================================================
def create_subs():
    with st.form("create_subscription_form", clear_on_submit=True):
        st.write("Create a subscription transaction for users (single or bulk).")
        # Select users (multi)
        selected_users = st.multiselect(
            "Select User(s)", options=df_users["UserID"].tolist(),
            format_func=lambda uid: f"{uid} — {df_users.loc[df_users['UserID']==uid,'Name'].values[0]}"
        )
        # Apply to all stores of selected users or pick stores
        apply_scope = st.radio("Apply to", ["All stores of selected users", "Specific stores"], index=0)
        specific_store_ids = []
        if apply_scope == "Specific stores":
            specific_store_ids = st.multiselect(
                "Select Store(s)",
                options=df_stores["StoreID"].tolist(),
                format_func=lambda sid: f"{sid} — {df_stores.loc[df_stores['StoreID']==sid,'StoreName'].values[0]}"
            )

        sub_type = st.selectbox("Subscription Type", ["Pro", "Basic", "Trial", "Non-Paid"], index=0)
        duration_days = st.selectbox("Duration (days)", [30, 90, 180, 365], index=0)
        # Suggested amount
        suggested = 400_000 if sub_type == "Pro" else (200_000 if sub_type == "Basic" else 0)
        amount = st.number_input("Amount (IDR)", min_value=0, value=suggested, step=50_000)

        submitted = st.form_submit_button("Create Transaction")
        if submitted:
            # Resolve target stores
            target_store_ids = set()
            if apply_scope == "All stores of selected users":
                for uid in selected_users:
                    # any store owned by or associated with the user
                    owned = df_stores[df_stores["OwnerUserID"] == uid]["StoreID"].tolist()
                    # plus stores listed in user's "Stores" association
                    assoc = df_users.loc[df_users["UserID"] == uid, "Stores"].values[0]
                    target_store_ids.update(owned + assoc)
            else:
                target_store_ids.update(specific_store_ids)

            target_store_ids = sorted(list(target_store_ids))
            st.success(
                f"Created {sub_type} ({duration_days} days) subscription transaction "
                f"for {len(target_store_ids)} store(s); amount: IDR {amount:,.0f}."
            )
            if target_store_ids:
                st.write("Target Stores:", target_store_ids)

# ======================================================
# ADMIN: DELETE SUBSCRIPTION TRANSACTION (st.dialog)
# ======================================================

def cancel_subscription():
    with st.form("cancel_subscription_form", clear_on_submit=True):
        st.write("Cancel a subscription transaction for a specific store.")

        # Select a store
        selected_store = st.selectbox(
            "Select Store",
            options=df_stores["StoreID"].tolist(),
            format_func=lambda sid: f"{sid} — {df_stores.loc[df_stores['StoreID']==sid,'StoreName'].values[0]}"
        )

        # Enter transaction ID
        transaction_id = st.text_input("Enter Transaction ID", placeholder="e.g., TXN-123456")

        # Reason for cancellation
        reason = st.text_area("Reason for cancellation", placeholder="Enter reason (optional)")

        submitted = st.form_submit_button("Cancel Subscription")
        if submitted:
            if not transaction_id:
                st.error("Transaction ID is required to cancel a subscription.")
            else:
                st.success(
                    f"Cancelled subscription transaction {transaction_id} "
                    f"for store {selected_store}."
                )
                if reason:
                    st.info(f"Reason provided: {reason}")

# ======================================================
# DATA TABLES (Tabs)
# ======================================================
with tab2:
    #with st.expander("📋 Detailed Data", expanded=True):
        co1, co2, co3, co4, co5, co6 = st.columns(6,  gap="small")
        with co1:
            open_dialog = st.button("➕ Create Subscription Transaction")
            if open_dialog:
                @st.dialog("Create Subscription Transaction")
                def show_dialog():
                    create_subs()
                show_dialog()
        with co2:
            open_dialog = st.button("⚠️ Cancel Subscription Transaction")
            if open_dialog:
                @st.dialog("Cancel Subscription Transaction")
                def show_dialog():
                    cancel_subscription()
                show_dialog()


        tab_users, tab_stores, tab_expiring, tab_subscription = st.tabs(["Users", "Stores", "Expiring", "Subscription"])
        # ---------- Users Tab ----------
        with tab_users:
            st.markdown("**Users**")
            cols = [
                "UserID", "Name", "CreatedAt", "LastActivity", "Role", "Stores",
                "DeviceType", "Phone", "Email", "ReferralCode", "City", "TotalTransactions"
            ]
            st.dataframe(users_f[cols], use_container_width=True)

        with tab_stores:
            st.markdown("**Stores**")

            # Join owner name
            owner_names = df_users.set_index("UserID")["Name"]
            stores_display = stores_f.copy()
            stores_display["Owner"] = stores_display["OwnerUserID"].map(owner_names)
            stores_display["DaysToExpiry"] = (stores_display["CurrentEnd"] - datetime.now()).dt.days

            cols = [
                "StoreID", "StoreName", "StoreType", "Owner", "City",
                "SubscriptionType", "CurrentStart", "CurrentEnd",
                "ReoccuringSubs", "TotalMoneySpent", "DaysToExpiry", "Is_Branch"
            ]

            # Sort by soonest expiry
            stores_display = stores_display.sort_values("DaysToExpiry", ascending=True)

            # Add a link column
            stores_display["View Details"] = stores_display["StoreID"].apply(
                lambda x: f"#store-{x}"
            )

            edited_df = st.data_editor(
                stores_display[cols + ["View Details"]],
                use_container_width=True,
                disabled=True,
                column_config={
                    "View Details": st.column_config.LinkColumn(
                        "View Details",
                        display_text="View",
                        help="Click to view store details",
                    )
                },
                hide_index=True,
            )

            selected_store_id = None
            if "selected_store" not in st.session_state:
                st.session_state.selected_store = None


            if st.session_state.selected_store:
                row = stores_display[stores_display["StoreID"] == st.session_state.selected_store].iloc[0]

                with st.dialog("Store Details"):
                    st.write("### Store Information")
                    for col in cols:
                        st.write(f"**{col}:** {row[col]}")  


        # ---------- Expiring Tab ----------
        with tab_expiring:
            st.markdown("**Expiring / Expired Subscriptions**")
            today = datetime.now()
            exp_df = stores_f.copy()
            exp_df["DaysToExpiry"] = (exp_df["CurrentEnd"] - today).dt.days

            # Apply expiry window
            if expiry_window == "7 days":
                exp_df = exp_df[(exp_df["DaysToExpiry"] >= 0) & (exp_df["DaysToExpiry"] <= 7)]
            elif expiry_window == "14 days":
                exp_df = exp_df[(exp_df["DaysToExpiry"] >= 0) & (exp_df["DaysToExpiry"] <= 14)]
            elif expiry_window == "30 days":
                exp_df = exp_df[(exp_df["DaysToExpiry"] >= 0) & (exp_df["DaysToExpiry"] <= 30)]
            elif expiry_window == "Expired":
                exp_df = exp_df[exp_df["DaysToExpiry"] < 0]
            # else "All" → keep as is

            # Table: expiring stores
            owner_names = df_users.set_index("UserID")["Name"]
            exp_df["Owner"] = exp_df["OwnerUserID"].map(owner_names)
            cols = [
                "StoreID", "StoreName", "StoreType", "Owner", "City",
                "SubscriptionType", "CurrentEnd", "DaysToExpiry", "ReoccuringSubs", "TotalMoneySpent"
            ]

            # Add "View Details" link column
            exp_df["View Details"] = exp_df["StoreID"].apply(lambda x: f"#store-{x}")

            st.data_editor(
                exp_df.sort_values("DaysToExpiry")[cols + ["View Details"]],
                use_container_width=True,
                disabled=True,  # 🔒 make table read-only
                column_config={
                    "View Details": st.column_config.LinkColumn(
                        "View Details",
                        display_text="View",
                        help="Click to view store details",
                    )
                },
                hide_index=True,
            )

            # Trendline: counts of expiring stores per subscription type (by CurrentEnd date)
            if not exp_df.empty:
                exp_df["EndDateOnly"] = exp_df["CurrentEnd"].dt.date
                trend_exp = (
                    exp_df.groupby(["EndDateOnly", "SubscriptionType"])
                    .size().reset_index(name="Count")
                )
                chart_exp = (
                    alt.Chart(trend_exp)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("EndDateOnly:T", title="End Date"),
                        y=alt.Y("Count:Q", title="Stores"),
                        color=alt.Color("SubscriptionType:N", title="Subscription"),
                        tooltip=["EndDateOnly:T", "SubscriptionType:N", "Count:Q"]
                    )
                    .properties(title=f"Expiring Stores Trend ({expiry_window})")
                )
                st.altair_chart(chart_exp, use_container_width=True)

            # Owners (users) affected by expiring stores
            affected_user_ids = exp_df["OwnerUserID"].unique().tolist()
            if affected_user_ids:
                st.markdown("**Affected Owners**")
                owners_df = df_users[df_users["UserID"].isin(affected_user_ids)][
                    ["UserID", "Name", "Role", "Phone", "Email", "City", "TotalTransactions"]
                ]
                st.data_editor(
                    owners_df,
                    use_container_width=True,
                    disabled=True,  # make owners table also non-editable
                    hide_index=True,
                )
            else:
                st.info("No owners in this expiry window.")
        
        with tab_subscription:
            n_logs = 50

            subscription_logs = pd.DataFrame({
                "StoreID": np.random.choice(df_stores["StoreID"], size=n_logs),
                "Datetime": [datetime.now() - timedelta(days=random.randint(0, 365), hours=random.randint(0,23)) for _ in range(n_logs)],
                "SubscriptionType": np.random.choice(df_stores["SubscriptionType"], size=n_logs),
                "SubscriptionPeriod": np.random.choice([30, 90, 180, 365], size=n_logs),
                "Amount": [random.choice([0, 200_000, 400_000]) for _ in range(n_logs)],
                "TransactionID": [f"TXN-{random.randint(100000,999999)}" for _ in range(n_logs)],
                "ReferralCodeUsed": np.random.choice(df_users["ReferralCode"].dropna().tolist() + [None]*10, size=n_logs)
            })

            # -------------------------
            # Display in Streamlit
            # -------------------------
            st.markdown("**Subscription Logs**")
            st.data_editor(
                subscription_logs,
                use_container_width=True,
                disabled=True,  # make table non-editable
                hide_index=True
            )
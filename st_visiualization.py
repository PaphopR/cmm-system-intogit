import pandas as pd
import streamlit as st
import altair as alt
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# โหลด Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_data():
    # ดึงข้อมูลจาก Supabase
    response = supabase.table("case_database").select("*").execute()
    df = pd.DataFrame(response.data)

    df["datetime"] = pd.to_datetime(df["datetime"])
    df["flow"] = df["flow"].fillna("-").str.strip().str.lower()
    df["process"] = df["process"].fillna("-").str.strip().str.lower()
    df["dimension"] = df["dimension"].fillna("-")
    df["family"] = df["family"].fillna("-")

    return df

def show_charts(df: pd.DataFrame):
    # กรองข้อมูลตาม process
    df_hauling = df[df["process"] == "hauling"]
    df_stock = df[df["process"] == "stock"]
    #df_usage = df[(df["process"] == "usage") & (df["element"].notna())]

    with st.expander("**🚛 Hauling Process**",expanded=True):
        
        hauling_group = df_hauling.groupby("dimension", as_index=False)["quantity"].sum()
        barchart = alt.Chart(hauling_group).mark_bar().encode(
            x=alt.X("quantity:Q", title="Quantity"),
            y=alt.Y("dimension:N", title="Dimension", sort='-x'),
            tooltip=["dimension", "quantity"]
        ).properties(
            title="Hauling Flow"
        )
        st.altair_chart(barchart, use_container_width=True)

    with st.expander("**📦 Stock Process**", expanded=True):
        # แปลง datetime
        df_stock["datetime"] = pd.to_datetime(df_stock["datetime"])

        # เตรียม DataFrame สำหรับรวมผลทุก dimension
        df_all = []

        for dim in df_stock["dimension"].dropna().unique():
            df_dim = df_stock[df_stock["dimension"] == dim].copy()

            # คำนวณ cumulative in/out
            df_in = df_dim[df_dim["flow"] == "in"].groupby("datetime")["quantity"].sum().cumsum().rename("in_cum")
            df_out = df_dim[df_dim["flow"] == "out"].groupby("datetime")["quantity"].sum().cumsum().rename("out_cum")

            # รวมข้อมูล
            df_merge = pd.concat([df_in, df_out], axis=1).fillna(method="ffill").fillna(0)
            df_merge["net"] = df_merge["in_cum"] + df_merge["out_cum"]
            df_merge = df_merge.reset_index()
            df_merge["dimension"] = dim

            df_all.append(df_merge[["datetime", "dimension", "net"]])

        # รวมทุก dimension
        df_final = pd.concat(df_all, ignore_index=True)

        # แบ่งเป็น 2 คอลัมน์: col1 = กราฟ, col2 = metric
        col1, col2 = st.columns([3, 1])

        with col1.container(border=True):
            chart = alt.Chart(df_final).mark_line().encode(
                x=alt.X("datetime:T", title="Datetime"),
                y=alt.Y("net:Q", title="Net Quantity", scale=alt.Scale(zero=True)),
                color=alt.Color("dimension:N", title="Dimension"),
                tooltip=[
                    alt.Tooltip("datetime:T", title="Datetime", format="%Y-%m-%d %H:%M:%S"),
                    alt.Tooltip("dimension:N", title="Dimension"),
                    alt.Tooltip("net:Q", title="Net Quantity"),
                ]
            ).properties(
                title="Net Quantity Flow"
            )
            st.altair_chart(chart, use_container_width=True)

        with col2:
            st.markdown("**Net Quantity by Dimension**")
            latest_nets = df_final.sort_values("datetime").groupby("dimension").tail(1)

            for _, row in latest_nets.iterrows():
                dim = row["dimension"]
                net = int(row["net"])
                st.metric(label=f"Dimension **:green-background[{dim}]** mm.", value=f"{net:,} ea.", border=True)

    with st.expander("**🏗️ Construction Usage Process**", expanded=True):
        # โหลด RoofList และเตรียมข้อมูล
        response_rooflist = supabase.table("RoofList").select("*").execute()
        df_rooflist = pd.DataFrame(response_rooflist.data)
        df_rooflist.columns = df_rooflist.columns.str.strip().str.lower()

        # คำนวณจำนวนที่วางแผนไว้
        planned = df_rooflist.groupby("element", as_index=False).size().rename(columns={"size": "planned_quantity"})

        # คำนวณจำนวนที่ติดตั้งแล้ว
        installed = df[df["process"] == "usage"].groupby("element", as_index=False)["quantity"].sum().rename(columns={"quantity": "installed_quantity"})

        # กรองข้อมูลสำหรับ stock_out (process='stock' and flow='out')
        df_stock_out_data = df[(df["process"] == "stock") & (df["flow"] == "out")]

        # กรองข้อมูลสำหรับ usage (process='usage')
        df_usage_data = df[df["process"] == "usage"]

        has_length_stock_out = "length" in df_stock_out_data.columns
        has_length_usage = "length" in df_usage_data.columns
        has_length_RoofList = "cutlength" in df_rooflist.columns

        if has_length_stock_out or has_length_usage or has_length_RoofList:
            st.markdown("##### **Length usage by Dimension (m.)**")

            result_frames = []

            if has_length_stock_out:
                df_stock_out_data_calc = df_stock_out_data.copy()
                if "quantity" in df_stock_out_data_calc.columns:
                    df_stock_out_data_calc["calculated_total_length"] = -(df_stock_out_data_calc["length"] * df_stock_out_data_calc["quantity"])
                    df_stock_out_sum = df_stock_out_data_calc.groupby("dimension")["calculated_total_length"].sum().rename("Stock Out").to_frame()
                    result_frames.append(df_stock_out_sum)

            if has_length_usage:
                df_usage_data_calc = df_usage_data.copy()
                if "quantity" in df_usage_data_calc.columns:
                    df_usage_data_calc["calculated_total_length"] = df_usage_data_calc["length"] * df_usage_data_calc["quantity"]
                    df_usage_sum = df_usage_data_calc.groupby("dimension")["calculated_total_length"].sum().rename("Usage").to_frame()
                    result_frames.append(df_usage_sum)

            if has_length_RoofList:
                              
                # ลบคำว่า RHS / SHS ออกด้วย str.replace
                df_rooflist_clean = df_rooflist.copy()
                df_rooflist_clean["dimension"] = df_rooflist_clean["dimension"].str.replace("TUBR", "", case=False, regex=False)
                df_rooflist_clean["dimension"] = df_rooflist_clean["dimension"].str.replace("TUBS", "", case=False, regex=False)
                df_rooflist_clean["dimension"] = df_rooflist_clean["dimension"].str.strip()

                # รวมความยาวโดย dimension ที่ล้างแล้ว
                df_rooflist_sum = df_rooflist_clean.groupby("dimension")["cutlength"].sum().rename("RoofList").to_frame()
                result_frames.append(df_rooflist_sum)

            # รวมผลทั้งหมดเข้าด้วยกัน
            if result_frames:
                df_combined = pd.concat(result_frames, axis=1).fillna(0)

                # ลำดับแถวที่ต้องการแสดง
                desired_order = ["RoofList", "Stock Out", "Usage"]

                # Transpose + เปลี่ยนชื่อแถวให้อ่านง่าย
                df_final = df_combined.T.loc[desired_order]
                df_final.rename(index={
                    "Stock Out": "⬇️ Length of steel from Stock Out",
                    "Usage": "🏗️ Length of steel from Installed",
                    "RoofList": "📋 Length of steel from Planner"
                }, inplace=True)

                # แสดงตาราง
                st.dataframe(df_final.style.format("{:,.2f}"))

                for col in df_final.columns:
                    try:
                        val_planner = df_final.loc["📋 Length of steel from Planner", col]
                    except:
                        val_planner = 0

                    try:
                        val_stockout = df_final.loc["⬇️ Length of steel from Stock Out", col]
                    except:
                        val_stockout = 0

                    try:
                        val_usage = df_final.loc["🏗️ Length of steel from Installed", col]
                    except:
                        val_usage = 0

                    # คำนวณ % เทียบ planner และ stock out
                    progress_rooflist = min(val_usage / val_planner, 1.0) if val_planner > 0 else 0.0
                    lre_u_pl = val_planner - val_usage

                    progress_stockout = min(val_usage / abs(val_stockout), 1.0) if val_stockout != 0 else 0.0
                    lre_so_u = val_stockout - val_usage

                    st.markdown(f"**:green-background[Steel Dimension {col} mm.]**")

                    #with col1:
                    #    textcol1 = f"Steel Installed: **{val_usage:.2f} m.** | Remaining: **{lre_u_pl:.2f} m.**"
                    #    st.progress(progress_rooflist, text=textcol1)

                    textcol2 = f"Steel Used: **{val_usage:.2f} m.** | Remaining: **{lre_so_u:.2f} m.**"
                    st.progress(progress_stockout, text=textcol2)
                
        else:
            st.warning("The 'length' column is not available in the data for 'stock out' or 'usage' processes.")

        st.divider() # เพิ่มเส้นแบ่งเพื่อความสวยงาม
        
        st.markdown("##### **Steel Usage by Structural Element**")

        # รวมข้อมูลและคำนวณ % ความคืบหน้า
        df_merge = pd.merge(planned, installed, on="element", how="left")
        df_merge["installed_quantity"] = df_merge["installed_quantity"].fillna(0)
        df_merge["progress_percent"] = (df_merge["installed_quantity"] / df_merge["planned_quantity"] * 100).round(2)

        # แสดง Pie Charts
        for i in range(0, len(df_merge), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(df_merge):
                    row = df_merge.iloc[i + j]
                    element = row["element"]
                    installed = row["installed_quantity"]
                    planned = row["planned_quantity"]
                    remaining = planned - installed
                    percent = row["progress_percent"]

                    pie_df = pd.DataFrame({
                        "status": ["Installed", "Remaining"],
                        "value": [installed, remaining]
                    })

                    pie_chart = alt.Chart(pie_df).mark_arc(innerRadius=40).encode(
                        theta=alt.Theta(field="value", type="quantitative"),
                        color=alt.Color(field="status", type="nominal",
                                        scale=alt.Scale(domain=["Installed", "Remaining"], range=["green", "lightgray"])),
                        tooltip=["status:N", "value:Q"]
                    ).properties(
                        width=220,
                        height=220,
                        title=f"{element} ({percent:.2f}%)"
                    )

                    with cols[j]:
                        st.altair_chart(pie_chart, use_container_width=False)




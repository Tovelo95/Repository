import streamlit as st
import pandas as pd

st.set_page_config(page_title="BUFF 价格与热度深度分析助手", page_icon="📈", layout="wide")

st.title("📈 BUFF 价格与热度深度分析助手")
st.markdown("---")


def find_column(col_list, keywords):
    for col in col_list:
        if all(kw in col for kw in keywords):
            return col
    return None


uploaded_file = st.file_uploader("📂 请上传 BUFF 导出的 CSV 文件", type=['csv'])

if uploaded_file is not None:
    file_mb = round(uploaded_file.size / 1024, 2)
    st.info(f"文件已接收，大小：{file_mb} MB，正在解析...")

    with st.spinner("🔄 解析CSV文件中，请等待..."):
        head_df = pd.read_csv(uploaded_file, encoding="utf-8-sig", nrows=0)
        all_cols = head_df.columns.str.strip().tolist()

        cost_col = find_column(all_cols, ['成本'])
        revenue_col = find_column(all_cols, ['预期', '收益'])
        name_col = find_column(all_cols, ['商品', '名称'])
        time_col = find_column(all_cols, ['创建', '时间'])

        missing = []
        if not cost_col: missing.append("成本价")
        if not revenue_col: missing.append("预期收益")
        if not name_col: missing.append("商品名称")
        if not time_col: missing.append("创建时间")

        if missing:
            st.error(f"❌ 缺少必要字段：{','.join(missing)}")
            st.code(f"文件列名：{all_cols}")
            st.stop()

        keep_cols = [cost_col, revenue_col, name_col, time_col]
        uploaded_file.seek(0)

        df = pd.read_csv(
            uploaded_file,
            encoding="utf-8-sig",
            usecols=keep_cols,
            low_memory=False
        )
        df.columns = df.columns.str.strip()

        df['日期'] = pd.to_datetime(df[time_col], errors="coerce").dt.date
        df['单件利润'] = df[revenue_col] - df[cost_col]

    st.success("✅ 文件解析完成！")

    min_date = df['日期'].min()
    max_date = df['日期'].max()

    st.sidebar.header("🗓️ 多日数据筛选")
    start_date, end_date = st.sidebar.date_input(
        "选择分析日期区间（支持多天）",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    filtered_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]

    if filtered_df.empty:
        st.warning(f"⚠️ {start_date} ~ {end_date} 区间没有交易记录")
    else:
        date_tip = f"{start_date} 至 {end_date}"
        st.subheader(f"📊 {date_tip} 经营总览")
        m1, m2, m3 = st.columns(3)
        m1.metric("区间总销售量", f"{len(filtered_df)} 件")
        m2.metric("区间总成本", f"¥{filtered_df[cost_col].sum():,.2f}")
        m3.metric("区间总记录利润", f"¥{filtered_df['单件利润'].sum():,.2f}")

        st.divider()
        st.subheader("⚡ 实时调价与利润复算")
        item_summary = filtered_df.groupby(name_col).agg(
            购买数量=(name_col, 'count'),
            平均历史成本=(cost_col, 'mean'),
            平均历史利润=('单件利润', 'mean'),
            区间总历史利润=('单件利润', 'sum')
        ).reset_index().round(2).sort_values("购买数量", ascending=False)

        item_summary["当日实时价"] = 0.0
        edited_df = st.data_editor(
            item_summary,
            column_config={
                "当日实时价": st.column_config.NumberColumn("当日实时价 (手动填充)", format="%.2f"),
                name_col: st.column_config.Column(width="medium", disabled=True),
                "购买数量": st.column_config.Column(disabled=True),
                "平均历史成本": st.column_config.Column("历史成本", disabled=True),
                "平均历史利润": st.column_config.Column("区间单件记录利润", disabled=True),
            },
            hide_index=True, use_container_width=True
        )

        if st.button("🚀 计算实时分析结果", type="primary"):
            edited_df['实时单件利润'] = edited_df['当日实时价'] - edited_df['平均历史成本']
            edited_df['区间实时总利润'] = (edited_df['实时单件利润'] * edited_df['购买数量']).round(2)
            st.dataframe(
                edited_df[[name_col, "购买数量", "当日实时价", "实时单件利润", "区间实时总利润"]],
                use_container_width=True, hide_index=True
            )

        st.divider()
        st.subheader("🔍 区间Top50热品每日销量趋势")
        st.write(f"说明：统计【{date_tip}】区间总销量前50商品")

        all_daily_counts = df.groupby(['日期', name_col]).size().reset_index(name='数量')
        range_total = filtered_df.groupby(name_col).size().reset_index(name="区间总销量")
        top_50_names = range_total.nlargest(50, '区间总销量')[name_col].tolist()

        if not top_50_names:
            st.info("所选区间数据不足，无法生成Top50榜单")
        else:
            trend_data = all_daily_counts[all_daily_counts[name_col].isin(top_50_names)]
            pivot_trend = trend_data.pivot(index=name_col, columns="日期", values="数量")
            pivot_trend = pivot_trend.fillna(0).astype(int)

            # 只保留透视表里存在的商品进行排序，杜绝KeyError
            valid_items = range_total[range_total[name_col].isin(pivot_trend.index)]
            valid_sort = valid_items.set_index(name_col)
            pivot_trend = pivot_trend.loc[valid_sort.index]

            st.dataframe(pivot_trend, use_container_width=True)
            st.caption("💡 单元格数值代表当日进货件数，横向观察商品热度变化")

        st.divider()
        csv_bytes = pivot_trend.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")
        fn = f"Top50_趋势_{start_date}_至_{end_date}.csv"
        st.download_button("📥 下载Top50趋势分析表", data=csv_bytes, file_name=fn)

else:
    st.info("👋 欢迎！请上传 BUFF 导出 CSV 文件开始分析。```")
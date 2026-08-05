import streamlit as st
import pandas as pd

# 1. 页面配置
st.set_page_config(page_title="BUFF 深度分析工具", page_icon="📈", layout="wide")

st.title("📈 BUFF 价格与热度深度分析助手")
st.markdown("---")

# 2. 文件上传
uploaded_file = st.file_uploader("📂 请上传 BUFF 导出的 CSV 文件", type=['csv'])

if uploaded_file is not None:
    # 读取CSV自动去除BOM头
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    # 清洗所有列名首尾空格
    df.columns = df.columns.str.strip()

    # 通用模糊匹配列函数
    def find_col(df, keywords):
        for col in df.columns:
            if all(kw in col for kw in keywords):
                return col
        return None

    # 自动匹配业务列
    cost_col = find_col(df, ['成本'])
    revenue_col = find_col(df, ['预期', '收益'])
    name_col = find_col(df, ['商品', '名称'])
    time_col = find_col(df, ['创建', '时间'])

    # 缺失列校验
    missing = []
    if not cost_col: missing.append("成本价")
    if not revenue_col: missing.append("预期收益")
    if not name_col: missing.append("商品名称")
    if not time_col: missing.append("创建时间")

    if missing:
        st.error(f"❌ 缺少必要字段：{', '.join(missing)}")
        st.write("文件现有全部列：")
        st.code(df.columns.tolist())
        st.stop()

    # 计算单件利润
    df['单件利润'] = df[revenue_col] - df[cost_col]
    # 解析日期字段
    df['日期'] = pd.to_datetime(df[time_col]).dt.date

    # 全局日期极值
    min_date = df['日期'].min()
    max_date = df['日期'].max()

    # ====================== 侧边栏改为【日期区间选择】======================
    st.sidebar.header("🗓️ 多日数据筛选")
    start_date, end_date = st.sidebar.date_input(
        "选择分析日期区间（支持多天）",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 筛选区间内所有数据（多日）
    filtered_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]

    if filtered_df.empty:
        st.warning(f"⚠️ {start_date} ~ {end_date} 区间内无交易记录！")
    else:
        date_tip = f"{start_date} 至 {end_date}"
        st.subheader(f"📊 {date_tip} 经营总览")
        m1, m2, m3 = st.columns(3)
        m1.metric("区间总销售量", f"{len(filtered_df)} 件")
        m2.metric("区间总成本", f"¥{filtered_df[cost_col].sum():,.2f}")
        m3.metric("区间总记录利润", f"¥{filtered_df['单件利润'].sum():,.2f}")

        # --- 功能模块2：实时调价与利润复算（区间商品汇总）
        st.divider()
        st.subheader("⚡ 实时调价与利润复算")
        item_summary = filtered_df.groupby(name).agg(
            购买数量=('单件利润', 'count'),
            平均历史成本=(cost_col, 'mean'),
            平均历史利润=('单件利润', 'mean'),
            区间总历史利润=('单件利润', 'sum')
        ).reset_index().round(2).sort_values(by='购买数量', ascending=False)

        item_summary['当日实时价'] = 0.0
        edited_df = st.data_editor(
            item_summary,
            column_config={
                "当日实时价": st.column_config.NumberColumn("当日实时价 (手动填充)", format="%.2f"),
                name_col: st.column_config.Column(width="medium", disabled=True),
                "购买数量": st.column_config.Column(disabled=True),
                "平均历史成本": st.column_config.Column("历史成本", disabled=True),
                "平均历史利润": st.column_config.Column("区间单件记录利润", disabled=True),
            },
            hide_index=True, use_container_width=True,
        )

        if st.button("🚀 计算实时分析结果", type="primary"):
            edited_df['实时单件利润'] = edited_df['当日实时价'] - edited_df['平均历史成本']
            edited_df['区间实时总利润'] = (edited_df['实时单件利润'] * edited_df['购买数量']).round(2)
            st.dataframe(
                edited_df[[name_col, '购买数量', '当日实时价', '实时单件利润', '区间实时总利润']],
                use_container_width=True, hide_index=True
            )

        # --- 功能模块3：Top50热品趋势（区间总销量前50）
        st.divider()
        st.subheader("🔍 区间Top50热品每日销量趋势")
        st.write(f"说明：统计【{date_tip}】区间总销量前50商品，展示每日进货量热力图")

        # 全历史每日商品销量
        all_daily_counts = df.groupby(['日期', name_col]).size().reset_index(name='数量')
        # 先算出区间内每个商品总销量，取Top50
        range_total = filtered_df.groupby(name_col).size().reset_index(name='区间总销量')
        top_50_names = range_total.nlargest(50, '区间总销量')[name_col].tolist()

        if not top_50_names:
            st.info("所选区间数据不足，无法生成Top50榜单")
        else:
            # 提取Top50所有日期的每日数据
            trend_data = all_daily_counts[all_daily_counts[name_col].isin(top_50_names)]
            # 透视表：行商品，列日期
            pivot_trend = trend_data.pivot(index=name_col, columns='日期', values='数量')
            pivot_trend = pivot_trend.fill(0).astype(int)
            # 按区间总销量降序排序
            sort_map = range_total.set_index(name_col)['区间总销量']
            pivot_trend = pivot_trend.loc[sort_map.index]

            st.dataframe(
                pivot_trend.style.background_gradient(axis=1, cmap='Greens'),
                use_container_width=True
            )
            st.caption("💡 绿色越深代表当日进货件数越多，横向观察商品持续热度")

        # 下载按钮（文件名带区间）
        st.divider()
        csv_data = pivot_trend.to_csv(index=True, encoding='utf-8-sig').encode('utf-8-sig')
        file_name = f"Top50_趋势_{start_date}_至_{end_date}.csv"
        st.download_button("📥 下载Top50趋势分析表", data=csv_data, file_name=file_name)

else:
    st.info("👋 欢迎！请上传 BUFF 导出 CSV 文件开始分析。")
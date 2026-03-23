import streamlit as st
import pandas as pd

# 1. 页面配置
st.set_page_config(page_title="BUFF 深度分析工具", page_icon="📈", layout="wide")

st.title("📈 BUFF 价格与热度深度分析助手")
st.markdown("---")

# 2. 文件上传
uploaded_file = st.file_uploader("📂 请上传 BUFF 导出的 CSV 文件", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # 基础计算
    df['单件利润'] = df['预期收益'] - df['成本价']
    time_column = '创建时间'

    if time_column in df.columns:
        df['日期'] = pd.to_datetime(df[time_column]).dt.date

        # 3. 日期选择
        min_date = df['日期'].min()
        max_date = df['日期'].max()
        st.sidebar.header("🗓️ 数据筛选")
        selected_date = st.sidebar.date_input("选择分析基准日：", value=max_date, min_value=min_date, max_value=max_date)

        # 过滤数据
        filtered_df = df[df['日期'] == selected_date]

        if filtered_df.empty:
            st.warning(f"⚠️ {selected_date} 这一天没有交易记录。")
        else:
            # --- 功能模块 1：当日概况 ---
            st.subheader(f"📊 {selected_date} 经营概况")
            m1, m2, m3 = st.columns(3)
            m1.metric("总销售量", f"{len(filtered_df)} 件")
            m2.metric("总成本", f"¥{filtered_df['成本价'].sum():,.2f}")
            m3.metric("记录总利润", f"¥{filtered_df['单件利润'].sum():,.2f}")

            # --- 功能模块 2：实时调价助手 (Data Editor) ---
            st.divider()
            st.subheader("⚡ 实时调价与利润复算")
            item_summary = filtered_df.groupby('商品名称').agg(
                购买数量=('商品名称', 'count'),
                平均历史成本=('成本价', 'mean'),
                平均历史利润=('单件利润', 'mean'),
                历史总利润=('单件利润', 'sum')
            ).reset_index().round(2).sort_values(by='购买数量', ascending=False)

            item_summary['当日实时价'] = 0.0
            edited_df = st.data_editor(
                item_summary,
                column_config={
                    "当日实时价": st.column_config.NumberColumn("当日实时价 (手动填充)", format="%.2f"),
                    "商品名称": st.column_config.Column(width="medium", disabled=True),
                    "购买数量": st.column_config.Column(disabled=True),
                    "平均历史成本": st.column_config.Column("历史成本", disabled=True),
                    "平均历史利润": st.column_config.Column("记录利润", disabled=True),
                },
                hide_index=True, use_container_width=True,
            )

            if st.button("🚀 计算实时分析结果", type="primary"):
                edited_df['实时单件利润'] = edited_df['当日实时价'] - edited_df['平均历史成本']
                edited_df['实时总利润'] = (edited_df['实时单件利润'] * edited_df['购买数量']).round(2)
                st.dataframe(edited_df[['商品名称', '购买数量', '当日实时价', '实时单件利润', '实时总利润']],
                             use_container_width=True, hide_index=True)

            # --- 功能模块 3：【新增】Top 50 热品历史趋势对比 ---
            st.divider()
            st.subheader("🔍 Top 50 热品趋势追踪")
            st.write(f"分析说明：提取 **{selected_date}** 销量前 50 的商品，并对比它们在历史每一天的购买数量。")

            # 1. 计算全表每日每种商品的购买数量
            all_daily_counts = df.groupby(['日期', '商品名称']).size().reset_index(name='数量')

            # 2. 获取基准日(selected_date)的 Top 50
            top_50_names = all_daily_counts[all_daily_counts['日期'] == selected_date].nlargest(50, '数量')[
                '商品名称'].tolist()

            if not top_50_names:
                st.info("该日没有足够的数据进行 Top 50 分析。")
            else:
                # 3. 提取这些商品在所有日期的表现
                trend_data = all_daily_counts[all_daily_counts['商品名称'].isin(top_50_names)]

                # 4. 透视表化：行是商品，列是日期
                pivot_trend = trend_data.pivot(index='商品名称', columns='日期', values='数量').fillna(0).astype(int)

                # 5. 排序：按基准日的数量降序排列
                pivot_trend = pivot_trend.sort_values(by=selected_date, ascending=False)

                # 6. 展示：使用热力图色阶 (颜色越深代表数量越多)
                st.dataframe(
                    pivot_trend.style.background_gradient(axis=1, cmap='Greens'),
                    use_container_width=True
                )

                st.caption(
                    "💡 提示：表格中颜色越绿的部分，代表该商品在当天的进货频率越高。你可以横向查看某个热销品是否在持续进货。")

            # 8. 底部下载
            st.divider()
            csv_data = pivot_trend.to_csv(index=True, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 下载 Top 50 趋势分析表", data=csv_data, file_name=f"Top50_Trend_{selected_date}.csv")

    else:
        st.error(f"❌ 找不到名为 '{time_column}' 的列。")
else:
    st.info("👋 欢迎！请上传 BUFF 导出 CSV 文件开始分析。")
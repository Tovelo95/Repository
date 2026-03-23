import streamlit as st
import pandas as pd

# 1. 页面配置：设置网页标题和图标
st.set_page_config(page_title="BUFF 价格实时分析助手", page_icon="📈", layout="wide")

st.title("📈 BUFF 价格实时分析助手")
st.markdown("---")

# 2. 文件上传区
uploaded_file = st.file_uploader("📂 请将导出的 CSV 文件拖拽到此处", type=['csv'])

if uploaded_file is not None:
    # 读取数据
    df = pd.read_csv(uploaded_file)

    # 核心计算：历史单件利润 = 预期收益 - 成本价
    df['单件利润'] = df['预期收益'] - df['成本价']

    # 时间列配置：根据您的反馈，这里设为 '创建时间'
    time_column = '创建时间'

    if time_column in df.columns:
        # 转换为日期格式
        df['日期'] = pd.to_datetime(df[time_column]).dt.date

        # 3. 日期选择侧边栏/顶部
        min_date = df['日期'].min()
        max_date = df['日期'].max()

        st.sidebar.header("🗓️ 数据筛选")
        selected_date = st.sidebar.date_input(
            "选择分析日期：",
            value=max_date,  # 默认显示最新的一天
            min_value=min_date,
            max_value=max_date
        )

        # 过滤选中日期的数据
        filtered_df = df[df['日期'] == selected_date]

        if filtered_df.empty:
            st.warning(f"⚠️ {selected_date} 这一天没有交易记录。")
        else:
            # 4. 顶部大盘指标展示
            st.subheader(f"📊 {selected_date} 经营概况")

            total_qty = len(filtered_df)
            total_cost = filtered_df['成本价'].sum()
            total_profit = filtered_df['单件利润'].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("总销售量", f"{total_qty} 件")
            m2.metric("总成本", f"¥{total_cost:,.2f}")
            m3.metric("历史总利润", f"¥{total_profit:,.2f}")

            st.divider()

            # 5. 实时价格分析助手 (交互核心)
            st.subheader("⚡ 实时调价与利润复算")
            st.info("💡 操作指南：在下方表格【当日实时价】列直接输入价格，完成后点击下方的蓝色按钮。")

            # 基础汇总：按商品名称分组
            item_summary = filtered_df.groupby('商品名称').agg(
                购买数量=('商品名称', 'count'),
                平均历史成本=('成本价', 'mean'),
                平均历史利润=('单件利润', 'mean'),
                历史总利润=('单件利润', 'sum')
            ).reset_index()
            item_summary = item_summary.round(2).sort_values(by='购买数量', ascending=False)

            # 新增一列用于手动填充
            item_summary['当日实时价'] = 0.0

            # 使用 data_editor 创建可编辑表格
            edited_df = st.data_editor(
                item_summary,
                column_config={
                    "当日实时价": st.column_config.NumberColumn(
                        "当日实时价 (手动填入)",
                        help="在这里输入该商品今天的最新市场价格",
                        min_value=0.0,
                        format="%.2f",
                        required=True,
                    ),
                    "商品名称": st.column_config.Column(width="medium", disabled=True),
                    "购买数量": st.column_config.Column(disabled=True),
                    "平均历史成本": st.column_config.Column("历史成本(均价)", disabled=True),
                    "平均历史利润": st.column_config.Column("记录利润(均价)", disabled=True),
                    "历史总利润": st.column_config.Column(disabled=True),
                },
                hide_index=True,
                use_container_width=True,
            )

            # 6. 计算按钮逻辑
            if st.button("🚀 点击计算实时分析结果", type="primary"):
                # 计算新维度
                # 实时单件利润 = 实时价 - 历史成本
                edited_df['实时单件利润'] = edited_df['当日实时价'] - edited_df['平均历史成本']
                # 利润变动 = 实时利润 - 记录利润
                edited_df['利润变动情况'] = edited_df['实时单件利润'] - edited_df['平均历史利润']
                # 实时总利润预估 = 实时单件利润 * 数量
                edited_df['实时预估总利润'] = (edited_df['实时单件利润'] * edited_df['购买数量']).round(2)

                # 整理显示顺序
                result_display = edited_df[
                    ['商品名称', '购买数量', '平均历史成本', '当日实时价', '实时单件利润', '利润变动情况',
                     '实时预估总利润']]

                st.write("#### ✅ 分析报告")
                st.dataframe(result_display, use_container_width=True, hide_index=True)

                # 实时汇总卡片
                realtime_total = result_display['实时预估总利润'].sum()
                profit_diff = realtime_total - total_profit

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("实时预估总利润汇总", f"¥{realtime_total:,.2f}", delta=f"{profit_diff:.2f} (对比历史)")
                with c2:
                    # 导出实时计算结果
                    csv_res = result_display.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("📥 下载此实时分析报表", data=csv_res,
                                       file_name=f"Realtime_Analysis_{selected_date}.csv")

            # 7. 原始数据下载 (底部备选)
            st.divider()
            with st.expander("💾 导出原始统计报表"):
                col1, col2 = st.columns(2)
                with col1:
                    csv_item = item_summary.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("下载当日商品统计", data=csv_item, file_name=f"Item_Summary_{selected_date}.csv")

    else:
        st.error(f"❌ 找不到名为 '{time_column}' 的列，请确认 CSV 文件格式是否正确。")
else:
    st.info("👋 欢迎！请在上方上传 BUFF 导出的 CSV 文件开始分析。")
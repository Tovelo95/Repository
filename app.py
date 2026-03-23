import streamlit as st
import pandas as pd

# 设置网页标题
st.set_page_config(page_title="订单数据分析工具", page_icon="📊")
st.title("📊 订单数据分析工具")

# 1. 拖拽上传文件 (Streamlit 原生支持)
uploaded_file = st.file_uploader("请将 CSV 文件拖拽到此处，或点击浏览上传", type=['csv'])

if uploaded_file is not None:
    # 读取数据
    df = pd.read_csv(uploaded_file)

    # 计算单件利润
    df['单件利润'] = df['预期收益'] - df['成本价']

    # ⚠️ 请将 '订单时间' 替换为你表格中实际代表时间的列名
    time_column = '创建时间'

    if time_column in df.columns:
        # 将时间处理为纯日期格式
        df['日期'] = pd.to_datetime(df[time_column]).dt.date

        st.divider()  # 一条分割线
        st.write("### 📅 请选择要分析的日期")

        # 2. 日历弹窗选择
        # 获取数据中存在的最小和最大日期，限制日历选择范围
        min_date = df['日期'].min()
        max_date = df['日期'].max()

        selected_date = st.date_input(
            "点击下方选择具体某一天：",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )

        # 3. 根据选中的日期过滤数据
        filtered_df = df[df['日期'] == selected_date]

        if filtered_df.empty:
            st.warning(f"在 {selected_date} 这一天没有找到订单数据。")
        else:
            st.success(f"成功筛选出 {selected_date} 的数据，当天共有 {len(filtered_df)} 笔订单！")

            # --- 数据统计逻辑 ---
            # (1) 大盘统计
            overall_summary = filtered_df.groupby('日期').agg(
                当日总销量=('商品名称', 'count'),
                当日总成本=('成本价', 'sum'),
                当日总预期收益=('预期收益', 'sum'),
                当日总利润=('单件利润', 'sum')
            ).reset_index()
            overall_summary = overall_summary.round(2)

            # (2) 商品明细统计
            item_summary = filtered_df.groupby('商品名称').agg(
                购买数量=('商品名称', 'count'),
                平均价格=('成本价', 'mean'),
                平均单件利润=('单件利润', 'mean'),
                该商品当日总利润=('单件利润', 'sum')
            ).reset_index()
            item_summary = item_summary.round(2).sort_values(by='购买数量', ascending=False)

            # --- 在界面上展示结果 ---
            st.write("#### 📈 当日大盘数据")
            st.dataframe(overall_summary, use_container_width=True)

            st.write("#### 📦 当日商品销售明细")
            st.dataframe(item_summary, use_container_width=True)

            # 4. 提供一键下载按钮 (不需要再硬编码绝对路径了)
            st.write("### ⬇️ 导出分析结果")
            col1, col2 = st.columns(2)

            with col1:
                # 转换数据为 CSV 格式 (utf-8-sig 防止 Excel 中文乱码)
                csv_overall = overall_summary.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="下载大盘统计 (CSV)",
                    data=csv_overall,
                    file_name=f"overall_summary_{selected_date}.csv",
                    mime='text/csv',
                )

            with col2:
                csv_item = item_summary.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="下载商品明细 (CSV)",
                    data=csv_item,
                    file_name=f"item_summary_{selected_date}.csv",
                    mime='text/csv',
                )
    else:
        st.error(f"❌ 找不到名为 '{time_column}' 的列，请检查你的 CSV 表头是否匹配！")
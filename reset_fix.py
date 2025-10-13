# 修复后的重置功能代码

# 重置按钮 - 修复版本
if nav_cols[2].button("🔄 重置当前步骤", use_container_width=True, type="secondary"):
    # 根据当前步骤重置数据
    if st.session_state.current_step == "core_company":
        if st.checkbox("确认重置核心公司设置？"):
            st.session_state.equity_data["core_company"] = ""
            st.session_state.equity_data["actual_controller"] = ""
            # 移除core_company实体
            st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "core_company"]
            st.success("核心公司设置已重置")
            st.rerun()  # ✅ 添加页面刷新
    elif st.session_state.current_step == "top_entities":
        if st.checkbox("确认重置顶级实体/股东？"):
            st.session_state.equity_data["top_level_entities"] = []
            # 移除相关实体
            st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "top_entity"]
            st.success("顶级实体/股东已重置")
            st.rerun()  # ✅ 添加页面刷新
    elif st.session_state.current_step == "subsidiaries":
        if st.checkbox("确认重置子公司？"):
            st.session_state.equity_data["subsidiaries"] = []
            # 移除相关实体
            st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "subsidiary"]
            st.success("子公司已重置")
            st.rerun()  # ✅ 添加页面刷新
    elif st.session_state.current_step == "relationships":
        if st.checkbox("确认重置关系设置？"):
            st.session_state.equity_data["entity_relationships"] = []
            st.session_state.equity_data["control_relationships"] = []
            st.success("关系设置已重置")
            st.rerun()  # ✅ 添加页面刷新
    elif st.session_state.current_step == "generate":
        st.info("在图表生成步骤中无需重置")

# 危险操作 - 完全重置所有数据（修复版本）
# 使用session_state来管理确认状态，避免嵌套按钮问题
if 'show_reset_confirm' not in st.session_state:
    st.session_state.show_reset_confirm = False

if st.button("⚠️ 完全重置所有数据", type="secondary", help="此操作将清除所有已输入的数据"):
    st.session_state.show_reset_confirm = True

if st.session_state.show_reset_confirm:
    st.warning("⚠️ 确认完全重置所有数据？此操作不可撤销！")
    confirm_cols = st.columns([1, 1, 1])
    
    if confirm_cols[0].button("✅ 确认重置", type="primary"):
        # 重置所有会话状态
        st.session_state.equity_data = {
            "core_company": "",
            "shareholders": [],
            "subsidiaries": [],
            "actual_controller": "",
            "top_level_entities": [],
            "entity_relationships": [],
            "control_relationships": [],
            "all_entities": []
        }
        st.session_state.mermaid_code = ""
        st.session_state.editing_entity = None
        st.session_state.editing_relationship = None
        st.session_state.current_step = "core_company"
        st.session_state.show_reset_confirm = False
        st.success("所有数据已重置")
        st.rerun()
    
    if confirm_cols[1].button("❌ 取消", type="secondary"):
        st.session_state.show_reset_confirm = False
        st.rerun()

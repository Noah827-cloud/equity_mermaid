# Streamlit Expander 正确写法与用法

## 核心语法

在Streamlit中，expander有两种主要写法：

### 写法1：直接使用with语句（推荐）
```python
with st.expander("标题文本", expanded=False):
    # expander内容
    st.write("这是expander的内容")
```

### 写法2：先赋值再使用with语句
```python
expander = st.expander("标题文本", expanded=False)
with expander:
    # expander内容
    st.write("这是expander的内容")
```

## 主要参数说明

- `label`：expander的标题文本（必需）
- `expanded`：是否默认展开（可选，默认为False）
- `icon`：可以在标题前添加emoji图标（如示例中的"📷"、"🗀"等）

## 侧边栏中使用expander

在侧边栏中使用expander的正确方式是：

```python
with st.sidebar:
    # 方法1：直接使用
    with st.expander("图像识别模式", expanded=True):
        st.markdown("- 上传清晰的股权结构图")
        st.markdown("- AI自动识别公司、股东信息")
    
    # 方法2：先赋值
    expander = st.expander("手动编辑模式")
    with expander:
        st.markdown("- 从零构建股权结构")
        st.markdown("- 精确设置持股比例")
```

## 实用技巧

1. **默认展开重要内容**：对于需要重点展示的内容，设置`expanded=True`

2. **分组相关控件**：将相关的输入控件放在同一个expander中

3. **配合session_state使用**：
```python
with st.expander("设置", expanded=False):
    option = st.selectbox("选择选项", options, key="my_option")
    # session_state会自动保存选择
```

4. **条件展开**：
```python
expanded_state = "show_details" in st.session_state
with st.expander("详细信息", expanded=expanded_state):
    # 详细内容
```

5. **嵌套expander**：虽然技术上支持，但不建议过度嵌套，影响用户体验

6. **响应式设计**：expander会自动适应不同屏幕尺寸

## 样式优化建议

如需自定义expander样式，可以通过CSS进行调整：
```python
st.markdown("""
<style>
    /* 侧边栏expander样式 */
    [data-testid="stSidebar"] .streamlit-expander-header {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
    }
    
    /* expander内容样式 */
    [data-testid="stSidebar"] .streamlit-expanderContent {
        background: rgba(0, 0, 0, 0.1);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)
```

## 常见问题

1. **避免使用特殊字符**：标题中避免使用过多特殊字符，可能影响显示
2. **内容适中**：每个expander内容不要过多，保持简洁
3. **性能考虑**：expander中的复杂计算会在展开时执行
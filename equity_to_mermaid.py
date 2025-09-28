import os
import json
import re
import base64
import tempfile
import webbrowser
import dashscope
import streamlit as st
from dashscope import MultiModalConversation
from streamlit_mermaid import st_mermaid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置 API Key
def set_api_key():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key and api_key != "your_dashscope_api_key":
        dashscope.api_key = api_key
        return True
    return False

def extract_json_from_text(text: str):
    """从任意文本中提取第一个合法的 JSON 对象"""
    # 尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试匹配 ```json ... ``` 或 ``` ... ```
    json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试查找最外层的 {...}
    brace_match = re.search(r"({.*})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # 如果都失败，抛出错误并显示原始内容
    raise ValueError(f"无法从以下文本中提取 JSON:\n{text}")

def image_to_equity_structure(image_path: str) -> dict:
    """直接用 Qwen-VL 理解股权结构图（增强版）"""
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:image/png;base64,{img_base64}"},
                {
                 "text": (
        "你是一名专业的企业尽调分析师，请极其仔细地分析这张股权结构图。注意以下要求：\n"
        "1. **人名和公司名称必须逐字准确识别，不得臆测或修改**。例如：'田桑' 不能识别为 '桑桑'。\n"
        "2. 如果文字模糊，请根据上下文谨慎推断，但优先保留原始字形。\n"
        "3. 识别核心公司名称\n"
        "4. 列出所有直接股东（自然人或企业）及其持股比例（如51.3287% → 0.513287）\n"
        "5. 列出所有子公司及其控股比例\n"
        "6. 判断实际控制人\n"
        "7. **只输出一个严格合法的 JSON 对象，不要任何其他文字**\n"
        '示例格式：{"core_company":"XX公司","shareholders":[{"name":"田桑","type":"自然人","ratio":0.6}],"subsidiaries":[],"controller":"田桑"}'
                    )
                }
            ]
        }
    ]

    response = MultiModalConversation.call(
        model='qwen3-vl-plus',
        messages=messages,
        temperature=0.01,  # 更低温度，减少自由发挥
        seed=12345         # 提高可重复性
    )

    if response.status_code != 200:
        raise Exception(f"API Error: {response.code} - {response.message}")

    # 获取模型返回的文本
    text_output = ""
    try:
        contents = response.output.choices[0].message.content
        for item in contents:
            if item.get("text"):
                text_output = item["text"].strip()
                break
    except Exception as e:
        raise Exception(f"解析模型输出失败: {e}")

    if not text_output:
        raise Exception("模型返回为空")

    # 安全提取 JSON
    return extract_json_from_text(text_output)

def generate_mermaid(structure: dict) -> str:
    def escape_mermaid_text(text: str) -> str:
        """转义 Mermaid 节点文本中的特殊字符"""
        # 替换换行符为 \n（Mermaid 要求双反斜杠）
        text = text.replace("\n", "\\n")
        text = text.replace('"', '\\"')  # 转义引号
        return text

    core = escape_mermaid_text(structure["core_company"])
    controller = escape_mermaid_text(structure["controller"])
    lines = ["graph TD"]
    
    # 添加注释
    lines.append("     %% 节点定义")
    
    # 控股人 -> 核心公司
    ctrl_ratio = next(s["ratio"] for s in structure["shareholders"] if s["name"] == structure["controller"])
    lines.append(f'     A["{controller}"] -->|{ctrl_ratio:.4%}| B["{core}"]')
    
    # 其他股东
    other_sh = [s for s in structure["shareholders"] if s["name"] != structure["controller"]]
    for i, sh in enumerate(other_sh):
        node_id = f"SH{i+1}"
        name = escape_mermaid_text(sh["name"])
        lines.append(f'     {node_id}["{name}"] -->|{sh["ratio"]:.4%}| B')
    
    # 空行分隔
    lines.append("")
    
    # 子公司
    sub_nodes = []
    for i, sub in enumerate(structure["subsidiaries"]):
        node_id = f"SUB{i+1}"
        sub_nodes.append(node_id)
        name = escape_mermaid_text(sub["name"])
        # 修改为使用浮点格式显示比例
        lines.append(f'     B -->|{sub["ratio"]:.4%}| {node_id}["{name}"]')
    
    # 空行分隔
    lines.append("")
    
    # 添加注释
    lines.append("     %% 样式定义")
    
    # 样式定义
    lines.extend([
        "     classDef person fill:#ffebee,stroke:#f44336;",
        "     classDef company fill:#bbdefb,stroke:#1976d2;",
        "     classDef sub fill:#e0f7fa,stroke:#00bcd4;"
    ])
    
    # 添加注释
    lines.append("")
    lines.append("     %% 应用样式")
    
    # 应用样式
    lines.extend([
        "     class A person",
        "     class B company"
    ])
    
    # 为子公司应用样式
    if sub_nodes:
        # 使用逗号连接所有子公司节点
        sub_nodes_str = ",".join(sub_nodes)
        lines.append(f"     class {sub_nodes_str} sub")
    
    return "\n".join(lines)

def process_image(image_file):
    """处理上传的图片并生成股权结构图"""
    # 创建临时文件保存上传的图片
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        temp_file.write(image_file.getbuffer())
        temp_path = temp_file.name
    
    try:
        # 分析图片
        structure = image_to_equity_structure(temp_path)
        # 生成 Mermaid 代码
        mermaid_code = generate_mermaid(structure)
        return structure, mermaid_code
    finally:
        # 清理临时文件
        os.unlink(temp_path)

def main_cli(image_path: str):
    """命令行界面入口"""
    print("🧠 Qwen-VL 正在分析股权结构图...")
    try:
        structure = image_to_equity_structure(image_path)
        print("✅ 提取成功：", json.dumps(structure, ensure_ascii=False, indent=2))
        
        mermaid_code = generate_mermaid(structure)
        print("\n🎨 Mermaid 代码：\n")
        print(mermaid_code)
        
        output_file = image_path.rsplit(".", 1)[0] + "_mermaid.mmd"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(mermaid_code)
        print(f"\n💾 已保存至: {output_file}")
    except Exception as e:
        print("❌ 错误发生：", str(e))

def main_streamlit():
    """Streamlit Web 界面入口"""
    st.set_page_config(
        page_title="股权结构图分析工具",
        page_icon="📊",
        layout="wide"
    )
    
    # 添加自定义CSS来优化图表显示区域
    st.markdown("""
    <style>
    /* 增加图表容器的显示大小和滚动条 */
    .mermaid-container {
        height: 100%;
        overflow: auto;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
    }
    /* 确保Mermaid图表可以正确缩放 */
    .mermaid {
        min-width: 100%;
        max-width: none;
    }
    /* 全屏模式的样式 */
    .fullscreen-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: white;
        z-index: 1000;
        padding: 20px;
        overflow: auto;
    }
    .close-button {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 8px 16px;
        cursor: pointer;
        z-index: 1001;
    }
    /* 增加图表容器的默认高度 */
    .stVerticalBlock {
        min-height: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面标题
    st.title("📊 股权结构图智能分析工具")
    st.markdown("通过 AI 技术自动识别股权结构图并生成可编辑的 Mermaid 图表")
    
    # 侧边栏 - API Key 设置和图表显示选项
    with st.sidebar:
        st.header("🔑 API 设置")
        api_key = st.text_input("请输入您的 DashScope API Key", 
                              value=os.getenv("DASHSCOPE_API_KEY", ""),
                              type="password")
        
        if api_key:
            dashscope.api_key = api_key
            os.environ["DASHSCOPE_API_KEY"] = api_key
            st.success("✅ API Key 已设置")
        else:
            # 尝试从环境变量加载
            if set_api_key():
                st.info("✅ 已从环境变量加载 API Key")
            else:
                st.warning("⚠️ 请设置 API Key 以使用服务")
        
        # 在侧边栏增加图表大小和缩放控制
        st.markdown("---")
        st.header("📊 图表显示设置")
        chart_height = st.slider("图表高度调整", min_value=500, max_value=1500, value=1000, step=100)
        zoom_factor = st.slider("图表缩放比例", min_value=50, max_value=200, value=100, step=10)
        st.caption(f"当前缩放: {zoom_factor}%")
        st.markdown("---")
        st.header("📝 使用说明")
        st.markdown("""
        1. 上传一张清晰的股权结构图图片
        2. 点击「分析图片」按钮
        3. 查看生成的股权结构分析结果
        4. 使用「放大查看」按钮全屏浏览图表
        5. 下载或复制 Mermaid 代码
        """)
    
    # 主界面 - 图片上传和处理
    # 移除左右分栏，改为上下布局
    st.header("🖼️ 上传股权结构图")
    uploaded_file = st.file_uploader("选择 PNG 或 JPG 格式的股权结构图", 
                                   type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        # 显示上传的图片预览，增加图片显示大小
        st.image(uploaded_file, caption="上传的股权结构图", 
                use_column_width=True)
        
        # 分析按钮
        if st.button("🔍 分析图片", type="primary"):
            if not dashscope.api_key or dashscope.api_key == "your_dashscope_api_key":
                st.error("❌ 请先设置有效的 API Key")
            else:
                with st.spinner("🧠 AI 正在分析图片..."):
                    try:
                        structure, mermaid_code = process_image(uploaded_file)
                        # 保存结果到 session state
                        st.session_state.structure = structure
                        st.session_state.mermaid_code = mermaid_code
                        st.session_state.processed = True
                        st.success("✅ 分析完成！")
                    except Exception as e:
                        st.error(f"❌ 分析失败: {str(e)}")
    
    # 水平分割线，明确区分两个区域
    st.markdown("---")
    
    st.header("📊 生成的股权结构图")
    
    # 检查是否有处理结果
    if "processed" in st.session_state and st.session_state.processed:
        # 创建一个容器来显示图表
        chart_container = st.container()
        
        with chart_container:
            # 使用HTML和JavaScript来渲染图表，而不是直接使用st_mermaid组件
            import streamlit.components.v1 as components
            import json
            
            # 构建Mermaid图表的HTML内容
            mermaid_code_content = st.session_state.mermaid_code
            zoom_factor_value = str(zoom_factor/100)
            
            # 使用JSON字符串化来正确转义JavaScript字符串
            json_mermaid_code = json.dumps(mermaid_code_content)
            json_zoom_factor = json.dumps(zoom_factor_value)
            
            # 使用原始字符串和正确的JavaScript字符串拼接，参考mermaid-safe.html的实现方式
            mermaid_html = '''
            <div style="width: 100%; height: 100%;">
                <div id="mermaid-container" style="background-color: white; min-height: 500px; padding: 20px;">
                    <div id="loading-indicator" style="text-align: center; padding: 50px; color: #666;">加载中...</div>
                    <div id="mermaid-chart" class="mermaid"></div>
                    <div id="error-container" style="display: none; padding: 20px; background-color: #f8f9fa; border-left: 4px solid #ff6b6b;"></div>
                </div>
                
                <script>
                    // 使用JSON解析确保字符串安全
                    const mermaidCode = ''' + json_mermaid_code + ''';
                    const zoomFactor = ''' + json_zoom_factor + ''';
                    
                    // 设置Mermaid代码
                    document.getElementById('mermaid-chart').textContent = mermaidCode;
                    
                    // 尝试加载Mermaid库
                    function loadMermaid() {
                        try {
                            const script = document.createElement('script');
                            script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
                            script.type = 'module';
                            script.onload = initMermaid;
                            script.onerror = handleCdnError;
                            document.head.appendChild(script);
                        } catch (error) {
                            showError('加载脚本时出错');
                        }
                    }
                    
                    function initMermaid() {
                        try {
                            // 由于使用ESM模块，需要动态导入
                            import('https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs')
                                .then(mermaid => {
                                    document.getElementById('loading-indicator').style.display = 'none';
                                    
                                    mermaid.default.initialize({
                                        startOnLoad: true,
                                        theme: 'default',
                                        securityLevel: 'antiscript',
                                        flowchart: {
                                            useMaxWidth: false,
                                            htmlLabels: true,
                                            curve: 'cardinal'
                                        },
                                        fontFamily: '"Segoe UI", sans-serif'
                                    });
                                    
                                    setTimeout(() => {
                                        const svg = document.querySelector('#mermaid-chart svg');
                                        if (svg) {
                                            svg.style.width = '100%';
                                            svg.style.height = 'auto';
                                            svg.style.transform = 'scale(' + zoomFactor + ')';
                                            svg.style.transformOrigin = 'top left';
                                        }
                                    }, 300); // 增加延迟确保渲染完成
                                })
                                .catch(error => {
                                    showError('初始化Mermaid时出错: ' + error.message);
                                });
                        } catch (error) {
                            showError('初始化Mermaid时出错: ' + error.message);
                        }
                    }
                    
                    function handleCdnError() {
                        try {
                            const fallbackScript = document.createElement('script');
                            fallbackScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js';
                            fallbackScript.onload = () => {
                                document.getElementById('loading-indicator').style.display = 'none';
                                
                                if (typeof mermaid !== 'undefined') {
                                    mermaid.initialize({
                                        startOnLoad: true,
                                        theme: 'default',
                                        securityLevel: 'antiscript',
                                        flowchart: {
                                            useMaxWidth: false,
                                            htmlLabels: true
                                        }
                                    });
                                    
                                    setTimeout(() => {
                                        const svg = document.querySelector('#mermaid-chart svg');
                                        if (svg) {
                                            svg.style.transform = 'scale(' + zoomFactor + ')';
                                            svg.style.transformOrigin = 'top left';
                                        }
                                    }, 300);
                                } else {
                                    showFallback();
                                }
                            };
                            fallbackScript.onerror = showFallback;
                            document.head.appendChild(fallbackScript);
                        } catch (error) {
                            showFallback();
                        }
                    }
                    
                    function showError(message) {
                        document.getElementById('loading-indicator').style.display = 'none';
                        const errorDiv = document.getElementById('error-container');
                        errorDiv.style.display = 'block';
                        errorDiv.innerHTML = '<div style="font-weight: bold; color: #ff6b6b; margin-bottom: 10px;">错误: ' + message + '</div>';
                    }
                    
                    function showFallback() {
                        document.getElementById('loading-indicator').style.display = 'none';
                        const errorDiv = document.getElementById('error-container');
                        errorDiv.style.display = 'block';
                        errorDiv.innerHTML = '<div style="font-weight: bold; color: #ff6b6b; margin-bottom: 10px;">图表加载失败，以下是原始Mermaid代码：</div>' +
                                           '<pre style="font-family: monospace; white-space: pre-wrap; background-color: #f0f0f0; padding: 15px; border-radius: 5px; overflow-x: auto;">' + mermaidCode + '</pre>';
                    }
                    
                    // 确保调用loadMermaid函数以开始加载和渲染过程
                    loadMermaid();
                </script>
            </div>'''
            
            # 使用components.html来渲染图表
            components.html(mermaid_html, height=chart_height, scrolling=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 图表操作按钮
        col_op1, col_op2, col_op3 = st.columns(3)
        with col_op1:
            # 全屏查看按钮 - 优化为直接在浏览器中打开带编辑器的预览页面
            if st.button("🔍 全屏查看 (带编辑器)", type="primary", use_container_width=True):
                # 在新标签页打开全屏视图
                # 使用字符串构建而非f-string，避免花括号冲突
                # 获取Mermaid代码内容并正确转义
                mermaid_code_content = st.session_state.mermaid_code
                
                # 生成类似mermaid-safe.html的分栏预览页面
                html_content = '''<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>股权结构图编辑器 - 左侧代码，右侧预览</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      height: 100vh;
      overflow: hidden;
      background-color: #f8f9fa;
    }
    .header {
      padding: 12px 20px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
      font-size: 16px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .controls {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .controls input {
      padding: 4px 8px;
      font-size: 14px;
      border: 1px solid #ccc;
      border-radius: 4px;
    }
    .controls button {
      padding: 4px 10px;
      font-size: 14px;
      cursor: pointer;
      background-color: #f8f9fa;
      border: 1px solid #ccc;
      border-radius: 4px;
      transition: all 0.3s;
    }
    .controls button:hover {
      background-color: #e9ecef;
    }
    .close-btn {
      background-color: #dc3545;
      color: white;
      border: none;
    }
    .close-btn:hover {
      background-color: #c82333;
      color: white;
    }
    .container {
      display: flex;
      height: calc(100vh - 60px);
      overflow: hidden;
    }
    #editor {
      height: 100%;
      width: 30%;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #e0e0e0;
      background-color: white;
    }
    #preview-container {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: white;
      overflow: hidden;
    }
    textarea {
      flex: 1;
      padding: 14px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      line-height: 1.4;
      border: none;
      outline: none;
      resize: none;
      background: #fff;
    }
    #preview {
      flex: 1;
      padding: 20px;
      overflow: auto;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      position: relative;
    }
    #preview svg {
      min-width: 100%;
      height: auto;
      max-width: none;
    }
    #preview svg text {
      cursor: pointer;
      user-select: none;
    }
    #preview svg text:hover {
      fill: #1976d2 !important;
      font-weight: bold !important;
    }
    #resizer {
      width: 6px;
      background: #e0e0e0;
      cursor: col-resize;
      user-select: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #resizer:hover { 
      background: #ccc;
    }
    #resizer::after {
      content: "⋮⋮";
      color: #999;
      font-size: 14px;
      writing-mode: vertical-rl;
    }
    .error {
      padding: 10px;
      color: #d32f2f;
      background: #ffebee;
      font-family: monospace;
      white-space: pre-wrap;
    }
    .zoom-controls {
      position: absolute;
      bottom: 20px;
      right: 20px;
      background-color: white;
      border-radius: 25px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      padding: 5px;
      z-index: 100;
    }
    .zoom-btn {
      background-color: #f8f9fa;
      border: none;
      border-radius: 50%;
      width: 35px;
      height: 35px;
      margin: 0 5px;
      font-size: 18px;
      cursor: pointer;
      transition: background-color 0.3s;
    }
    .zoom-btn:hover {
      background-color: #e9ecef;
    }
    .zoom-value {
      display: inline-block;
      line-height: 35px;
      padding: 0 10px;
      color: #495057;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="header">
    📊 股权结构图编辑器（左侧代码，右侧实时预览）
    <div class="controls">
      <input type="text" id="keywordInput" placeholder="输入关键词高亮">
      <button id="highlightBtn">高亮</button>
      <button id="clearBtn">清除高亮</button>
      <button class="close-btn" onclick="window.close()">关闭页面</button>
    </div>
  </div>
  <div class="container">
    <div id="editor">
      <textarea id="source" spellcheck="false">'''
                
                # 插入Mermaid代码内容
                html_content += mermaid_code_content
                
                html_content += '''</textarea>
    </div>
    <div id="resizer"></div>
    <div id="preview-container">
      <div id="preview"></div>
      <div class="zoom-controls">
        <button class="zoom-btn" onclick="zoomDiagram(-0.1)">-</button>
        <span class="zoom-value" id="zoom-value">100%</span>
        <button class="zoom-btn" onclick="zoomDiagram(0.1)">+</button>
        <button class="zoom-btn" onclick="resetZoom()">⟲</button>
      </div>
    </div>
  </div>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';

    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'antiscript',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: false,
        curve: 'cardinal'
      },
      fontFamily: '"Segoe UI", sans-serif'
    });

    const source = document.getElementById('source');
    const preview = document.getElementById('preview');
    const editor = document.getElementById('editor');
    const resizer = document.getElementById('resizer');
    const keywordInput = document.getElementById('keywordInput');
    const highlightBtn = document.getElementById('highlightBtn');
    const clearBtn = document.getElementById('clearBtn');

    let currentSvgEl = null;
    let currentZoom = 1.0;

    // ========== 渲染函数 ==========
    async function render() {
      const code = source.value.trim();
      preview.innerHTML = '';

      if (!code) {
        preview.textContent = '请输入 Mermaid 代码...';
        currentSvgEl = null;
        return;
      }

      try {
        const { svg: rawSvg } = await mermaid.render('chart', code);
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(rawSvg, 'image/svg+xml');
        currentSvgEl = svgDoc.documentElement;

        preview.innerHTML = '';
        preview.appendChild(currentSvgEl);

        currentSvgEl.style.width = '100%';
        currentSvgEl.style.height = 'auto';
        
        // 应用当前缩放设置
        updateZoom();

        // === 绑定点击事件：点击 text 修改内容 ===
        const texts = currentSvgEl.querySelectorAll('text');
        texts.forEach(text => {
          // 移除旧监听器（防止重复绑定）
          text.style.cursor = 'pointer';
          const onClick = () => {
            const currentText = text.textContent || '';
            const newText = prompt('请输入新节点文字：', currentText);
            if (newText !== null && newText !== currentText) {
              text.textContent = newText;
              // 可选：自动调整文字位置居中（Mermaid 的 rect 通常有 x/y/width/height）
              const rect = text.closest('g')?.querySelector('rect');
              if (rect) {
                const x = parseFloat(rect.getAttribute('x')) || 0;
                const width = parseFloat(rect.getAttribute('width')) || 0;
                text.setAttribute('x', x + width / 2);
                text.setAttribute('text-anchor', 'middle');
              }
            }
          };
          // 先移除可能的旧监听器（避免重复）
          text.removeEventListener('click', onClick);
          text.addEventListener('click', onClick);
        });

      } catch (e) {
        console.error(e);
        preview.innerHTML = `<div class="error">❌ ${e.message || e}</div>`;
        currentSvgEl = null;
      }
    }

    // ========== 高亮函数 ==========
    function highlightKeyword(keyword) {
      if (!currentSvgEl || !keyword.trim()) return;
      render(); // 先重置（清除之前高亮）
      setTimeout(() => {
        if (!currentSvgEl) return;
        const groups = currentSvgEl.querySelectorAll('g');
        groups.forEach(g => {
          const texts = g.querySelectorAll('text');
          let match = false;
          texts.forEach(t => {
            if ((t.textContent || '').includes(keyword)) {
              match = true;
            }
          });
          if (match) {
            texts.forEach(t => {
              t.setAttribute('fill', '#d32f2f');
              t.setAttribute('font-weight', 'bold');
            });
            const rect = g.querySelector('rect');
            if (rect) {
              rect.setAttribute('fill', '#ffebee');
              rect.setAttribute('stroke', '#f44336');
              rect.setAttribute('stroke-width', '2');
            }
          }
        });
      }, 50);
    }

    function clearHighlight() {
      render();
    }

    // ========== 缩放函数 ==========
    function zoomDiagram(delta) {
      currentZoom = Math.max(0.1, Math.min(3.0, currentZoom + delta));
      updateZoom();
    }

    function resetZoom() {
      currentZoom = 1.0;
      updateZoom();
    }

    function updateZoom() {
      if (currentSvgEl) {
        currentSvgEl.style.transform = 'scale(' + currentZoom + ')';
        currentSvgEl.style.transformOrigin = 'center';
        document.getElementById('zoom-value').textContent = Math.round(currentZoom * 100) + '%';
      }
    }

    // 事件绑定
    let timer;
    source.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(render, 400);
    });

    highlightBtn.addEventListener('click', () => {
      highlightKeyword(keywordInput.value);
    });

    clearBtn.addEventListener('click', () => {
      clearHighlight();
    });

    keywordInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') highlightKeyword(keywordInput.value);
    });

    // 拖拽分割条
    let isResizing = false;
    resizer.addEventListener('mousedown', (e) => {
      isResizing = true;
      document.body.style.cursor = 'col-resize';
      e.preventDefault();
    });
    document.addEventListener('mousemove', (e) => {
      if (!isResizing) return;
      const containerRect = document.querySelector('.container').getBoundingClientRect();
      let leftPercent = ((e.clientX - containerRect.left) / containerRect.width) * 100;
      leftPercent = Math.max(10, Math.min(70, leftPercent));
      editor.style.width = `${leftPercent}%`;
    });
    document.addEventListener('mouseup', () => {
      if (isResizing) {
        isResizing = false;
        document.body.style.cursor = 'default';
        render(); // 重新渲染图表以适应新的布局
      }
    });

    // Ctrl + 滚轮缩放
    preview.addEventListener('wheel', (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        zoomDiagram(delta);
      }
    }, { passive: false });

    // 双击重置缩放
    document.addEventListener('dblclick', function() {
      resetZoom();
    });

    // 初始渲染
    render();
  </script>
</body>
</html>'''
                
                # 创建临时HTML文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_file_path = f.name
                
                # 在新标签页打开文件
                webbrowser.open_new_tab('file://' + os.path.abspath(temp_file_path))
        
        with col_op2:
            # 下载按钮
            st.download_button(
                label="💾 下载 Mermaid 代码",
                data=st.session_state.mermaid_code,
                file_name=f"股权结构图_{st.session_state.structure['core_company']}_mermaid.mmd",
                mime="text/plain"
            )
        
        # 显示股权结构数据
        with st.expander("📋 查看详细股权结构数据"):
            st.json(st.session_state.structure, expanded=False)
        
        # 复制代码按钮
        if st.button("📋 复制 Mermaid 代码"):
            st.code(st.session_state.mermaid_code, language="mermaid")
            st.toast("✅ 代码已复制到剪贴板")
    else:
        # 只在未处理时显示提示信息
        st.info("请上传并分析股权结构图以查看结果")
    
    # 页脚
    st.markdown("---")
    st.markdown("© 2024 股权结构图分析工具 | 基于千问 VL 模型")

if __name__ == "__main__":
    import sys
    # 判断是命令行模式还是 Web 模式
    if len(sys.argv) > 1:
        # 命令行模式
        if not set_api_key():
            print("请设置 DASHSCOPE_API_KEY 环境变量")
            sys.exit(1)
        main_cli(sys.argv[1])
    else:
        # Web 模式
        main_streamlit()
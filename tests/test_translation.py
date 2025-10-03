import sys
import os
import json
import io
import contextlib

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.translation_utils import translate_mermaid_to_english

# 测试的中文Mermaid代码
chinese_mermaid_code = '''
graph TD
    subgraph "Fujian South Pavement Machinery Co., Ltd.股权结构"
        A["Fujian South Pavement Machinery Co., Ltd."] --> B["Fang Qingxi (42.71%)"]
        A --> C["Chen Guihua (12.79%)"]
        A --> D["Fang Kai (5.41%)"]
        A --> E["Quanzhou Zhicheng Investment Partnership (Limited Partnership) (4.4%)"]
        A --> F["Quanzhou Fangyao Investment Partnership (Limited Partnership) (3.75%)"]
        A --> G["Quanzhou Zhixin Investment Partnership (Limited Partnership) (3.21%)"]
        A --> H["Quanzhou Fanghua Investment Partnership (Limited Partnership) (1.96%)"]
        A --> I["Jiang Fenfen (0.44%)"]
        A --> J["Zhu Caiqin (0.35%)"]
        A --> K["UBS AG (0.23%)"]
        A --> L["Weng Rushan (0.2162%)"]
        A --> M["Zhang upright post (0.19999%)"]
        A --> N["Cao Yong (0.188%)"]
        A --> O["You (0.1829%)"]
        A --> P["BARCLAYS BANK PLC (0.1712%)"]
        A --> Q["Chen Guoshan (0.1641%)"]
        A --> R["Cathay Pacific Haitong Securities Co., Ltd. (0.1344%)"]
    end

    subgraph "子公司"
        A --> S["Southern Pavement Machinery (Xiantao) Co., Ltd. (100.0%)"]
        A --> T["Quanzhou Nanfang Road Machine Mobile Crushing Equipment Co., Ltd. (100.0%)"]
        A --> U["Fujian Nante Building Materials Equipment Research Institute Co., Ltd. (100.0%)"]
    end

    %% 样式定义
    classDef mainCompany fill:#ff9999,stroke:#333,stroke-width:2px;
    classDef subsidiary fill:#99ccff,stroke:#333,stroke-width:1px;
    classDef shareholder fill:#99ff99,stroke:#333,stroke-width:1px;
    classDef topEntity fill:#1E90FF,stroke:#333,stroke-width:2px;

    %% 应用样式
    class A mainCompany;
    class S,T,U subsidiary;
    class B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R shareholder;
    class B,C,D,E,F,G,H topEntity;
'''

# 执行翻译
try:
    # 捕获翻译过程中的输出
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        translated_mermaid = translate_mermaid_to_english(chinese_mermaid_code)
    output = f.getvalue()
    
    # 打印翻译结果
    print("翻译后的英文Mermaid代码：")
    print(translated_mermaid)
    
    # 打印处理信息
    print("\n翻译处理信息：")
    print(output)
    
    # 保存翻译结果到文件
    output_file = 'tests/translated_test_data.json'
    translation_result = {
        "chinese_mermaid": chinese_mermaid_code,
        "english_mermaid": translated_mermaid,
        "processing_info": output
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translation_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n翻译结果已保存到 {output_file}")
    
except Exception as e:
    print(f"翻译过程中出错：{str(e)}")
    import traceback
    traceback.print_exc()
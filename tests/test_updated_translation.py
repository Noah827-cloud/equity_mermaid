import sys
import os
import json
import io
import contextlib

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.translation_utils import translate_mermaid_to_english

# 测试的中文Mermaid代码（更新版本）
chinese_mermaid_code = '''
graph TD
    subgraph "福建南方路面机械有限公司股权结构"
        A["福建南方路面机械有限公司"] --> B["方庆熙 (42.71%)"]
        A --> C["陈桂华 (12.79%)"]
        A --> D["方凯 (5.41%)"]
        A --> E["泉州市志成投资合伙企业 (有限合伙) (4.4%)"]
        A --> F["泉州市方耀投资合伙企业 (有限合伙) (3.75%)"]
        A --> G["泉州市志信投资合伙企业 (有限合伙) (3.21%)"]
        A --> H["泉州市方华投资合伙企业 (有限合伙) (1.96%)"]
        A --> I["江芬芳 (0.44%)"]
        A --> J["朱彩芹 (0.35%)"]
        A --> K["UBS AG (0.23%)"]
        A --> L["翁如山 (0.2162%)"]
        A --> M["张立柱 (0.19999%)"]
        A --> N["曹勇 (0.188%)"]
        A --> O["尤金 (0.1829%)"]
        A --> P["巴克莱银行 (0.1712%)"]
        A --> Q["陈国山 (0.1641%)"]
        A --> R["国泰海通证券有限公司 (0.1344%)"]
    end

    subgraph "子公司"
        A --> S["南方路面机械(仙桃)有限公司 (100.0%)"]
        A --> T["泉州市南方路机移动破碎设备有限公司 (100.0%)"]
        A --> U["福建南特建材装备研究院有限公司 (100.0%)"]
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
    output_file = 'tests/updated_translation_test_results.json'
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
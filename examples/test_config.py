import sys
import os

# 将当前目录添加到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alicloud_translator import get_access_key, translate_with_alicloud

def test_config_reading():
    try:
        print("测试读取配置文件...")
        access_key_id, access_key_secret = get_access_key()
        print(f"配置文件读取成功!")
        print(f"AccessKey ID: {access_key_id}")
        print(f"AccessKey Secret: {'*' * 10}{access_key_secret[-4:]}")
        return True
    except Exception as e:
        print(f"配置文件读取失败: {str(e)}")
        return False

def test_translation_function():
    try:
        print("\n测试翻译功能...")
        # 检查配置是否存在
        access_key_id, access_key_secret = get_access_key()
        
        if not access_key_id or access_key_id == "your_access_key_id_here":
            print("错误: 配置文件中的AccessKey仍为占位符值")
            return False
        else:
            # 实际测试翻译功能
            test_text = "测试文本"
            print(f"准备翻译文本: '{test_text}'")
            result = translate_with_alicloud(test_text, "zh", "en")
            print(f"翻译结果: '{result}'")
            
            # 测试公司名称翻译
            company_text = "阿里巴巴集团控股有限公司"
            print(f"\n测试公司名称翻译: '{company_text}'")
            company_result = translate_with_alicloud(company_text, "zh", "en")
            print(f"公司名称翻译结果: '{company_result}'")
            
        print("\n翻译功能测试完成 - 成功!")
        return True
    except Exception as e:
        print(f"翻译功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== 阿里云翻译API测试 ===")
    config_ok = test_config_reading()
    if config_ok:
        test_translation_function()
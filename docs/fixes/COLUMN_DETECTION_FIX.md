# Excel列识别功能修复

## 📋 问题描述

用户上传包含"序号"列的Excel文件时，系统错误地将"序号"列识别为实体名称列，而不是正确识别"发起人名称"列。

**错误示例**：
```
列映射自动到序号1，不是发起人名称
1 → 山东蓝电电力有限公司 (100.0%)
```

## 🔧 修复方案

### 1. 精确匹配序号列
在 `_is_excluded_column()` 函数中添加精确匹配逻辑：

```python
# 精确匹配列名（序号列通常列名就是"序号"）
if col_name in ['序号', '编号', 'ID', 'id', 'No', 'NO', 'no', 'Num', 'num', 'Number', 'number', 'Index', 'index']:
    return True
```

### 2. 检测数字序列
添加数据内容检测，识别 `1, 2, 3...` 这样的序列：

```python
# 检查样本数据内容是否为序号（纯数字序列）
numeric_count = 0
sequential_count = 0

for i, value in enumerate(sample_values):
    try:
        num = int(float(str(value)))
        numeric_count += 1
        # 检查是否为序列（1, 2, 3...）
        if num == i + 1:
            sequential_count += 1
    except:
        pass

# 如果大部分是数字且呈序列，很可能是序号列
if numeric_count / total_valid >= 0.8 and sequential_count / total_valid >= 0.5:
    return True
```

### 3. 添加更具体的名称关键词
在 `entity_name` 关键词中添加更具体的名称字段：

```python
'entity_name': [
    '被投资企业名称', '企业名称', '公司名称', '投资企业', '被投资方',
    '发起人名称', '股东名称', '投资人名称',  # 新增
    'entity_name', 'company_name', 'name', '企业', '公司', '投资方',
    'entity name', 'company name', 'investor', 'investee'
],
```

### 4. 优化关键词匹配顺序
按关键词长度降序排序，优先匹配更具体的关键词：

```python
# 对关键词按长度降序排序，优先匹配长关键词
for col_type, keywords in self.column_keywords.items():
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in col_lower or keyword in col_name:
            return col_type
```

## ✅ 测试结果

### 测试数据
| 序号 | 发起人名称 | 持股比例 | 发起人类型 | 登记状态 |
|------|-----------|---------|----------|---------|
| 1 | 山东蓝电电力有限公司 | 100.0% | 企业法人 | 在业 |
| 2 | 力诺电力集团股份有限公司 | 80.5% | 企业法人 | 在业 |
| 3 | 北京XX科技有限公司 | 60.0% | 企业法人 | 在业 |

### 识别结果
| 列名 | 识别类型 | 置信度 | 状态 |
|------|---------|--------|------|
| 序号 | unknown | 0.00 | ✅ 正确排除 |
| 发起人名称 | entity_name | 1.00 | ✅ 正确识别 |
| 持股比例 | investment_ratio | 0.70 | ✅ 正确识别 |
| 发起人类型 | unknown | 0.00 | ✅ 正确排除 |
| 登记状态 | unknown | 0.00 | ✅ 正确排除 |

### 导入摘要
- **实体名称列**: 发起人名称 ✅
- **持股比例列**: 持股比例 ✅
- **总行数**: 5
- **识别列数**: 2

## 🎯 支持的列类型

### 会被正确排除的列
- **序号列**: 序号, 编号, ID, No, Number
- **类型列**: 发起人类型, 股东类型, 企业类型
- **状态列**: 登记状态, 经营状态
- **日期列**: 成立日期, 注册日期
- **金额列**: 出资额, 投资额, 注册资本

### 会被正确识别的列
- **实体名称**: 发起人名称, 股东名称, 企业名称, 公司名称
- **持股比例**: 持股比例, 出资比例, 投资比例
- **法人代表**: 法定代表人, 法人代表
- **注册资本**: 注册资本, 注册资金

## 📝 代码位置
- `src/utils/excel_smart_importer.py`
  - `_is_excluded_column()` - 排除列检测
  - `_detect_column_type()` - 列类型检测
  - `analyze_excel_columns()` - 列分析主函数

## 💡 使用建议

为了获得最佳识别效果，Excel文件的列名应该包含明确的关键词：

**推荐命名**：
- ✅ 发起人名称 / 股东名称 / 企业名称
- ✅ 持股比例 / 出资比例 / 投资比例
- ✅ 发起人类型 / 股东类型
- ✅ 登记状态 / 经营状态

**避免命名**：
- ❌ 名称（太泛泛）
- ❌ 比例（太泛泛）
- ❌ 类型（太泛泛）


# 批量导入文件类型双重验证功能

**更新日期**: 2025-10-24  
**功能**: 通过文件名 + 文件内容列名的双重验证，更准确地识别文件类型

## 📋 问题背景

### 用户需求
> "除了文件名规则，请再加一层处理，就是里面内容有控制企业或被投资企业名称，一般是对外投资，文件名里的公司就是母公司，如果文件里面有股东名称或发起人名称，一般是股东信息，公司名是子公司"

### 为什么需要双重验证？

**单纯依赖文件名的问题**：
- ❌ 文件名可能被错误命名
- ❌ 文件名可能不规范
- ❌ 文件名和内容可能不匹配

**添加内容验证的优势**：
- ✅ 更准确（列名最能反映实际内容）
- ✅ 容错性更强
- ✅ 自动纠正文件名错误

---

## 🔍 双重验证机制

### 验证流程

```
步骤 1: 文件名检测（初步判断）
   ↓
   提取文件名中的关键词
   判断可能的文件类型
   
步骤 2: 读取 Excel 文件
   ↓
   解析表头
   获取所有列名
   
步骤 3: 列名检测（精确验证）← 新增！
   ↓
   分析列名中的关键词
   计算匹配分数
   
步骤 4: 类型确认
   ↓
   if 列名检测有结果:
       使用列名检测结果 ✅ (优先级更高)
       重新分配公司角色
   else:
       使用文件名检测结果
```

---

## 🎯 列名检测规则

### 规则 1: 对外投资文件识别

**特征列名**：
```
控制企业
被投资企业（名称）
被投资单位
被投资公司
对外投资
投资企业
子公司
参股企业
```

**判断逻辑**：
- 如果列名中包含这些关键词 → **对外投资文件**
- **文件名中的公司** = 母公司（parent/投资方）

**示例**：
```
文件名: 山东蓝电电力有限公司-股东信息.xlsx
列名: ["序号", "被投资企业名称", "投资比例", "注册资本"]
            ↓
判断: 列名包含"被投资企业" → 对外投资文件
修正: shareholder → investment
角色: 山东蓝电电力有限公司 = parent (投资方)
```

### 规则 2: 股东文件识别

**特征列名**：
```
股东名称
发起人名称
投资人名称
出资人名称
股东（类型）
发起人（类型）
持股比例
出资比例
```

**判断逻辑**：
- 如果列名中包含这些关键词 → **股东文件**
- **文件名中的公司** = 子公司（child/被投资方）

**示例**：
```
文件名: 对外投资-山东蓝电电力有限公司.xlsx
列名: ["序号", "股东名称", "股东类型", "持股比例"]
            ↓
判断: 列名包含"股东名称"、"持股比例" → 股东文件
修正: investment → shareholder
角色: 山东蓝电电力有限公司 = child (被投资方)
```

### 规则 3: 计分机制

```python
investment_score = 匹配到的对外投资关键词数量
shareholder_score = 匹配到的股东关键词数量

if investment_score > shareholder_score:
    → 对外投资文件
elif shareholder_score > investment_score:
    → 股东文件
else:
    → unknown (使用文件名判断结果)
```

---

## 💡 实际应用场景

### 场景 1: 文件名错误但内容正确

**输入**：
```
文件名: 山东蓝电-股东.xlsx  (错误：暗示是股东文件)
列名: ["被投资企业", "注册资本", "投资比例"]  (实际：对外投资内容)
```

**处理**：
```
第一层（文件名）: shareholder
第二层（列名）: investment ✅
最终结果: investment
公司角色: 山东蓝电 = parent (投资方)
```

### 场景 2: 文件名模糊但内容清晰

**输入**：
```
文件名: 力诺集团企业信息.xlsx  (模糊：不确定类型)
列名: ["股东名称", "出资额", "持股比例"]  (清晰：股东信息)
```

**处理**：
```
第一层（文件名）: unknown
第二层（列名）: shareholder ✅
最终结果: shareholder
公司角色: 力诺集团 = child (被投资方)
```

### 场景 3: 新旧格式都能正确识别

**新格式**：
```
文件名: 股东信息工商登记-山东蓝电.xlsx
列名: ["股东名称", "出资比例"]
结果: shareholder ✅ (文件名和列名一致)
角色: 山东蓝电 = child
```

**旧格式**：
```
文件名: 山东蓝电-对外投资.xlsx
列名: ["控制企业", "投资额"]
结果: investment ✅ (文件名和列名一致)
角色: 山东蓝电 = parent
```

---

## 🔧 技术实现

### 核心函数

#### 1. `_detect_file_type_from_columns(df)`

```python
def _detect_file_type_from_columns(df) -> str:
    """
    从Excel文件的列名检测文件类型（第二层验证）
    
    Returns:
        'investment' | 'shareholder' | 'unknown'
    """
    # 获取所有列名
    columns_str = ' '.join([str(col).lower() for col in df.columns])
    
    # 定义关键词
    investment_keywords = ['控制企业', '被投资企业', ...]
    shareholder_keywords = ['股东名称', '发起人名称', ...]
    
    # 计算匹配分数
    investment_score = sum(1 for kw in investment_keywords if kw in columns_str)
    shareholder_score = sum(1 for kw in shareholder_keywords if kw in columns_str)
    
    # 返回最高分的类型
    if investment_score > shareholder_score:
        return 'investment'
    elif shareholder_score > investment_score:
        return 'shareholder'
    return 'unknown'
```

#### 2. 批量导入中的应用

```python
# 步骤 1: 文件名检测
file_type = _detect_file_type_from_filename(file.name)

# 步骤 2: 读取 Excel
df = pd.read_excel(file)
df = _apply_header_detection(df, ...)

# 步骤 3: 列名检测（新增）
file_type_from_columns = _detect_file_type_from_columns(df)

# 步骤 4: 优先使用列名检测结果
if file_type_from_columns != 'unknown':
    if file_type != file_type_from_columns:
        print(f"📊 基于列名修正: {file_type} → {file_type_from_columns}")
        file_type = file_type_from_columns
        
        # 重新分配公司角色
        company = _extract_company_name_from_filename(file.name)
        if file_type == 'shareholder':
            child_company = company    # 被投资方
        elif file_type == 'investment':
            parent_company = company   # 投资方
```

---

## ✅ 优势总结

### 1. **准确性提升**
- ✅ 列名是内容的直接反映，比文件名更可靠
- ✅ 自动纠正文件名错误
- ✅ 支持不规范的文件命名

### 2. **用户体验改善**
- ✅ 用户不用担心文件名格式
- ✅ 即使文件名不规范也能正确导入
- ✅ 减少手动修正的工作量

### 3. **容错能力增强**
- ✅ 文件名+内容双重验证
- ✅ 一层失败另一层兜底
- ✅ 更robust的系统

### 4. **与现有功能兼容**
- ✅ 不影响正确命名的文件
- ✅ 只在需要时才修正
- ✅ 保持向后兼容

---

## 🧪 测试场景

### 测试 1: 文件名和内容一致
```
文件名: 山东蓝电-股东信息.xlsx
列名: ["股东名称", "持股比例"]
预期: shareholder (无需修正)
结果: ✅
```

### 测试 2: 文件名错误需要修正
```
文件名: 山东蓝电-股东.xlsx
列名: ["被投资企业", "投资额"]
预期: investment (修正)
结果: ✅ 修正并输出提示
```

### 测试 3: 文件名模糊但内容清晰
```
文件名: 力诺集团.xlsx
列名: ["控制企业", "注册资本"]
预期: investment
结果: ✅
```

### 测试 4: 新格式+列名验证
```
文件名: 股东信息-ABC公司.xlsx
列名: ["股东名称", "出资比例"]
预期: shareholder (一致，无需修正)
角色: ABC公司 = child
结果: ✅
```

### 测试 5: 新格式+列名不一致
```
文件名: 股东信息-ABC公司.xlsx
列名: ["被投资企业", "投资比例"]
预期: investment (修正)
角色: ABC公司 = parent
结果: ✅ 修正并重新分配角色
```

---

## 📊 验证优先级

```
优先级 1: 列名检测结果
   ↓ (最准确，直接反映内容)
   
优先级 2: 文件名检测结果
   ↓ (辅助判断)
   
优先级 3: 用户手动选择
   ↓ (兜底方案)
```

---

## 🎯 关键词对照表

### 对外投资关键词
| 中文 | 说明 |
|------|------|
| 控制企业 | 表示对其他企业有控制权 |
| 被投资企业 | 明确表示对外投资关系 |
| 被投资单位/公司 | 同上 |
| 对外投资 | 直接说明是投资行为 |
| 子公司/参股企业 | 投资关系的体现 |

### 股东关键词
| 中文 | 说明 |
|------|------|
| 股东名称 | 最明确的股东标识 |
| 发起人名称 | 股东的另一种称呼 |
| 投资人名称 | 在被投资方视角的股东 |
| 持股比例 | 股东的核心属性 |
| 出资比例/额 | 股东信息的体现 |

---

## 📝 代码位置

### 新增函数
- `_detect_file_type_from_columns()` - 第 133-178 行
  - 位置: `src/main/manual_equity_editor.py`
  - 功能: 基于列名检测文件类型

### 修改位置
- 批量导入逻辑 - 第 4895-4918 行
  - 位置: `src/main/manual_equity_editor.py`
  - 修改: 添加列名验证和类型修正

---

## 🔄 更新记录

- **2025-10-24**: 实现双重验证机制
- **2025-10-24**: 添加基于列名的文件类型检测
- **2025-10-24**: 实现自动类型修正和角色重新分配

---

## 📚 相关文档

- `FILENAME_FORMAT_FLEXIBLE_PARSING.md` - 文件名灵活解析
- `FILENAME_PARSING_IMPROVEMENTS.md` - 文件名解析改进
- `src/main/manual_equity_editor.py` - 实现代码

---

**总结**: 现在系统同时使用文件名和文件内容进行双重验证，更准确地识别文件类型和公司角色！🎉


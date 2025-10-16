#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel智能导入工具
提供自动列识别和实体类型判断功能
"""

import pandas as pd
import re
from typing import Dict, List, Tuple, Optional, Any


class ExcelSmartImporter:
    """Excel智能导入器"""
    
    def __init__(self):
        # 定义列名关键词映射
        self.column_keywords = {
            'entity_name': [
                '被投资企业名称', '企业名称', '公司名称', '投资企业', '被投资方',
                '发起人名称', '股东名称', '投资人名称',  # 🔥 添加更具体的名称关键词
                'entity_name', 'company_name', 'name', '企业', '公司', '投资方',
                'entity name', 'company name', 'investor', 'investee'
            ],
            'english_name': [
                '英文名', '英文名称', '英文企业名称', '英文公司名称',
                'English Name', 'English', 'Name (EN)', 'Name(EN)', 'EN Name',
                'english_name', 'english name', 'name_en', 'name_english'
            ],
            'legal_representative': [
                '法定代表人', '法人代表', '负责人', '代表', '法人',
                'legal_representative', 'representative', 'director',
                'legal representative', 'representative'
            ],
            'registered_capital': [
                '注册资本', '资本', '注册资金', '资金', '资本金',
                'registered_capital', 'capital', 'fund',
                'registered capital', 'fund'
            ],
            'investment_ratio': [
                '投资比例', '持股比例', '出资比例', '比例', '股权比例', '股份比例',
                'investment_ratio', 'equity_ratio', 'share_ratio', 'percentage', 'percent',
                'investment ratio', 'equity ratio', 'share ratio', 'percentage', 'percent'
            ],
            'investment_amount': [
                '投资数额', '投资金额', '出资额', '投资额', '金额', '数额',
                'investment_amount', 'amount', 'investment', 'money',
                'investment amount', 'amount', 'money'
            ],
            'establishment_date': [
                '成立日期', '注册日期', '设立日期', '成立时间', '注册时间',
                'establishment_date', 'registration_date', 'founded_date', 'date',
                'establishment date', 'registration date', 'founded date', 'date'
            ],
            'registration_status': [
                '登记状态', '经营状态', '状态', '企业状态', '公司状态',
                'registration_status', 'status', 'business_status',
                'registration status', 'status', 'business status'
            ]
        }
        
        # 公司名称关键词
        self.company_keywords = [
            '有限公司', '有限责任公司', '股份有限公司', '股份公司', '集团', '控股',
            '投资', '科技', '实业', '贸易', '商贸', '咨询', '管理', '服务',
            '企业', '公司', '有限合伙', '合伙企业', '中心', '研究院', '研究所',
            'Co.', 'Ltd.', 'Corp.', 'Inc.', 'LLC', 'Company', 'Corporation'
        ]
        
        # 个人姓名特征（中文姓名通常2-4个字符，英文姓名通常包含空格）
        self.person_name_pattern = re.compile(r'^[\u4e00-\u9fff]{2,4}$')
        self.english_name_pattern = re.compile(r'^[A-Za-z\s]{2,30}$')
    
    def analyze_excel_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析Excel列并自动识别列类型
        
        Args:
            df: pandas DataFrame
            
        Returns:
            Dict: 包含列分析结果的字典
        """
        result = {
            'detected_columns': {},
            'column_suggestions': {},
            'sample_data': {},
            'confidence_scores': {}
        }
        
        # 分析每一列
        for col in df.columns:
            col_lower = str(col).lower()
            # 扩大采样窗口，提升在包含表头行/空值时的识别稳健性
            sample_values = df[col].dropna().head(12).astype(str).tolist()
            
            # 检测列类型
            detected_type = self._detect_column_type(col, col_lower, sample_values)
            
            if detected_type:
                result['detected_columns'][col] = detected_type
                result['column_suggestions'][col] = self._get_column_suggestion(detected_type)
                result['sample_data'][col] = sample_values
                result['confidence_scores'][col] = self._calculate_confidence(col, col_lower, sample_values, detected_type)
        
        return result
    
    def _detect_column_type(self, col_name: str, col_lower: str, sample_values: List[str]) -> Optional[str]:
        """检测列类型"""
        
        # 🔥 首先检查是否为排除列（状态、类型等不应该被识别为实体名称）
        if self._is_excluded_column(col_name, col_lower, sample_values):
            return None
        
        # 🔥 检查列名关键词 - 优先匹配更长、更具体的关键词
        # 对关键词按长度降序排序，优先匹配长关键词
        for col_type, keywords in self.column_keywords.items():
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            for keyword in sorted_keywords:
                if keyword in col_lower or keyword in col_name:
                    return col_type
        
        # 🔥 对于数字列名（如Column_0），主要依赖数据内容分析
        if col_name.startswith('Column_') or col_name.startswith('Unnamed'):
            # 🔥 调整检查顺序，优先检查比例列和金额列
            if self._is_percentage_column(sample_values):
                return 'investment_ratio'
            elif self._is_amount_column(sample_values):
                return 'investment_amount'
            elif self._is_date_column(sample_values):
                return 'establishment_date'
            elif self._is_entity_name_column(sample_values):
                return 'entity_name'
        
        # 🔥 移除备选检查，避免被排除的列仍然被识别
        return None
    
    def _is_excluded_column(self, col_name: str, col_lower: str, sample_values: List[str]) -> bool:
        """检查是否为排除列（状态、类型等不应该被识别为实体名称的列）"""
        
        # 🔥 大幅扩展排除关键词
        excluded_keywords = [
            '状态', '登记状态', '经营状态', '企业状态', '公司状态', '存续', '在业', '注销', '吊销',
            '类型', '企业类型', '公司类型', '发起人类型', '股东类型',
            '序号', '编号', 'id', 'index', 'number', 'no', 'num',
            '日期', '时间', '成立日期', '注册日期', '设立日期',
            '金额', '数额', '出资额', '投资额', '注册资本', '万元', '千元', '亿元',
            '关联', '产品', '机构', '备注', '说明', '描述',
            '法定代表人', '法人', '代表'
        ]
        
        # 🔥 精确匹配列名（序号列通常列名就是"序号"）
        if col_name in ['序号', '编号', 'ID', 'id', 'No', 'NO', 'no', 'Num', 'num', 'Number', 'number', 'Index', 'index']:
            return True
        
        # 检查列名是否包含排除关键词
        for keyword in excluded_keywords:
            if keyword in col_name or keyword in col_lower:
                return True
        
        # 🔥 检查样本数据内容是否为序号（纯数字序列）
        if sample_values:
            numeric_count = 0
            sequential_count = 0
            
            for i, value in enumerate(sample_values):
                if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                    continue
                try:
                    num = int(float(str(value)))
                    numeric_count += 1
                    # 检查是否为序列（1, 2, 3...）
                    if num == i + 1:
                        sequential_count += 1
                except:
                    pass
            
            total_valid = len([v for v in sample_values if v and str(v).lower() not in ['nan', 'none', 'null', '']])
            if total_valid > 0:
                # 🔥 如果大部分是数字且呈序列，很可能是序号列
                if numeric_count / total_valid >= 0.8 and sequential_count / total_valid >= 0.5:
                    return True
        
        # 🔥 检查样本数据内容是否为状态/类型信息
        if sample_values:
            # 🔥 状态关键词（用于识别状态列）
            status_keywords = ['在业', '注销', '吊销', '停业', '清算', '正常', '异常', '存续', '歇业']
            # 🔥 类型关键词（用于识别类型列，注意：不包含公司名称中常见的词）
            # ⚠️ 重要：不要包含"有限责任公司"、"股份有限公司"等，这些是公司名称的一部分！
            type_keywords = ['企业法人', '社团法人', '个人', '自然人', '机构']
            # 🔥 其他排除关键词
            other_exclude_keywords = ['-', 'nan', 'none', 'null', '序号', '编号', '日期', '时间', '金额', '数额', '万元', '千元', '亿元']
            
            # 🔥 如果样本数据主要是状态、类型或其他排除信息，则排除
            status_count = sum(1 for value in sample_values if any(keyword in str(value) for keyword in status_keywords))
            type_count = sum(1 for value in sample_values if any(keyword in str(value) for keyword in type_keywords))
            exclude_count = sum(1 for value in sample_values if any(keyword in str(value).lower() for keyword in other_exclude_keywords))
            
            total_valid = len([v for v in sample_values if v and str(v).lower() not in ['nan', 'none', 'null', '']])
            if total_valid > 0:
                # 🔥 更严格的排除条件（不包含百分比，因为百分比列可能是比例列）
                if (status_count + type_count + exclude_count) / total_valid >= 0.3:
                    return True
        
        return False
    
    def _is_entity_name_column(self, sample_values: List[str]) -> bool:
        """判断是否为实体名称列"""
        if not sample_values:
            return False
        
        # 🔥 首先检查是否应该被排除
        if self._should_exclude_from_entity_names(sample_values):
            return False
        
        # 检查是否包含公司关键词或个人姓名特征
        company_count = 0
        person_count = 0
        total_valid_values = 0
        
        for value in sample_values:
            if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                continue
                
            value_str = str(value).strip()
            total_valid_values += 1
            
            # 🔥 优先检查公司关键词（权重更高）
            if any(keyword in value_str for keyword in self.company_keywords):
                company_count += 1
            # 检查个人姓名特征
            elif self.person_name_pattern.match(value_str) or self.english_name_pattern.match(value_str):
                person_count += 1
        
        if total_valid_values == 0:
            return False
            
        # 🔥 改进置信度计算：公司名称权重更高
        total_valid = company_count + person_count
        confidence = total_valid / total_valid_values
        
        # 🔥 调整阈值，确保能正确识别包含公司名称的列
        if company_count > 0:
            return confidence >= 0.6  # 公司名称阈值降低到60%
        else:
            return confidence >= 0.8  # 个人名称保持80%阈值
    
    def _should_exclude_from_entity_names(self, sample_values: List[str]) -> bool:
        """检查样本数据是否应该从实体名称识别中排除"""
        if not sample_values:
            return True
        
        # 🔥 检查是否主要是短字符串、数字或状态信息
        short_string_count = 0
        numeric_count = 0
        status_count = 0
        total_valid = 0
        
        for value in sample_values:
            if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                continue
            
            value_str = str(value).strip()
            total_valid += 1
            
            # 如果字符串太短（<=3个字符），可能是状态或类型
            if len(value_str) <= 3:
                short_string_count += 1
            
            # 检查是否为纯数字（可能是序号、金额等）
            try:
                float(value_str)
                numeric_count += 1
            except:
                pass
            
            # 检查是否包含状态关键词
            status_keywords = ['在业', '注销', '吊销', '存续', '歇业', '正常', '异常']
            if any(keyword in value_str for keyword in status_keywords):
                status_count += 1
            
            # 🔥 检查是否包含百分比符号（应该排除，因为不是实体名称）
            if '%' in value_str or '％' in value_str:
                numeric_count += 1
        
        if total_valid > 0:
            # 🔥 降低阈值，更严格地排除
            if (short_string_count + numeric_count + status_count) / total_valid >= 0.2:
                return True
        
        return False
    
    def _is_percentage_column(self, sample_values: List[str]) -> bool:
        """判断是否为比例列"""
        if not sample_values:
            return False
        
        numeric_count = 0
        total_valid = 0
        
        for value in sample_values:
            if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                continue
                
            total_valid += 1
            value_str = str(value).strip()
            
            try:
                # 🔥 改进：支持更多百分比格式
                # 处理百分比格式（如"100%", "(100%)", "100"等）
                clean_value = value_str.replace('%', '').replace('％', '').replace('(', '').replace(')', '').strip()
                num = float(clean_value)
                if 0 <= num <= 100:
                    numeric_count += 1
            except:
                # 🔥 尝试正则表达式提取数字
                import re
                patterns = [
                    r'(\d+(?:\.\d+)?)%',  # 42.71%
                    r'\((\d+(?:\.\d+)?)\)',  # (42.71)
                    r'(\d+(?:\.\d+)?)',  # 42.71
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, value_str)
                    if match:
                        try:
                            num = float(match.group(1))
                            if 0 <= num <= 100:
                                numeric_count += 1
                                break
                        except ValueError:
                            continue
        
        if total_valid == 0:
            return False
            
        # 🔥 降低阈值，提高识别准确性
        return numeric_count >= total_valid * 0.5
    
    def _is_amount_column(self, sample_values: List[str]) -> bool:
        """判断是否为金额列"""
        if not sample_values:
            return False
        
        numeric_count = 0
        amount_keywords = ['万', '元', '千', '亿', '万元', '千元', '亿元']
        
        for value in sample_values:
            if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                continue
                
            value_str = str(value)
            
            # 🔥 检查是否包含金额关键词
            if any(keyword in value_str for keyword in amount_keywords):
                numeric_count += 1
                continue
                
            try:
                # 移除常见的金额符号
                clean_value = value_str.replace('¥', '').replace('$', '').replace(',', '').replace('万', '0000')
                float(clean_value)
                numeric_count += 1
            except:
                pass
        
        # 🔥 提高阈值，确保只有真正的金额列才被识别
        return numeric_count >= len(sample_values) * 0.6
    
    def _is_date_column(self, sample_values: List[str]) -> bool:
        """判断是否为日期列"""
        if not sample_values:
            return False
        
        date_count = 0
        for value in sample_values:
            if self._is_date_format(str(value)):
                date_count += 1
        
        return date_count >= len(sample_values) * 0.6
    
    def _is_date_format(self, value: str) -> bool:
        """检查是否为日期格式"""
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{4}/\d{1,2}/\d{1,2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, value.strip()):
                return True
        return False
    
    def _get_column_suggestion(self, col_type: str) -> str:
        """获取列建议"""
        suggestions = {
            'entity_name': 'Entity Name Column',
            'legal_representative': 'Legal Representative Column',
            'registered_capital': 'Registered Capital Column',
            'investment_ratio': 'Investment Ratio Column',
            'investment_amount': 'Investment Amount Column',
            'establishment_date': 'Establishment Date Column',
            'registration_status': 'Registration Status Column'
        }
        return suggestions.get(col_type, 'Unknown Column')
    
    def _calculate_confidence(self, col_name: str, col_lower: str, sample_values: List[str], detected_type: str) -> float:
        """计算检测置信度"""
        confidence = 0.0
        
        # 🔥 只有真正匹配的列名才给基础分
        if detected_type == 'entity_name':
            # 检查列名是否包含实体名称相关关键词
            entity_name_keywords = ['名称', 'name', 'entity', 'company', '企业', '公司']
            if any(keyword in col_lower or keyword in col_name for keyword in entity_name_keywords):
                confidence += 0.4
        elif detected_type == 'investment_ratio':
            # 检查列名是否包含比例相关关键词
            ratio_keywords = ['比例', 'ratio', 'percent', '百分比', '持股']
            if any(keyword in col_lower or keyword in col_name for keyword in ratio_keywords):
                confidence += 0.4
        elif detected_type == 'investment_amount':
            # 检查列名是否包含金额相关关键词
            amount_keywords = ['金额', 'amount', '出资', '投资额']
            if any(keyword in col_lower or keyword in col_name for keyword in amount_keywords):
                confidence += 0.4
        elif detected_type == 'establishment_date':
            # 检查列名是否包含日期相关关键词
            date_keywords = ['日期', 'date', '成立', '注册']
            if any(keyword in col_lower or keyword in col_name for keyword in date_keywords):
                confidence += 0.4
        
        # 数据内容匹配加分
        if detected_type == 'entity_name':
            if self._is_entity_name_column(sample_values):
                # 计算实际的公司/个人名称比例
                company_count = 0
                person_count = 0
                total_valid_values = 0
                
                for value in sample_values:
                    if not value or str(value).lower() in ['nan', 'none', 'null', '']:
                        continue
                    value_str = str(value).strip()
                    total_valid_values += 1
                    
                    if any(keyword in value_str for keyword in self.company_keywords):
                        company_count += 1
                    elif self.person_name_pattern.match(value_str) or self.english_name_pattern.match(value_str):
                        person_count += 1
                
                if total_valid_values > 0:
                    # 基于实际匹配比例计算置信度
                    match_ratio = (company_count + person_count) / total_valid_values
                    confidence += match_ratio * 0.6  # 内容匹配权重更高
                    
        elif detected_type == 'investment_ratio' and self._is_percentage_column(sample_values):
            confidence += 0.3
        elif detected_type == 'investment_amount' and self._is_amount_column(sample_values):
            confidence += 0.3
        elif detected_type == 'establishment_date' and self._is_date_column(sample_values):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def auto_detect_entity_type(self, entity_name: str) -> str:
        """
        自动判断实体类型
        
        Args:
            entity_name: 实体名称
            
        Returns:
            str: 'company' 或 'person'
        """
        if not entity_name or pd.isna(entity_name):
            return 'company'  # 默认公司
        
        entity_name = str(entity_name).strip()
        
        # 检查是否包含公司关键词
        if any(keyword in entity_name for keyword in self.company_keywords):
            return 'company'
        
        # 检查是否为个人姓名（中文或英文）
        if self.person_name_pattern.match(entity_name) or self.english_name_pattern.match(entity_name):
            return 'person'
        
        # 检查长度：公司名通常较长，个人姓名较短
        if len(entity_name) <= 4:
            return 'person'
        else:
            return 'company'
    
    def get_import_summary(self, df: pd.DataFrame, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成导入摘要
        
        Args:
            df: pandas DataFrame
            analysis_result: 分析结果
            
        Returns:
            Dict: 导入摘要
        """
        summary = {
            'total_rows': len(df),
            'detected_columns': len(analysis_result['detected_columns']),
            'entity_name_column': None,
            'investment_ratio_column': None,
            'entity_type_distribution': {'company': 0, 'person': 0},
            'confidence_summary': {}
        }
        
        # 找到关键列
        for col, col_type in analysis_result['detected_columns'].items():
            if col_type == 'entity_name':
                summary['entity_name_column'] = col
            elif col_type == 'investment_ratio':
                summary['investment_ratio_column'] = col
        
        # 分析实体类型分布
        if summary['entity_name_column']:
            entity_col = summary['entity_name_column']
            for entity_name in df[entity_col].dropna():
                entity_type = self.auto_detect_entity_type(entity_name)
                summary['entity_type_distribution'][entity_type] += 1
        
        # 置信度摘要
        for col, confidence in analysis_result['confidence_scores'].items():
            summary['confidence_summary'][col] = confidence
        
        return summary


def create_smart_excel_importer() -> ExcelSmartImporter:
    """创建智能Excel导入器实例"""
    return ExcelSmartImporter()

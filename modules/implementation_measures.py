import json
import json5
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import streamlit as st

class ImplementationMeasuresExtractor:
    """
    实施举措提取工具类
    用于从大模型输出中提取优化策略结果，并匹配对应的实施举措
    """
    
    def __init__(self, strategy_list_key: str = "优化策略列表", measures_list_key: str = "实施举措列表"):
        self.strategy_list_key = strategy_list_key
        self.measures_list_key = measures_list_key
    
    def extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从大模型输出中提取json包裹的内容
        :param response: 大模型输出的文本
        :return: 解析后的JSON字典，如果提取失败返回None
        """
        try:
            # 移除可能的换行符和多余空格
            response = response.strip()
            
            # 尝试多种方式提取JSON内容
            json_str = None
            
            # 1. 提取完整的 ```json ``` 包裹的内容
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            else:
                # 2. 尝试提取完整的 ``` ``` 包裹的内容（不指定语言）
                json_pattern = r'```\s*([\s\S]*?)\s*```'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                else:
                    # 3. 处理不完整的Markdown JSON包装（只有开头没有结尾）
                    start_match = re.search(r'```(?:json)?\s*', response)
                    if start_match:
                        # 从标记后开始提取所有内容作为可能的JSON
                        json_content = response[start_match.end():].strip()
                        if json_content:
                            json_str = json_content
                    else:
                        # 4. 尝试提取没有包裹标记的JSON
                        json_pattern = r'\{[\s\S]*\}'
                        match = re.search(json_pattern, response, re.DOTALL)
                        if match:
                            json_str = match.group(0).strip()
                        else:
                            return None
            
            if not json_str:
                return None
            
            # 解析JSON，优先使用标准json库
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 标准解析失败，才使用json5进行修正
                try:
                    return json5.loads(json_str)
                except Exception:
                    # 尝试增强修复：处理字符串没有闭合的情况
                    try:
                        # 修复1：处理没有闭合的字符串
                        if json_str.count('"') % 2 != 0:
                            # 闭合最后一个字符串
                            fixed_json = json_str.rstrip() + '"'
                            return json5.loads(fixed_json)
                    except Exception:
                        # 尝试处理单引号格式
                        try:
                            import ast
                            return ast.literal_eval(json_str)
                        except (SyntaxError, ValueError, NameError):
                            return None
        except Exception:
            return None
    
    def extract_strategies(self, json_data: Dict[str, Any]) -> List[str]:
        """
        从JSON数据中提取优化策略结果
        :param json_data: 解析后的JSON字典
        :return: 优化策略结果列表
        """
        try:
            # 初始化优化策略结果
            strategies = []
            
            # 遍历JSON数据，查找策略列表字段
            def find_strategies(obj):
                nonlocal strategies
                if isinstance(obj, dict):
                    if self.strategy_list_key in obj:
                        result = obj[self.strategy_list_key]
                        if isinstance(result, list):
                            for item in result:
                                if isinstance(item, dict) and "优化策略" in item:
                                    strategies.append(item["优化策略"])
                                elif isinstance(item, str):
                                    strategies.append(item)
                        elif isinstance(result, str):
                            # 尝试分割字符串
                            if ',' in result:
                                # 逗号分隔
                                strategies.extend([strategy.strip() for strategy in result.split(',') if strategy.strip()])
                            else:
                                # 中文顿号分隔
                                strategies.extend([strategy.strip() for strategy in result.split('、') if strategy.strip()])
                    else:
                        # 递归查找
                        for value in obj.values():
                            find_strategies(value)
                elif isinstance(obj, list):
                    for item in obj:
                        find_strategies(item)
                elif isinstance(obj, str):
                    # 尝试从字符串中提取JSON
                    extracted_json = self.extract_json_from_response(obj)
                    if extracted_json:
                        find_strategies(extracted_json)
            
            # 开始查找
            find_strategies(json_data)
            
            # 确保返回的是列表，且每个元素都是字符串
            return [str(strategy).strip() for strategy in strategies if str(strategy).strip()]
        except Exception:
            return []
    
    def load_measures_mapping(self, excel_path: str) -> Dict[str, List[Dict[str, str]]]:
        """
        从Excel表格加载优化策略到实施举措的映射
        :param excel_path: Excel文件路径
        :return: 优化策略到实施举措的映射字典
        """
        try:
            df = pd.read_excel(excel_path)
            
            # 检查必要列是否存在
            required_cols = ['优化策略', '实施举措', '实施举措内涵']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Excel表格缺少必要列：{col}")
            
            # 构建映射字典
            measures_mapping = {}
            
            for _, row in df.iterrows():
                strategy = str(row['优化策略']).strip()
                implementation_measure = str(row['实施举措']).strip()
                measure_content = str(row['实施举措内涵']).strip()
                
                if strategy not in measures_mapping:
                    measures_mapping[strategy] = []
                
                measures_mapping[strategy].append({
                    '实施举措': implementation_measure,
                    '实施举措内涵': measure_content
                })
            
            return measures_mapping
        except Exception as e:
            raise Exception(f"加载Excel表格失败：{str(e)}")
    
    def match_measures(self, strategies: List[str], measures_mapping: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, Any]]:
        """
        根据优化策略结果匹配对应的实施举措
        :param strategies: 优化策略结果列表
        :param measures_mapping: 优化策略到实施举措的映射字典
        :return: 匹配后的结果列表
        """
        matched_results = []
        
        # 获取所有的举措键，用于匹配
        measure_keys = list(measures_mapping.keys())
        
        for strategy in strategies:
            # 清理优化策略字符串，移除可能的Markdown格式和多余字符
            cleaned_strategy = strategy.strip()
            if cleaned_strategy.startswith('```json'):
                # 提取Markdown中的JSON
                extracted_json = self.extract_json_from_response(cleaned_strategy)
                if extracted_json:
                    # 从提取的JSON中获取优化策略结果列表
                    nested_strategies = extracted_json.get(self.strategy_list_key, [])
                    if nested_strategies and isinstance(nested_strategies, list):
                        # 递归处理嵌套的优化策略结果
                        nested_matched = self.match_measures(nested_strategies, measures_mapping)
                        matched_results.extend(nested_matched)
                        continue
                # 如果无法提取JSON，尝试清理字符串
                cleaned_strategy = re.sub(r'```json\s*|[\s\S]*?\{[\s\S]*\}[\s\S]*?```', '', cleaned_strategy).strip()
            elif cleaned_strategy.startswith('{') and cleaned_strategy.endswith('}'):
                # 如果是JSON字符串，尝试解析
                try:
                    json_obj = json.loads(cleaned_strategy)
                    nested_strategies = json_obj.get(self.strategy_list_key, [])
                    if nested_strategies and isinstance(nested_strategies, list):
                        # 递归处理嵌套的优化策略结果
                        nested_matched = self.match_measures(nested_strategies, measures_mapping)
                        matched_results.extend(nested_matched)
                        continue
                except json.JSONDecodeError:
                    pass
            
            if not cleaned_strategy:
                continue
            
            # 直接匹配
            if cleaned_strategy in measures_mapping:
                measures = measures_mapping[cleaned_strategy]
                matched_results.append({
                    '优化策略': cleaned_strategy,
                    self.measures_list_key: measures
                })
            else:
                # 尝试模糊匹配，处理可能的空格、标点符号差异
                matched = False
                for key in measure_keys:
                    # 清理键名，用于比较
                    cleaned_key = key.strip()
                    if cleaned_key == cleaned_strategy:
                        measures = measures_mapping[key]
                        matched_results.append({
                            '优化策略': cleaned_strategy,
                            self.measures_list_key: measures
                        })
                        matched = True
                        break
                if not matched:
                    matched_results.append({
                        '优化策略': cleaned_strategy,
                        self.measures_list_key: []
                    })
        
        return matched_results
    
    def generate_json_result(self, matched_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成JSON格式的结果
        :param matched_results: 匹配后的结果列表
        :return: JSON格式的结果字典
        """
        return {
            '优化策略及实施举措': matched_results
        }
    
    def generate_markdown_result(self, matched_results: List[Dict[str, Any]]) -> str:
        """
        生成Markdown格式的结果
        :param matched_results: 匹配后的结果列表
        :return: Markdown格式的结果字符串
        """
        md_content = "# 优化策略及实施举措\n\n"
        
        # 按图片名称分组
        image_groups = {}
        for result in matched_results:
            image_name = result.get('image_name', '未知图片')
            if image_name not in image_groups:
                image_groups[image_name] = []
            image_groups[image_name].append(result)
        
        # 生成每个图片的结果
        for image_name, results in image_groups.items():
            md_content += f"## {image_name}\n\n"
            
            # 去重优化策略
            unique_strategies = {}
            for result in results:
                strategy = result['优化策略']
                if strategy not in unique_strategies:
                    unique_strategies[strategy] = result[self.measures_list_key]
            
            # 生成每个优化策略的结果
            for strategy, measures in unique_strategies.items():
                md_content += f"### {strategy}\n\n"
                
                if measures:
                    for measure in measures:
                        md_content += f"**实施举措**：{measure['实施举措']}\n"
                        md_content += f"**内涵**：{measure['实施举措内涵']}\n\n"
                else:
                    md_content += "**未找到对应的实施举措**\n\n"
        
        return md_content
    
    def save_result(self, result: Any, file_path: str, file_type: str = 'json') -> None:
        """
        保存结果到文件
        :param result: 要保存的结果
        :param file_path: 文件路径
        :param file_type: 文件类型，可选值：'json' 或 'markdown'
        """
        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            if file_type == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            elif file_type == 'markdown':
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result)
        except Exception as e:
            raise Exception(f"保存结果失败：{str(e)}")
    
    def process_file(self, file_content: str, excel_path: str) -> Tuple[Dict[str, Any], str, pd.DataFrame]:
        """
        处理文件内容，提取优化策略并匹配实施举措
        :param file_content: 文件内容
        :param excel_path: Excel举措映射文件路径
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            # 步骤1：提取JSON
            json_data = self.extract_json_from_response(file_content)
            if not json_data:
                raise ValueError("无法从文件中提取有效的JSON数据")
            
            # 步骤2：提取优化策略结果
            strategies = self.extract_strategies(json_data)
            
            # 步骤3：添加image_name（从JSON数据中提取或使用默认值）
            image_name = json_data.get("image_name", json_data.get("image_basename", "未知图片"))
            
            # 检查是否为"无明显问题"情况或没有识别到任何策略
            has_no_obvious_problem = any("无明显问题" in strategy for strategy in strategies)
            has_no_strategies = not strategies
            
            if has_no_obvious_problem or has_no_strategies:
                # 无明显问题或没有识别到任何策略，统一使用新的提示信息
                # 生成JSON结果
                json_result = {
                    'image_implementation_measures': [{ 
                        "image_name": image_name,
                        "优化策略及实施举措": [{ 
                            "优化策略": "未识别到具体策略",
                            self.measures_list_key: [],
                            "备注": "该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考"
                        }]
                    }]
                }
                
                # 生成Markdown结果
                markdown_result = f"# 优化策略及实施举措\n\n## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考\n"
                
                # 生成Excel结果
                excel_result_df = pd.DataFrame([{
                    'image_basename': image_name,
                    '优化策略': '未识别到具体策略',
                    '实施举措': '',
                    '实施举措内涵': '',
                    'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考'
                }])
                
                return json_result, markdown_result, excel_result_df
            
            # 正常情况：有优化策略结果，需要匹配实施举措
            # 步骤4：加载举措映射
            measures_mapping = self.load_measures_mapping(excel_path)
            
            # 步骤5：匹配实施举措
            matched_results = self.match_measures(strategies, measures_mapping)
            
            # 步骤6：添加image_name到匹配结果
            for result in matched_results:
                result['image_name'] = image_name
            
            # 去重优化策略
            unique_strategies = {}
            for result in matched_results:
                strategy = result['优化策略']
                if strategy not in unique_strategies:
                    unique_strategies[strategy] = result[self.measures_list_key]
            
            # 检查是否所有举措列表都为空
            all_empty = all(len(measures) == 0 for measures in unique_strategies.values())
            
            if all_empty:
                # 所有举措列表都为空，返回特定提示信息
                # 生成JSON结果
                json_result = {
                    'image_implementation_measures': [{ 
                        "image_name": image_name,
                        "优化策略及实施举措": [{ 
                            "优化策略": '; '.join(unique_strategies.keys()),
                            self.measures_list_key: [],
                            "备注": "该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考"
                        }]
                    }]
                }
                
                # 生成Markdown结果
                markdown_result = f"# 优化策略及实施举措\n\n## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考\n"
                
                # 生成Excel结果
                excel_result_df = pd.DataFrame([{
                    'image_basename': image_name,
                    '优化策略': '; '.join(unique_strategies.keys()),
                    '实施举措': '',
                    '实施举措内涵': '',
                    'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考'
                }])
            else:
                # 正常情况：有非空举措列表
                # 生成JSON结果
                image_json_result = {
                    "image_name": image_name,
                    "优化策略及实施举措": []
                }
                
                for strategy, measures in unique_strategies.items():
                    image_json_result["优化策略及实施举措"].append({
                        "优化策略": strategy,
                        self.measures_list_key: measures
                    })
                
                json_result = {
                    'image_implementation_measures': [image_json_result]
                }
                
                # 生成Markdown结果
                markdown_result = f"# 优化策略及实施举措\n\n"
                image_markdown = f"## {image_name}\n\n"
                image_markdown += "该街道断面优化策略结果分别关联的实施举措如下：\n\n"
                
                for strategy_idx, (strategy, measures) in enumerate(unique_strategies.items(), 1):
                    if measures:
                        measure_list = []
                        for m_idx, measure in enumerate(measures, 1):
                            if m_idx == 1:
                                number = "①"
                            elif m_idx == 2:
                                number = "②"
                            elif m_idx == 3:
                                number = "③"
                            elif m_idx == 4:
                                number = "④"
                            elif m_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{m_idx}、"
                            measure_list.append(f"{number}{measure['实施举措']}，其内涵为{measure['实施举措内涵']}")
                        image_markdown += f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n\n"
                    else:
                        image_markdown += f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n\n"
                
                markdown_result += image_markdown
                
                # 生成Excel结果
                all_strategies = []
                all_measures = []
                all_measure_contents = []
                all_md_contents = []
                
                for strategy_idx, (strategy, measures) in enumerate(unique_strategies.items(), 1):
                    all_strategies.append(strategy)
                    all_measures.extend([m['实施举措'] for m in measures])
                    all_measure_contents.extend([m['实施举措内涵'] for m in measures])
                    
                    if measures:
                        measure_list = []
                        for m_idx, measure in enumerate(measures, 1):
                            if m_idx == 1:
                                number = "①"
                            elif m_idx == 2:
                                number = "②"
                            elif m_idx == 3:
                                number = "③"
                            elif m_idx == 4:
                                number = "④"
                            elif m_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{m_idx}、"
                            measure_list.append(f"{number}{measure['实施举措']}，其内涵为{measure['实施举措内涵']}")
                        md_content = f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n"
                    else:
                        md_content = f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n"
                    all_md_contents.append(md_content)
                
                excel_md_content = "该街道断面优化策略结果分别关联的实施举措如下：\n\n" + ''.join(all_md_contents)
                
                excel_result = {
                    'image_basename': image_name,
                    '优化策略': '; '.join(all_strategies),
                    '实施举措': '; '.join(all_measures),
                    '实施举措内涵': '; '.join(all_measure_contents),
                    'markdown结果': excel_md_content
                }
                
                excel_result_df = pd.DataFrame([excel_result])
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理文件失败：{str(e)}")
    
    def process_jsonl_file(self, file_path: str, excel_path: str, show_progress: bool = True) -> Tuple[Dict[str, Any], str, pd.DataFrame]:
        """
        处理JSONL文件，提取所有优化策略并匹配实施举措
        :param file_path: JSONL文件路径
        :param excel_path: Excel举措映射文件路径
        :param show_progress: 是否显示进度条
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            # 按图片分组的结果字典
            image_results = {}
            excel_results = []
            
            # 读取所有行并计算总行数，用于进度条
            total_lines = 0
            lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(line)
                        total_lines += 1
            
            # 初始化进度条
            progress_bar = None
            if show_progress:
                progress_bar = st.progress(0.0, text="正在处理JSONL文件...")
            
            # 处理每一行
            for idx, line in enumerate(lines):
                # 提取JSON
                json_data = self.extract_json_from_response(line)
                if json_data:
                    # 提取优化策略
                    strategies = self.extract_strategies(json_data)
                    
                    # 添加image_name（从JSON数据中提取或使用默认值）
                    image_name = json_data.get("image_name", json_data.get("image_basename", "未知图片"))
                    
                    # 检查是否为"无明显问题"情况或没有识别到任何策略
                    has_no_obvious_problem = any("无明显问题" in strategy for strategy in strategies)
                    has_no_strategies = not strategies
                    
                    if has_no_obvious_problem or has_no_strategies:
                        # 无明显问题或没有识别到任何策略，统一使用新的提示信息
                        # 添加到image_results
                        if image_name not in image_results:
                            image_results[image_name] = []
                        image_results[image_name].append({
                            '优化策略': '未识别到具体策略',
                            self.measures_list_key: [],
                            'image_name': image_name
                        })
                    else:
                        # 正常情况：无论优化策略结果是否为空，都需要处理
                        # 加载举措映射
                        measures_mapping = self.load_measures_mapping(excel_path)
                        
                        # 匹配实施举措
                        matched_results = self.match_measures(strategies, measures_mapping)
                        
                        # 添加image_name到匹配结果
                        for result in matched_results:
                            result['image_name'] = image_name
                        
                        # 按图片分组保存结果
                        if image_name not in image_results:
                            image_results[image_name] = []
                        image_results[image_name].extend(matched_results)
                        
                        # 如果没有匹配到任何结果，也要添加一个空结果
                        if not matched_results:
                            image_results[image_name].append({
                                '优化策略': '未识别到具体策略',
                                self.measures_list_key: [],
                                'image_name': image_name
                            })
                
                # 更新进度条
                if show_progress and progress_bar:
                    progress = (idx + 1) / total_lines
                    progress_bar.progress(progress, text=f"正在处理第 {idx + 1}/{total_lines} 行...")
            
            if not image_results:
                raise ValueError("未找到有效的优化策略结果")
            
            # 生成综合JSON结果（按图片分组）
            json_result = {
                'image_implementation_measures': []
            }
            
            # 生成综合Markdown结果
            markdown_result = "# 优化策略及实施举措\n\n"
            
            # 生成Excel结果
            excel_results = []
            
            # 遍历每个图片的结果
            for image_name, results in image_results.items():
                # 检查是否为"无明显问题"情况（现在统一使用"未识别到具体策略"）
                has_no_obvious_problem = any("未识别到具体策略" in result['优化策略'] for result in results) or any("无明显问题" in result['优化策略'] for result in results)
                
                if has_no_obvious_problem:
                    # 无明显问题，统一使用新的提示信息
                    # 构建图片的JSON结果
                    image_json_result = {
                        "image_name": image_name,
                        "优化策略及实施举措": [{
                            "优化策略": "未识别到具体策略",
                            self.measures_list_key: [],
                            "备注": "该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考"
                        }]
                    }
                    
                    # 构建图片的Markdown结果
                    image_markdown = f"## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考\n\n"
                    
                    # 生成一行Excel结果
                    excel_results.append({
                        'image_basename': image_name,
                        '优化策略': '未识别到具体策略',
                        '实施举措': '',
                        '实施举措内涵': '',
                        'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考'
                    })
                else:
                    # 正常情况：有优化策略结果，需要匹配实施举措
                    # 去重优化策略
                    unique_strategies = {}
                    for result in results:
                        strategy = result['优化策略']
                        if strategy not in unique_strategies:
                            unique_strategies[strategy] = result[self.measures_list_key]
                    
                    # 检查是否所有举措列表都为空
                    all_empty = all(len(measures) == 0 for measures in unique_strategies.values())
                    
                    if all_empty:
                        # 所有举措列表都为空，返回特定提示信息
                        # 构建图片的JSON结果
                        image_json_result = {
                            "image_name": image_name,
                            "优化策略及实施举措": [{
                                "优化策略": "未识别到具体策略",
                                self.measures_list_key: [],
                                "备注": "该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考"
                            }]
                        }
                        
                        # 构建图片的Markdown结果
                        image_markdown = f"## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考\n\n"
                        
                        # 生成一行Excel结果
                        excel_results.append({
                            'image_basename': image_name,
                            '优化策略': '; '.join(unique_strategies.keys()),
                            '实施举措': '',
                            '实施举措内涵': '',
                            'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考'
                        })
                    else:
                        # 正常情况：有非空举措列表
                        # 构建图片的JSON结果
                        image_json_result = {
                            "image_name": image_name,
                            "优化策略及实施举措": []
                        }
                        
                        # 遍历每个优化策略，添加到图片的JSON结果
                        for strategy, measures in unique_strategies.items():
                            image_json_result["优化策略及实施举措"].append({
                                "优化策略": strategy,
                                self.measures_list_key: measures
                            })
                        
                        # 构建图片的Markdown结果
                        image_markdown = f"## {image_name}\n\n"
                        image_markdown += "该街道断面优化策略结果分别关联的实施举措如下：\n\n"
                        
                        # 构建图片的所有优化策略和实施举措（用于Excel）
                        all_strategies = []
                        all_measures = []
                        all_measure_contents = []
                        all_md_contents = []
                        
                        # 按顺序编号优化策略
                        for strategy_idx, (strategy, measures) in enumerate(unique_strategies.items(), 1):
                            all_strategies.append(strategy)
                            all_measures.extend([m['实施举措'] for m in measures])
                            all_measure_contents.extend([m['实施举措内涵'] for m in measures])
                            
                            if measures:
                                # 构建实施举措列表
                                measure_list = []
                                for m_idx, measure in enumerate(measures, 1):
                                    # 根据索引选择对应的中文编号
                                    if m_idx == 1:
                                        number = "①"
                                    elif m_idx == 2:
                                        number = "②"
                                    elif m_idx == 3:
                                        number = "③"
                                    elif m_idx == 4:
                                        number = "④"
                                    elif m_idx == 5:
                                        number = "⑤"
                                    else:
                                        number = f"{m_idx}、"
                                    measure_list.append(f"{number}{measure['实施举措']}，其内涵为{measure['实施举措内涵']}")
                                
                                # 组合成流畅的句子
                                image_markdown += f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n\n"
                                
                                # 构建Excel中的Markdown结果（不包含图片名称）
                                md_content = f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n"
                            else:
                                image_markdown += f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n\n"
                                md_content = f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n"
                            all_md_contents.append(md_content)
                        
                        # 生成Excel中的Markdown结果（包含开头语句）
                        excel_md_content = "该街道断面优化策略结果分别关联的实施举措如下：\n\n" + ''.join(all_md_contents)
                        
                        # 生成一行Excel结果
                        excel_results.append({
                            'image_basename': image_name,
                            '优化策略': '; '.join(all_strategies),
                            '实施举措': '; '.join(all_measures),
                            '实施举措内涵': '; '.join(all_measure_contents),
                            'markdown结果': excel_md_content
                        })
                
                # 添加到综合JSON结果
                json_result['image_implementation_measures'].append(image_json_result)
                
                # 添加到综合Markdown结果
                markdown_result += image_markdown
            
            excel_result_df = pd.DataFrame(excel_results)
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理JSONL文件失败：{str(e)}")
    
    def process_excel_file(self, file_content: bytes, excel_path: str, image_basename_col: str, strategies_col: str, show_progress: bool = True) -> Tuple[Dict[str, Any], str, pd.DataFrame]:
        """
        处理Excel文件，提取优化策略结果并匹配实施举措
        :param file_content: Excel文件内容（字节流）
        :param excel_path: Excel举措映射文件路径
        :param image_basename_col: 图片名称列名
        :param strategies_col: 优化策略列表列名
        :param show_progress: 是否显示进度条
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            import io
            
            # 读取Excel文件
            df = pd.read_excel(io.BytesIO(file_content))
            
            # 检查必要列是否存在
            required_cols = [image_basename_col, strategies_col]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Excel表格缺少必要列：{col}")
            
            # 按图片分组的结果字典
            image_results = {}
            excel_results = []
            
            # 加载举措映射
            measures_mapping = self.load_measures_mapping(excel_path)
            
            # 初始化进度条
            progress_bar = None
            if show_progress:
                progress_bar = st.progress(0.0, text="正在处理Excel文件...")
                total_rows = len(df)
            
            # 遍历每一行，提取优化策略结果
            for idx, row in df.iterrows():
                # 获取图片名称
                image_basename = str(row[image_basename_col]).strip()
                
                # 获取优化策略结果
                strategies_str = str(row[strategies_col]).strip()
                strategies = []
                
                if strategies_str and strategies_str != "nan":
                    # 尝试解析为JSON列表
                    try:
                        parsed_strategies = json.loads(strategies_str)
                        if isinstance(parsed_strategies, list):
                            strategies = [str(strategy).strip() for strategy in parsed_strategies if str(strategy).strip()]
                        elif isinstance(parsed_strategies, str):
                            # 如果解析后是字符串，尝试按分隔符分割
                            if ',' in parsed_strategies:
                                # 逗号分隔
                                strategies = [strategy.strip() for strategy in parsed_strategies.split(',') if strategy.strip()]
                            else:
                                # 中文顿号分隔
                                strategies = [strategy.strip() for strategy in parsed_strategies.split('、') if strategy.strip()]
                    except (json.JSONDecodeError, ValueError):
                        # 如果JSON解析失败，尝试按分隔符分割
                        if ',' in strategies_str:
                            # 逗号分隔
                            strategies = [strategy.strip() for strategy in strategies_str.split(',') if strategy.strip()]
                        else:
                            # 中文顿号分隔
                            strategies = [strategy.strip() for strategy in strategies_str.split('、') if strategy.strip()]
                    
                # 检查是否为"无明显问题"情况或没有识别到任何策略
                has_no_obvious_problem = any("无明显问题" in strategy for strategy in strategies)
                has_no_strategies = not strategies
                
                if has_no_obvious_problem or has_no_strategies:
                    # 无明显问题或没有识别到任何策略，统一使用新的提示信息
                    # 添加到image_results
                    if image_basename not in image_results:
                        image_results[image_basename] = []
                    image_results[image_basename].append({
                        '优化策略': '未识别到具体策略',
                        self.measures_list_key: [],
                        'image_name': image_basename
                    })
                else:
                    # 正常情况：无论优化策略结果是否为空，都需要匹配实施举措
                    # 匹配实施举措
                    matched_results = self.match_measures(strategies, measures_mapping)
                    
                    # 添加图片名称到结果中并按图片分组
                    if image_basename not in image_results:
                        image_results[image_basename] = []
                    
                    if matched_results:
                        for result in matched_results:
                            result['image_name'] = image_basename
                            image_results[image_basename].append(result)
                    else:
                        # 如果没有匹配到任何结果，也要添加一个空结果
                        image_results[image_basename].append({
                            '优化策略': '未识别到具体策略',
                            self.measures_list_key: [],
                            'image_name': image_basename
                        })
                
                # 更新进度条
                if show_progress and progress_bar:
                    progress = (idx + 1) / total_rows
                    progress_bar.progress(progress, text=f"正在处理第 {idx + 1}/{total_rows} 行...")
            
            if not image_results:
                raise ValueError("未找到有效的优化策略结果")
            
            # 生成综合JSON结果（按图片分组）
            json_result = {
                'image_implementation_measures': []
            }
            
            # 生成综合Markdown结果
            markdown_result = "# 优化策略及实施举措\n\n"
            
            # 生成Excel结果
            excel_results = []
            
            # 遍历每个图片的结果
            for image_name, results in image_results.items():
                # 检查是否为"无明显问题"情况（现在统一使用"未识别到具体策略"）
                has_no_obvious_problem = any("未识别到具体策略" in result['优化策略'] for result in results) or any("无明显问题" in result['优化策略'] for result in results)
                
                if has_no_obvious_problem:
                    # 无明显问题，统一使用新的提示信息
                    # 构建图片的JSON结果
                    image_json_result = {
                        "image_name": image_name,
                        "优化策略及实施举措": [{
                            "优化策略": "未识别到具体策略",
                            self.measures_list_key: [],
                            "备注": "该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考"
                        }]
                    }
                    
                    # 构建图片的Markdown结果
                    image_markdown = f"## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考\n\n"
                    
                    # 生成一行Excel结果
                    excel_results.append({
                        'image_basename': image_name,
                        '优化策略': '未识别到具体策略',
                        '实施举措': '',
                        '实施举措内涵': '',
                        'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的优化策略/实施举措参考'
                    })
                else:
                    # 正常情况：有优化策略结果，需要匹配实施举措
                    # 去重优化策略
                    unique_strategies = {}
                    for result in results:
                        strategy = result['优化策略']
                        if strategy not in unique_strategies:
                            unique_strategies[strategy] = result[self.measures_list_key]
                    
                    # 检查是否所有举措列表都为空
                    all_empty = all(len(measures) == 0 for measures in unique_strategies.values())
                    
                    if all_empty:
                        # 所有举措列表都为空，返回特定提示信息
                        # 构建图片的JSON结果
                        image_json_result = {
                            "image_name": image_name,
                            "优化策略及实施举措": [{
                                "优化策略": "未识别到具体策略",
                                self.measures_list_key: [],
                                "备注": "街道无需进一步提升，没有相关的实施举措参考"
                            }]
                        }
                        
                        # 构建图片的Markdown结果
                        image_markdown = f"## {image_name}\n\n该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考\n\n"
                        
                        # 生成一行Excel结果
                        excel_results.append({
                            'image_basename': image_name,
                            '优化策略': '; '.join(unique_strategies.keys()),
                            '实施举措': '',
                            '实施举措内涵': '',
                            'markdown结果': '该街道断面优化策略结果分别关联的实施举措如下：街道无需进一步提升，没有相关的实施举措参考'
                        })
                    else:
                        # 正常情况：有非空举措列表
                        # 构建图片的JSON结果
                        image_json_result = {
                            "image_name": image_name,
                            "优化策略及实施举措": []
                        }
                        
                        # 遍历每个优化策略，添加到图片的JSON结果
                        for strategy, measures in unique_strategies.items():
                            image_json_result["优化策略及实施举措"].append({
                                "优化策略": strategy,
                                self.measures_list_key: measures
                            })
                        
                        # 构建图片的Markdown结果
                        image_markdown = f"## {image_name}\n\n"
                        image_markdown += "该街道断面优化策略结果分别关联的实施举措如下：\n\n"
                        
                        # 构建图片的所有优化策略和实施举措（用于Excel）
                        all_strategies = []
                        all_measures = []
                        all_measure_contents = []
                        all_md_contents = []
                        
                        # 按顺序编号优化策略
                        for strategy_idx, (strategy, measures) in enumerate(unique_strategies.items(), 1):
                            all_strategies.append(strategy)
                            all_measures.extend([m['实施举措'] for m in measures])
                            all_measure_contents.extend([m['实施举措内涵'] for m in measures])
                            
                            if measures:
                                # 构建实施举措列表
                                measure_list = []
                                for m_idx, measure in enumerate(measures, 1):
                                    # 根据索引选择对应的中文编号
                                    if m_idx == 1:
                                        number = "①"
                                    elif m_idx == 2:
                                        number = "②"
                                    elif m_idx == 3:
                                        number = "③"
                                    elif m_idx == 4:
                                        number = "④"
                                    elif m_idx == 5:
                                        number = "⑤"
                                    else:
                                        number = f"{m_idx}、"
                                    measure_list.append(f"{number}{measure['实施举措']}，其内涵为{measure['实施举措内涵']}")
                                
                                # 组合成流畅的句子
                                image_markdown += f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n\n"
                                
                                # 构建Excel中的Markdown结果（不包含图片名称）
                                md_content = f"（{strategy_idx}）{strategy}，其对应的实施举措包括：{'; '.join(measure_list)}\n"
                            else:
                                image_markdown += f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n\n"
                                md_content = f"（{strategy_idx}）{strategy}，未找到对应的实施举措\n"
                            all_md_contents.append(md_content)
                        
                        # 生成Excel中的Markdown结果（包含开头语句）
                        excel_md_content = "该街道断面优化策略结果分别关联的实施举措如下：\n\n" + ''.join(all_md_contents)
                        
                        # 生成一行Excel结果
                        excel_results.append({
                            'image_basename': image_name,
                            '优化策略': '; '.join(all_strategies),
                            '实施举措': '; '.join(all_measures),
                            '实施举措内涵': '; '.join(all_measure_contents),
                            'markdown结果': excel_md_content
                        })
                
                # 添加到综合JSON结果
                json_result['image_implementation_measures'].append(image_json_result)
                
                # 添加到综合Markdown结果
                markdown_result += image_markdown
            
            # 创建Excel结果DataFrame
            excel_result_df = pd.DataFrame(excel_results)
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理Excel文件失败：{str(e)}")

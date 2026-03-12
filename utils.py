import json
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

class OptimizationStrategyExtractor:
    """
    优化策略提取工具类
    用于从大模型输出中提取问题归因结果，并匹配对应的优化策略
    """
    
    def __init__(self):
        self.question_cause_key = "问题归因结果"
    
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
            
            # 1. 提取 ```json ``` 包裹的内容
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            else:
                # 2. 尝试提取 ``` ``` 包裹的内容（不指定语言）
                json_pattern = r'```\s*([\s\S]*?)\s*```'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                else:
                    # 3. 尝试提取没有包裹标记的JSON
                    json_pattern = r'\{[\s\S]*\}'
                    match = re.search(json_pattern, response, re.DOTALL)
                    if match:
                        json_str = match.group(0).strip()
                    else:
                        return None
            
            if not json_str:
                return None
            
            # 解析JSON
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试处理单引号格式
            try:
                import ast
                return ast.literal_eval(json_str)
            except (SyntaxError, ValueError, NameError):
                return None
        except Exception:
            return None
    
    def extract_question_causes(self, json_data: Dict[str, Any]) -> List[str]:
        """
        从JSON数据中提取问题归因结果
        :param json_data: 解析后的JSON字典
        :return: 问题归因结果列表
        """
        try:
            # 初始化问题归因结果
            question_causes = []
            
            # 遍历JSON数据，查找"问题归因结果"字段
            def find_question_causes(obj):
                nonlocal question_causes
                if isinstance(obj, dict):
                    if "问题归因结果" in obj:
                        result = obj["问题归因结果"]
                        if isinstance(result, list):
                            question_causes.extend(result)
                        elif isinstance(result, str):
                            # 尝试分割字符串
                            question_causes.extend([cause.strip() for cause in result.split('、') if cause.strip()])
                    else:
                        # 递归查找
                        for value in obj.values():
                            find_question_causes(value)
                elif isinstance(obj, list):
                    for item in obj:
                        find_question_causes(item)
                elif isinstance(obj, str):
                    # 尝试从字符串中提取JSON
                    extracted_json = self.extract_json_from_response(obj)
                    if extracted_json:
                        find_question_causes(extracted_json)
            
            # 开始查找
            find_question_causes(json_data)
            
            # 确保返回的是列表，且每个元素都是字符串
            return [str(cause).strip() for cause in question_causes if str(cause).strip()]
        except Exception:
            return []
    
    def load_strategy_mapping(self, excel_path: str) -> Dict[str, List[Dict[str, str]]]:
        """
        从Excel表格加载问题归因到优化策略的映射
        :param excel_path: Excel文件路径
        :return: 问题归因到优化策略的映射字典
        """
        try:
            df = pd.read_excel(excel_path)
            
            # 检查必要列是否存在
            required_cols = ['问题归因', '优化策略', '优化策略内涵']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Excel表格缺少必要列：{col}")
            
            # 构建映射字典
            strategy_mapping = {}
            
            for _, row in df.iterrows():
                question_cause = str(row['问题归因']).strip()
                optimization_strategy = str(row['优化策略']).strip()
                strategy_content = str(row['优化策略内涵']).strip()
                
                if question_cause not in strategy_mapping:
                    strategy_mapping[question_cause] = []
                
                strategy_mapping[question_cause].append({
                    '优化策略': optimization_strategy,
                    '优化策略内涵': strategy_content
                })
            
            return strategy_mapping
        except Exception as e:
            raise Exception(f"加载Excel表格失败：{str(e)}")
    
    def match_strategies(self, question_causes: List[str], strategy_mapping: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, Any]]:
        """
        根据问题归因结果匹配对应的优化策略
        :param question_causes: 问题归因结果列表
        :param strategy_mapping: 问题归因到优化策略的映射字典
        :return: 匹配后的结果列表
        """
        matched_results = []
        
        # 获取所有的策略键，用于匹配
        strategy_keys = list(strategy_mapping.keys())
        
        for cause in question_causes:
            # 清理问题归因字符串，移除可能的Markdown格式和多余字符
            cleaned_cause = cause.strip()
            if cleaned_cause.startswith('```json'):
                # 提取Markdown中的JSON
                extracted_json = self.extract_json_from_response(cleaned_cause)
                if extracted_json:
                    # 从提取的JSON中获取问题归因结果列表
                    nested_causes = extracted_json.get('问题归因结果', [])
                    if nested_causes and isinstance(nested_causes, list):
                        # 递归处理嵌套的问题归因结果
                        nested_matched = self.match_strategies(nested_causes, strategy_mapping)
                        matched_results.extend(nested_matched)
                        continue
                # 如果无法提取JSON，尝试清理字符串
                cleaned_cause = re.sub(r'```json\s*|[\s\S]*?\{[\s\S]*\}[\s\S]*?```', '', cleaned_cause).strip()
            elif cleaned_cause.startswith('{') and cleaned_cause.endswith('}'):
                # 如果是JSON字符串，尝试解析
                try:
                    json_obj = json.loads(cleaned_cause)
                    nested_causes = json_obj.get('问题归因结果', [])
                    if nested_causes and isinstance(nested_causes, list):
                        # 递归处理嵌套的问题归因结果
                        nested_matched = self.match_strategies(nested_causes, strategy_mapping)
                        matched_results.extend(nested_matched)
                        continue
                except json.JSONDecodeError:
                    pass
            
            if not cleaned_cause:
                continue
            
            # 直接匹配
            if cleaned_cause in strategy_mapping:
                strategies = strategy_mapping[cleaned_cause]
                matched_results.append({
                    '问题归因': cleaned_cause,
                    '优化策略列表': strategies
                })
            else:
                # 尝试模糊匹配，处理可能的空格、标点符号差异
                matched = False
                for key in strategy_keys:
                    # 清理键名，用于比较
                    cleaned_key = key.strip()
                    if cleaned_key == cleaned_cause:
                        strategies = strategy_mapping[key]
                        matched_results.append({
                            '问题归因': cleaned_cause,
                            '优化策略列表': strategies
                        })
                        matched = True
                        break
                if not matched:
                    matched_results.append({
                        '问题归因': cleaned_cause,
                        '优化策略列表': []
                    })
        
        return matched_results
    
    def generate_json_result(self, matched_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成JSON格式的结果
        :param matched_results: 匹配后的结果列表
        :return: JSON格式的结果字典
        """
        return {
            '问题归因及优化策略': matched_results
        }
    
    def generate_markdown_result(self, matched_results: List[Dict[str, Any]]) -> str:
        """
        生成Markdown格式的结果
        :param matched_results: 匹配后的结果列表
        :return: Markdown格式的结果字符串
        """
        md_content = "# 问题归因及优化策略\n\n"
        
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
            
            # 去重问题归因
            unique_causes = {}
            for result in results:
                cause = result['问题归因']
                if cause not in unique_causes:
                    unique_causes[cause] = result['优化策略列表']
            
            # 生成每个问题归因的结果
            for cause, strategies in unique_causes.items():
                md_content += f"### {cause}\n\n"
                
                if strategies:
                    for strategy in strategies:
                        md_content += f"**优化策略**：{strategy['优化策略']}\n"
                        md_content += f"**内涵**：{strategy['优化策略内涵']}\n\n"
                else:
                    md_content += "**未找到对应的优化策略**\n\n"
        
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
        处理文件内容，提取问题归因并匹配优化策略
        :param file_content: 文件内容
        :param excel_path: Excel策略映射文件路径
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            # 步骤1：提取JSON
            json_data = self.extract_json_from_response(file_content)
            if not json_data:
                raise ValueError("无法从文件中提取有效的JSON数据")
            
            # 步骤2：提取问题归因结果
            question_causes = self.extract_question_causes(json_data)
            
            # 步骤3：加载策略映射
            strategy_mapping = self.load_strategy_mapping(excel_path)
            
            # 步骤4：匹配优化策略
            matched_results = self.match_strategies(question_causes, strategy_mapping)
            
            # 步骤5：添加image_name（从JSON数据中提取或使用默认值）
            image_name = json_data.get("image_name", json_data.get("image_basename", "未知图片"))
            for result in matched_results:
                result['image_name'] = image_name
            
            # 步骤6：生成JSON结果（按图片分组，统一格式）
            # 构建图片的JSON结果
            image_json_result = {
                "image_name": image_name,
                "问题归因及优化策略": []
            }
            
            # 去重问题归因
            unique_causes = {}
            for result in matched_results:
                cause = result['问题归因']
                if cause not in unique_causes:
                    unique_causes[cause] = result['优化策略列表']
            
            for cause, strategies in unique_causes.items():
                image_json_result["问题归因及优化策略"].append({
                    "问题归因": cause,
                    "优化策略列表": strategies
                })
            
            # 生成综合JSON结果（统一格式）
            json_result = {
                'image_optimization_strategies': [image_json_result]
            }
            
            # 步骤7：生成Markdown结果（按图片分组）
            markdown_result = f"# 问题归因及优化策略\n\n"
            
            # 构建图片的Markdown结果
            image_markdown = f"## {image_name}\n\n"
            
            # 按顺序编号问题归因
            for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                if strategies:
                    # 构建优化策略列表
                    strategy_list = []
                    for s_idx, strategy in enumerate(strategies, 1):
                        strategy_list.append(f"①{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                    
                    # 组合成流畅的句子
                    image_markdown += f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n\n"
                else:
                    image_markdown += f"（{cause_idx}）{cause}，未找到对应的优化策略\n\n"
            
            # 添加到综合Markdown结果
            markdown_result += image_markdown
            
            # 步骤7：生成Markdown结果（按图片分组）
            # 添加指定的说明文字
            markdown_result = f"# 问题归因及优化策略\n\n"
            
            # 构建图片的Markdown结果
            image_markdown = f"## {image_name}\n\n"
            image_markdown += "该街道断面问题归因结果分别关联的优化策略如下：\n\n"
            
            # 按顺序编号问题归因
            for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                if strategies:
                    # 构建优化策略列表
                    strategy_list = []
                    for s_idx, strategy in enumerate(strategies, 1):
                        # 根据索引选择对应的中文编号
                        if s_idx == 1:
                            number = "①"
                        elif s_idx == 2:
                            number = "②"
                        elif s_idx == 3:
                            number = "③"
                        elif s_idx == 4:
                            number = "④"
                        elif s_idx == 5:
                            number = "⑤"
                        else:
                            number = f"{s_idx}、"
                        strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                    
                    # 组合成流畅的句子
                    image_markdown += f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n\n"
                else:
                    image_markdown += f"（{cause_idx}）{cause}，未找到对应的优化策略\n\n"
            
            # 添加到综合Markdown结果
            markdown_result += image_markdown
            
            # 步骤8：生成Excel结果（每个图片对应一行）
            # 构建图片的所有问题归因和优化策略
            all_causes = []
            all_strategies = []
            all_strategy_contents = []
            all_md_contents = []
            
            # 按顺序编号问题归因
            for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                all_causes.append(cause)
                all_strategies.extend([s['优化策略'] for s in strategies])
                all_strategy_contents.extend([s['优化策略内涵'] for s in strategies])
                
                if strategies:
                    # 构建Excel中的Markdown结果（不包含图片名称）
                            strategy_list = []
                            for s_idx, strategy in enumerate(strategies, 1):
                                # 根据索引选择对应的中文编号
                                if s_idx == 1:
                                    number = "①"
                                elif s_idx == 2:
                                    number = "②"
                                elif s_idx == 3:
                                    number = "③"
                                elif s_idx == 4:
                                    number = "④"
                                elif s_idx == 5:
                                    number = "⑤"
                                else:
                                    number = f"{s_idx}、"
                                strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                            md_content = f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n"
                else:
                    md_content = f"（{cause_idx}）{cause}，未找到对应的优化策略\n"
                all_md_contents.append(md_content)
            
            # 生成Excel中的Markdown结果（包含开头语句）
            excel_md_content = "该街道断面问题归因结果分别关联的优化策略如下：\n\n" + ''.join(all_md_contents)
            
            # 生成一行Excel结果
            excel_result = {
                'image_basename': image_name,
                '问题归因': '; '.join(all_causes),
                '优化策略': '; '.join(all_strategies),
                '优化策略内涵': '; '.join(all_strategy_contents),
                'markdown结果': excel_md_content
            }
            
            excel_result_df = pd.DataFrame([excel_result])
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理文件失败：{str(e)}")
    
    def process_jsonl_file(self, file_path: str, excel_path: str) -> Tuple[Dict[str, Any], str, pd.DataFrame]:
        """
        处理JSONL文件，提取所有问题归因并匹配优化策略
        :param file_path: JSONL文件路径
        :param excel_path: Excel策略映射文件路径
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            # 按图片分组的结果字典
            image_results = {}
            
            # 读取JSONL文件
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # 提取JSON
                        json_data = self.extract_json_from_response(line)
                        if json_data:
                            # 提取问题归因
                            question_causes = self.extract_question_causes(json_data)
                            if question_causes:
                                # 加载策略映射
                                strategy_mapping = self.load_strategy_mapping(excel_path)
                                
                                # 匹配优化策略
                                matched_results = self.match_strategies(question_causes, strategy_mapping)
                                
                                # 添加image_name（从JSON数据中提取或使用默认值）
                                image_name = json_data.get("image_name", json_data.get("image_basename", "未知图片"))
                                for result in matched_results:
                                    result['image_name'] = image_name
                                
                                # 按图片分组保存结果
                                if image_name not in image_results:
                                    image_results[image_name] = []
                                image_results[image_name].extend(matched_results)
            
            if not image_results:
                raise ValueError("未找到有效的问题归因结果")
            
            # 生成综合JSON结果（按图片分组）
            json_result = {
                'image_optimization_strategies': []
            }
            
            # 生成综合Markdown结果
            markdown_result = "# 问题归因及优化策略\n\n"
            
            # 生成Excel结果
            excel_results = []
            
            # 遍历每个图片的结果
            for image_name, results in image_results.items():
                # 去重问题归因
                unique_causes = {}
                for result in results:
                    cause = result['问题归因']
                    if cause not in unique_causes:
                        unique_causes[cause] = result['优化策略列表']
                
                # 构建图片的JSON结果
                image_json_result = {
                    "image_name": image_name,
                    "问题归因及优化策略": []
                }
                
                # 遍历每个问题归因，添加到图片的JSON结果
                for cause, strategies in unique_causes.items():
                    image_json_result["问题归因及优化策略"].append({
                        "问题归因": cause,
                        "优化策略列表": strategies
                    })
                
                # 构建图片的Markdown结果
                image_markdown = f"## {image_name}\n\n"
                image_markdown += "该街道断面问题归因结果分别关联的优化策略如下：\n\n"
                
                # 按顺序编号问题归因
                for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                    if strategies:
                        # 构建优化策略列表
                        strategy_list = []
                        for s_idx, strategy in enumerate(strategies, 1):
                            # 根据索引选择对应的中文编号
                            if s_idx == 1:
                                number = "①"
                            elif s_idx == 2:
                                number = "②"
                            elif s_idx == 3:
                                number = "③"
                            elif s_idx == 4:
                                number = "④"
                            elif s_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{s_idx}、"
                            strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                        
                        # 组合成流畅的句子
                        image_markdown += f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n\n"
                    else:
                        image_markdown += f"（{cause_idx}）{cause}，未找到对应的优化策略\n\n"
                
                # 添加到综合JSON结果
                json_result['image_optimization_strategies'].append(image_json_result)
                
                # 添加到综合Markdown结果
                markdown_result += image_markdown
                
                # 生成Excel结果（每个图片对应一行）
                # 构建图片的所有问题归因和优化策略
                all_causes = []
                all_strategies = []
                all_strategy_contents = []
                all_md_contents = []
                
                # 按顺序编号问题归因
                for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                    all_causes.append(cause)
                    all_strategies.extend([s['优化策略'] for s in strategies])
                    all_strategy_contents.extend([s['优化策略内涵'] for s in strategies])
                    
                    if strategies:
                        # 构建Excel中的Markdown结果（不包含图片名称）
                        strategy_list = []
                        for s_idx, strategy in enumerate(strategies, 1):
                            # 根据索引选择对应的中文编号
                            if s_idx == 1:
                                number = "①"
                            elif s_idx == 2:
                                number = "②"
                            elif s_idx == 3:
                                number = "③"
                            elif s_idx == 4:
                                number = "④"
                            elif s_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{s_idx}、"
                            strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                        md_content = f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n"
                    else:
                        md_content = f"（{cause_idx}）{cause}，未找到对应的优化策略\n"
                    all_md_contents.append(md_content)
                
                # 生成Excel中的Markdown结果（包含开头语句）
                excel_md_content = "该街道断面问题归因结果分别关联的优化策略如下：\n\n" + ''.join(all_md_contents)
                
                # 生成一行Excel结果
                excel_results.append({
                    'image_basename': image_name,
                    '问题归因': '; '.join(all_causes),
                    '优化策略': '; '.join(all_strategies),
                    '优化策略内涵': '; '.join(all_strategy_contents),
                    'markdown结果': excel_md_content
                })
            
            excel_result_df = pd.DataFrame(excel_results)
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理JSONL文件失败：{str(e)}")
    
    def process_excel_file(self, file_content: bytes, excel_path: str, image_basename_col: str, question_causes_col: str) -> Tuple[Dict[str, Any], str, pd.DataFrame]:
        """
        处理Excel文件，提取问题归因结果并匹配优化策略
        :param file_content: Excel文件内容（字节流）
        :param excel_path: Excel策略映射文件路径
        :param image_basename_col: 图片名称列名
        :param question_causes_col: 问题原因列表列名
        :return: 包含JSON结果、Markdown结果和Excel结果的元组
        """
        try:
            import io
            
            # 读取Excel文件
            df = pd.read_excel(io.BytesIO(file_content))
            
            # 检查必要列是否存在
            required_cols = [image_basename_col, question_causes_col]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Excel表格缺少必要列：{col}")
            
            # 按图片分组的结果字典
            image_results = {}
            excel_results = []
            
            # 加载策略映射
            strategy_mapping = self.load_strategy_mapping(excel_path)
            
            # 遍历每一行，提取问题归因结果
            for _, row in df.iterrows():
                # 获取图片名称
                image_basename = str(row[image_basename_col]).strip()
                
                # 获取问题归因结果
                question_causes_str = str(row[question_causes_col]).strip()
                if question_causes_str and question_causes_str != "nan":
                    # 尝试解析为JSON列表
                    question_causes = []
                    try:
                        parsed_causes = json.loads(question_causes_str)
                        if isinstance(parsed_causes, list):
                            question_causes = [str(cause).strip() for cause in parsed_causes if str(cause).strip()]
                        elif isinstance(parsed_causes, str):
                            # 如果解析后是字符串，尝试按分隔符分割
                            question_causes = [cause.strip() for cause in parsed_causes.split('、') if cause.strip()]
                    except (json.JSONDecodeError, ValueError):
                        # 如果JSON解析失败，尝试按分隔符分割
                        question_causes = [cause.strip() for cause in question_causes_str.split('、') if cause.strip()]
                    
                    if question_causes:
                        # 匹配优化策略
                        matched_results = self.match_strategies(question_causes, strategy_mapping)
                        
                        # 添加图片名称到结果中并按图片分组
                        if image_basename not in image_results:
                            image_results[image_basename] = []
                        for result in matched_results:
                            result['image_name'] = image_basename
                            image_results[image_basename].append(result)
            
            if not image_results:
                raise ValueError("未找到有效的问题归因结果")
            
            # 生成综合JSON结果（按图片分组）
            json_result = {
                'image_optimization_strategies': []
            }
            
            # 生成综合Markdown结果
            markdown_result = "# 问题归因及优化策略\n\n"
            
            # 遍历每个图片的结果
            for image_name, results in image_results.items():
                # 去重问题归因
                unique_causes = {}
                for result in results:
                    cause = result['问题归因']
                    if cause not in unique_causes:
                        unique_causes[cause] = result['优化策略列表']
                
                # 构建图片的JSON结果
                image_json_result = {
                    "image_name": image_name,
                    "问题归因及优化策略": []
                }
                
                # 遍历每个问题归因，添加到图片的JSON结果
                for cause, strategies in unique_causes.items():
                    image_json_result["问题归因及优化策略"].append({
                        "问题归因": cause,
                        "优化策略列表": strategies
                    })
                
                # 构建图片的Markdown结果
                image_markdown = f"## {image_name}\n\n"
                image_markdown += "该街道断面问题归因结果分别关联的优化策略如下：\n\n"
                
                # 按顺序编号问题归因
                for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                    if strategies:
                        # 构建优化策略列表
                        strategy_list = []
                        for s_idx, strategy in enumerate(strategies, 1):
                            # 根据索引选择对应的中文编号
                            if s_idx == 1:
                                number = "①"
                            elif s_idx == 2:
                                number = "②"
                            elif s_idx == 3:
                                number = "③"
                            elif s_idx == 4:
                                number = "④"
                            elif s_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{s_idx}、"
                            strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                        
                        # 组合成流畅的句子
                        image_markdown += f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n\n"
                    else:
                        image_markdown += f"（{cause_idx}）{cause}，未找到对应的优化策略\n\n"
                
                # 添加到综合JSON结果
                json_result['image_optimization_strategies'].append(image_json_result)
                
                # 添加到综合Markdown结果
                markdown_result += image_markdown
                
                # 生成Excel结果（每个图片对应一行）
                # 构建图片的所有问题归因和优化策略
                all_causes = []
                all_strategies = []
                all_strategy_contents = []
                all_md_contents = []
                
                # 按顺序编号问题归因
                for cause_idx, (cause, strategies) in enumerate(unique_causes.items(), 1):
                    all_causes.append(cause)
                    all_strategies.extend([s['优化策略'] for s in strategies])
                    all_strategy_contents.extend([s['优化策略内涵'] for s in strategies])
                    
                    if strategies:
                        # 构建Excel中的Markdown结果（不包含图片名称）
                        strategy_list = []
                        for s_idx, strategy in enumerate(strategies, 1):
                            # 根据索引选择对应的中文编号
                            if s_idx == 1:
                                number = "①"
                            elif s_idx == 2:
                                number = "②"
                            elif s_idx == 3:
                                number = "③"
                            elif s_idx == 4:
                                number = "④"
                            elif s_idx == 5:
                                number = "⑤"
                            else:
                                number = f"{s_idx}、"
                            strategy_list.append(f"{number}{strategy['优化策略']}，其内涵为{strategy['优化策略内涵']}")
                        md_content = f"（{cause_idx}）{cause}，其对应的优化策略包括：{'; '.join(strategy_list)}\n"
                    else:
                        md_content = f"（{cause_idx}）{cause}，未找到对应的优化策略\n"
                    all_md_contents.append(md_content)
                
                # 生成Excel中的Markdown结果（包含开头语句）
                excel_md_content = "该街道断面问题归因结果分别关联的优化策略如下：\n\n" + ''.join(all_md_contents)
                
                # 生成一行Excel结果
                excel_results.append({
                    'image_basename': image_name,
                    '问题归因': '; '.join(all_causes),
                    '优化策略': '; '.join(all_strategies),
                    '优化策略内涵': '; '.join(all_strategy_contents),
                    'markdown结果': excel_md_content
                })
            
            # 创建Excel结果DataFrame
            excel_result_df = pd.DataFrame(excel_results)
            
            return json_result, markdown_result, excel_result_df
        except Exception as e:
            raise Exception(f"处理Excel文件失败：{str(e)}")

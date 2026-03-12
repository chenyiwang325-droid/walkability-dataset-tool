import json
import json5
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Union
import os
import streamlit as st

class JSONLProcessor:
    """
    JSONL处理工具类
    用于将JSONL文件转换为JSON文件，并支持进一步转换为Excel和结构化Excel文件
    """
    
    def __init__(self):
        self.PROCESS_STEP = 1
        self.PROCESS_MODE = "optimization"
        self.OUTPUT_DIR = "."
        self.IS_GENERAL_MODE = False
        
        # JSON字段键名配置 - 问题诊断
        self.LEVEL_NAME_KEY = "层级"
        self.STAGE2_KEY = "第二阶段：发现问题结果"
        self.LEVEL_RATING_KEY = "层级评级"
        self.DIMENSION_RATING_LIST_KEY = "维度评级"
        self.DIMENSION_NAME_KEY = "维度名称"
        self.DIMENSION_RATING_KEY = "评级结果"
        self.STAGE3_KEY = "第三阶段：问题归因结果"
        self.STAGE3_KEY_ALT = "第三阶段：问题诊断分析结果"
        self.PROBLEM_CAUSE_KEY = "问题归因"
        self.PROBLEM_ANALYSIS_KEY = "问题归因影响分析"
        self.PROBLEM_ANALYSIS_KEY_ALT = "问题影响分析"
        
        # JSON字段键名配置 - 优化方向
        self.OPTIMIZATION_MACRO_KEY = "宏观外部现实条件"
        self.OPTIMIZATION_MICRO_KEY = "微观优先改进需求"
        self.OPTIMIZATION_STRATEGY_KEY = "优化策略提出"
        
        # 其他配置
        self.MISSING_DIM_VALUE = "未评级"
    
    def set_config(self, process_step: int, process_mode: str, output_dir: str):
        """
        设置配置参数
        :param process_step: 处理步骤
        :param process_mode: 处理模式
        :param output_dir: 输出目录
        """
        self.PROCESS_STEP = process_step
        self.PROCESS_MODE = process_mode
        
        # 确保输出目录基于当前文件所在的项目根目录
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取项目根目录（当前目录的父目录）
        project_root = os.path.dirname(current_dir)
        
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(output_dir):
            self.OUTPUT_DIR = os.path.join(project_root, output_dir)
        else:
            self.OUTPUT_DIR = output_dir
        
        self.IS_GENERAL_MODE = process_mode == "general"
    
    def jsonl_to_json(self, input_path: str, output_path: str, show_progress: bool = True) -> None:
        """
        将JSONL文件转换为JSON文件
        :param input_path: 输入JSONL文件路径
        :param output_path: 输出JSON文件路径
        :param show_progress: 是否显示进度条
        """
        data = []
        
        # 处理多行JSON块和不完整的JSON包装器
        current_json_block = []
        in_json_block = False
        
        # 初始化进度条，只在需要时读取文件计算总行数
        progress_bar = None
        total_lines = 0
        update_interval = 100  # 每处理100行更新一次进度条
        
        if show_progress:
            # 计算总行数，用于进度条
            with open(input_path, 'r', encoding='utf-8') as f:
                for _ in f:
                    total_lines += 1
            progress_bar = st.progress(0.0, text="正在处理JSONL文件...")
        
        # 一次打开文件处理，避免重复读取
        with open(input_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    # 只在更新间隔或最后一行更新进度条
                    if show_progress and progress_bar and ((idx + 1) % update_interval == 0 or idx + 1 == total_lines):
                        progress = (idx + 1) / total_lines
                        progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_lines} 行...")
                    continue
                
                # 处理JSON包装器的开始
                if line.startswith('```json') or line.startswith('```'):
                    in_json_block = True
                    # 提取行中可能的JSON内容，处理完整和不完整的包装器
                    json_content = line[line.index('```')+3:].strip()
                    # 移除可能的json标记
                    if json_content.startswith('json'):
                        json_content = json_content[4:].strip()
                    if json_content:
                        current_json_block.append(json_content)
                    # 只在更新间隔或最后一行更新进度条
                    if show_progress and progress_bar and ((idx + 1) % update_interval == 0 or idx + 1 == total_lines):
                        progress = (idx + 1) / total_lines
                        progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_lines} 行...")
                    continue
                
                # 处理JSON包装器的结束
                if line.endswith('```'):
                    in_json_block = False
                    # 提取行中可能的JSON内容
                    json_content = line[:-3].strip()
                    if json_content:
                        current_json_block.append(json_content)
                    # 处理当前JSON块
                    if current_json_block:
                        json_str = ' '.join(current_json_block)
                        self._process_json_line(json_str, data)
                        current_json_block = []
                    # 只在更新间隔或最后一行更新进度条
                    if show_progress and progress_bar and ((idx + 1) % update_interval == 0 or idx + 1 == total_lines):
                        progress = (idx + 1) / total_lines
                        progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_lines} 行...")
                    continue
                
                # 如果在JSON块中，收集行内容
                if in_json_block:
                    current_json_block.append(line)
                else:
                    # 处理单行JSON
                    self._process_json_line(line, data)
                
                # 只在更新间隔或最后一行更新进度条
                if show_progress and progress_bar and ((idx + 1) % update_interval == 0 or idx + 1 == total_lines):
                    progress = (idx + 1) / total_lines
                    progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_lines} 行...")
        
        # 处理文件结束时可能剩余的JSON块
        if current_json_block:
            json_str = ' '.join(current_json_block)
            self._process_json_line(json_str, data)
            current_json_block = []
        
        # 定义获取图片basename的函数
        def get_image_basename(item):
            if isinstance(item, dict):
                if "image_basename" in item:
                    return item["image_basename"]
                elif "image_name" in item:
                    return item["image_name"]
                elif "images" in item and isinstance(item["images"], list) and item["images"]:
                    img = item["images"][0]
                    if isinstance(img, dict) and "path" in img:
                        return Path(img["path"]).name
            return ""
        
        # 确保图片名称按照自然数顺序排序
        def extract_number_sort_key(item):
            img_name = get_image_basename(item)
            # 提取所有数字
            numbers = re.findall(r'\d+', img_name)
            # 如果有数字，将第一个数字转换为整数作为排序键
            if numbers:
                return int(numbers[0])
            # 否则使用字符串本身作为排序键
            return img_name
        
        # 按照图片名称中的数字进行自然数排序
        data_sorted = sorted(
            data,
            key=extract_number_sort_key
        )
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_sorted, f, ensure_ascii=False, indent=2)
    
    def _process_json_line(self, json_str: str, data: List[Dict]) -> None:
        """
        处理单行或多行JSON字符串，尝试解析并添加到数据列表中
        :param json_str: JSON字符串
        :param data: 数据列表
        """
        if not json_str:
            return
        
        # 尝试多种方法解析JSON，优先使用性能更好的标准json库
        # 1. 首先尝试使用标准json库解析（性能最好）
        try:
            parsed_json = json.loads(json_str)
            data.append(parsed_json)
            return
        except json.JSONDecodeError:
            # 标准json解析失败，才使用json5进行修正（性能较差）
            try:
                parsed_json = json5.loads(json_str)
                data.append(parsed_json)
                return
            except Exception:
                pass
        except Exception:
            pass
        
        # 2. 尝试从字符串中提取JSON对象
        try:
            # 匹配JSON对象或数组，使用非贪婪匹配优化性能
            json_pattern = r'(\{[\s\S]*?\}|\[[\s\S]*?\])'
            matches = re.findall(json_pattern, json_str, re.DOTALL)
            for match in matches:
                try:
                    # 首先尝试使用标准json库
                    parsed_json = json.loads(match)
                    data.append(parsed_json)
                except json.JSONDecodeError:
                    # 标准json解析失败，才使用json5
                    try:
                        parsed_json = json5.loads(match)
                        data.append(parsed_json)
                    except Exception:
                        continue
            return
        except Exception:
            pass
        
        # 3. 尝试处理可能包含多个JSON对象的情况
        try:
            # 移除可能的多余字符
            cleaned_json = json_str.strip()
            if cleaned_json and (cleaned_json.startswith('{') or cleaned_json.startswith('[')):
                try:
                    # 首先尝试使用标准json库
                    parsed_json = json.loads(cleaned_json)
                    data.append(parsed_json)
                except json.JSONDecodeError:
                    # 标准json解析失败，才使用json5
                    try:
                        parsed_json = json5.loads(cleaned_json)
                        data.append(parsed_json)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def natural_sort_key(self, s: str) -> List:
        """
        生成自然排序键
        :param s: 字符串
        :return: 排序键列表
        """
        return [int(text) if text.isdigit() else text.lower() for text in re.split('(\\d+)', s)]
    
    def flatten_nested_data(self, data_item: Dict) -> Dict:
        """
        扁平化嵌套数据
        :param data_item: 嵌套数据项
        :return: 扁平化后的数据项
        """
        # 1. 处理images获取basename
        image_basename = ""
        # 优先使用顶层的image_basename字段
        if "image_basename" in data_item:
            image_basename = data_item["image_basename"]
        elif "image_name" in data_item:
            image_basename = data_item["image_name"]
        else:
            # 从images.path中提取basename
            images = data_item.get("images", [])
            if isinstance(images, list) and len(images) > 0 and "path" in images[0]:
                image_path = images[0].get("path", "")
                image_basename = Path(image_path).name

        # 2. 提取顶层非嵌套字段
        base_data = {
            "image_basename": image_basename,
            "response": data_item.get("response", ""),
            "labels": data_item.get("labels", "") if data_item.get("labels") is not None else "",
            "logprobs": data_item.get("logprobs", "") if data_item.get("logprobs") is not None else ""
        }

        # 3. 处理嵌套的messages数组
        messages = data_item.get("messages", [])
        if isinstance(messages, list) and len(messages) > 0:
            for idx, msg in enumerate(messages):
                base_data[f"messages_{idx}_role"] = msg.get("role", "")
                base_data[f"messages_{idx}_content"] = msg.get("content", "")
        else:
            base_data["messages_0_role"] = ""
            base_data["messages_0_content"] = ""

        # 4. 处理嵌套的images数组
        images = data_item.get("images", [])
        if isinstance(images, list) and len(images) > 0:
            for idx, img in enumerate(images):
                base_data[f"images_{idx}_bytes"] = img.get("bytes", "") if img.get("bytes") is not None else ""
                base_data[f"images_{idx}_path"] = img.get("path", "")
        else:
            base_data["images_0_bytes"] = ""
            base_data["images_0_path"] = ""

        return base_data
    
    def json_to_excel(self, json_file_path: str, excel_output_path: str, show_progress: bool = True) -> None:
        """
        将JSON文件转换为Excel文件
        :param json_file_path: 输入JSON文件路径
        :param excel_output_path: 输出Excel文件路径
        :param show_progress: 是否显示进度条
        """
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        
        if not isinstance(json_data, list):
            raise ValueError("JSON文件顶层必须是数组结构（[]）")
        
        # 初始化进度条
        progress_bar = None
        update_interval = 100  # 每处理100项更新一次进度条
        total_items = len(json_data)
        
        if show_progress:
            progress_bar = st.progress(0.0, text="正在转换为Excel文件...")
        
        # 使用列表推导式代替for循环，提高性能
        flattened_data = [self.flatten_nested_data(item) for item in json_data]
        
        # 更新进度条，只在处理完成后更新一次
        if show_progress and progress_bar:
            progress_bar.progress(1.0, text=f"正在转换为Excel文件...")
        
        # 确保image_basename是字符串，并提取数字进行排序
        def extract_number_sort_key(item):
            image_basename = str(item.get("image_basename", ""))
            # 提取所有数字
            numbers = re.findall(r'\d+', image_basename)
            # 如果有数字，将第一个数字转换为整数作为排序键
            if numbers:
                return int(numbers[0])
            # 否则使用字符串本身作为排序键
            return image_basename
        
        # 使用提取的数字进行排序
        flattened_data_sorted = sorted(
            flattened_data,
            key=extract_number_sort_key
        )
        
        df = pd.DataFrame(flattened_data_sorted)
        columns = ["image_basename"] + [col for col in df.columns if col != "image_basename"]
        df = df[columns]
        
        df.to_excel(excel_output_path, index=False, engine="openpyxl")
    
    def parse_single_row(self, json_str, image_name: str) -> Dict:
        """
        解析单行数据
        :param json_str: JSON字符串
        :param image_name: 图片名称
        :return: 解析后的数据
        """
        if self.PROCESS_MODE == "diagnosis":
            result_dict = {
                "图片名称": image_name,
                "层级名称": "未知层级",
                "层级评级结果": "未评级",
                "问题归因": "无",
                "问题归因影响分析": "无",
                "问题归因列表": "无"
            }
        else:
            result_dict = {
                "图片名称": image_name,
                "层级名称": "未知层级",
                "宏观外部现实条件": "无",
                "微观优先改进需求": "无",
                "优化策略提出": "无",
                "优化策略列表": "无"
            }
        
        dim_rating_dict = {}
        raw_json = {}
        
        try:
            # 统一处理所有类型的json_str
            if pd.isna(json_str):
                raw_json = {}
            else:
                # 转换为字符串处理
                if not isinstance(json_str, str):
                    json_str = str(json_str)
                
                original_json = json_str.strip()
                
                if original_json:
                    # 尝试使用修复函数修复JSON
                    raw_json = self._fix_json(original_json)
                    
                    # 如果修复失败，尝试标准解析流程
                    if not raw_json:
                        # 处理Markdown格式的JSON，包括不完整的包裹
                        # 1. 查找并移除开头的 ```json 或 ``` 标记
                        start_match = re.search(r'```(?:json)?\s*', original_json)
                        if start_match:
                            json_str = original_json[start_match.end():].strip()
                        else:
                            json_str = original_json
                        
                        # 2. 查找并移除结尾的 ``` 标记
                        end_match = re.search(r'\s*```$', json_str)
                        if end_match:
                            json_str = json_str[:end_match.start()].strip()
                        
                        # 3. 首先尝试使用标准json库解析
                        try:
                            raw_json = json.loads(json_str)
                        except json.JSONDecodeError:
                            # 标准解析失败，才使用json5进行修正
                            try:
                                raw_json = json5.loads(json_str)
                            except Exception:
                                # 尝试使用ast.literal_eval解析
                                try:
                                    import ast
                                    raw_json = ast.literal_eval(json_str)
                                except (SyntaxError, ValueError):
                                    # 尝试提取JSON对象
                                    try:
                                        # 匹配JSON对象或数组
                                        json_pattern = r'(\{[\s\S]*?\}|\[[\s\S]*?\])'
                                        matches = re.findall(json_pattern, json_str, re.DOTALL)
                                        if matches:
                                            # 尝试解析每个匹配的JSON
                                            for match in matches:
                                                try:
                                                    raw_json = json5.loads(match)
                                                    break
                                                except Exception:
                                                    continue
                                        else:
                                            # 如果没有匹配成功，使用空字典
                                            raw_json = {}
                                    except Exception:
                                        raw_json = {}
        
        except Exception as e:
            error_info = f"解析错误：{str(e)}"
            if self.PROCESS_MODE == "diagnosis":
                result_dict["层级名称"] = error_info
                result_dict["层级评级结果"] = error_info
                result_dict["问题归因"] = error_info
                result_dict["问题归因影响分析"] = error_info
            else:
                result_dict["层级名称"] = error_info
                result_dict["宏观外部现实条件"] = error_info
                result_dict["微观优先改进需求"] = error_info
                result_dict["优化策略提出"] = error_info
        
        # 根据处理模式填充结果
        if self.PROCESS_MODE == "diagnosis":
            result_dict["层级名称"] = raw_json.get(self.LEVEL_NAME_KEY, "未知层级")
            result_dict["层级评级结果"] = raw_json.get(self.STAGE2_KEY, {}).get(self.LEVEL_RATING_KEY, "未评级")
            stage3_data = raw_json.get(self.STAGE3_KEY, raw_json.get(self.STAGE3_KEY_ALT, {}))
            result_dict["问题归因"] = stage3_data.get(self.PROBLEM_CAUSE_KEY, "无")
            result_dict["问题归因影响分析"] = stage3_data.get(self.PROBLEM_ANALYSIS_KEY, 
                                                          stage3_data.get(self.PROBLEM_ANALYSIS_KEY_ALT, "无"))
            # 添加问题归因列表支持，将列表转换为逗号分隔的字符串
            problem_cause_list = raw_json.get("问题归因列表", "无")
            if isinstance(problem_cause_list, list):
                result_dict["问题归因列表"] = ', '.join(str(item) for item in problem_cause_list)
            else:
                result_dict["问题归因列表"] = problem_cause_list
            
            dimension_list = raw_json.get(self.STAGE2_KEY, {}).get(self.DIMENSION_RATING_LIST_KEY, [])
            for dim in dimension_list:
                dim_name = dim.get(self.DIMENSION_NAME_KEY, "未知维度")
                dim_rating = dim.get(self.DIMENSION_RATING_KEY, self.MISSING_DIM_VALUE)
                dim_rating_dict[dim_name] = dim_rating
        else:
            result_dict["层级名称"] = raw_json.get(self.LEVEL_NAME_KEY, "未知层级")
            result_dict["宏观外部现实条件"] = raw_json.get(self.OPTIMIZATION_MACRO_KEY, "无")
            result_dict["微观优先改进需求"] = raw_json.get(self.OPTIMIZATION_MICRO_KEY, "无")
            result_dict["优化策略提出"] = raw_json.get(self.OPTIMIZATION_STRATEGY_KEY, "无")
            # 添加优化策略列表支持，将列表转换为逗号分隔的字符串
            optimization_strategy_list = raw_json.get("优化策略列表", "无")
            if isinstance(optimization_strategy_list, list):
                result_dict["优化策略列表"] = ', '.join(str(item) for item in optimization_strategy_list)
            else:
                result_dict["优化策略列表"] = optimization_strategy_list
        
        result_dict.update(dim_rating_dict)
        return result_dict
    
    def _fix_json(self, json_str: str) -> Optional[Dict]:
        """
        修复JSON字符串中的常见错误，特别是"问题归因列表"错误地包含在"问题归因影响分析"字段值中的情况
        :param json_str: JSON字符串
        :return: 修复后的JSON对象，如果无法修复返回None
        """
        try:
            # 保存原始字符串用于调试
            original_json = json_str
            
            # 修复1：移除可能的Markdown格式
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            # 修复2：将中文引号替换为英文引号
            json_str = json_str.replace('“', '"').replace('”', '"')
            
            # 首先尝试正常解析
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                # 解析失败，尝试使用json5
                try:
                    result = json5.loads(json_str)
                    return result
                except Exception as e:
                    # json5也失败，尝试特殊处理
                    pass
            
            # 检查是否包含"问题归因列表"，如果包含则进行特殊处理
            if '问题归因列表' in json_str:
                # 这是用户提到的特殊情况，需要专门处理
                repair_success = False
                repair_reason = ""
                original_json_str = json_str
                result = None
                
                try:
                    # 1. 修复Markdown格式，但保留原始内容中的中文符号
                    fixed_json_str = json_str
                    if fixed_json_str.startswith('```json'):
                        fixed_json_str = fixed_json_str[7:]
                        repair_reason += "移除了开头的```json标记；"
                    if fixed_json_str.startswith('```'):
                        fixed_json_str = fixed_json_str[3:]
                        repair_reason += "移除了开头的```标记；"
                    if fixed_json_str.endswith('```'):
                        fixed_json_str = fixed_json_str[:-3]
                        repair_reason += "移除了结尾的```标记；"
                    fixed_json_str = fixed_json_str.strip()
                    
                    # 2. 核心修复：修复"问题归因列表"错误嵌入的情况
                    # 处理多种情况：
                    # 情况1："问题归因影响分析": "...问题归因列表: [...]"
                    # 情况2："问题归因影响分析": "...问题归因列表": ["..."]  (没有闭合引号)
                    # 情况3："问题归因影响分析": "..."问题归因列表": ["..."]  (多余引号)
                    
                    # 重点处理用户提供的特殊情况
                    special_pattern = r'"问题归因影响分析"\s*[:：]\s*"(.*?)"?\s*"?问题归因列表"?\s*[:：]\s*\[(.*?)\]'
                    special_match = re.search(special_pattern, fixed_json_str, re.DOTALL)
                    
                    if special_match:
                        # 提取各个部分
                        impact_prefix = special_match.group(1)
                        list_content = special_match.group(2)
                        
                        # 构建修复后的JSON片段，保留原始内容中的中文符号
                        fixed_segment = f'"问题归因影响分析": "{impact_prefix}", "问题归因列表": [{list_content}]'
                        
                        # 替换原有的错误片段
                        fixed_json_str = re.sub(special_pattern, fixed_segment, fixed_json_str, count=1, flags=re.DOTALL)
                        repair_reason += "修复了问题归因列表错误嵌入问题归因影响分析的情况；"
                    else:
                        # 尝试其他修复模式
                        fix_pattern = r'"问题归因影响分析"\s*:\s*"(.*?)问题归因列表\s*[:：]\s*\[(.*?)\]'
                        match = re.search(fix_pattern, fixed_json_str, re.DOTALL)
                        
                        if match:
                            # 提取各个部分
                            impact_prefix = match.group(1)
                            list_content = match.group(2)
                            
                            # 构建修复后的JSON片段，保留原始内容中的中文符号
                            fixed_segment = f'"问题归因影响分析": "{impact_prefix}", "问题归因列表": [{list_content}]'
                            
                            # 替换原有的错误片段
                            fixed_json_str = re.sub(fix_pattern, fixed_segment, fixed_json_str, count=1, flags=re.DOTALL)
                            repair_reason += "修复了问题归因列表错误嵌入问题归因影响分析的情况；"
                    
                    # 3. 尝试解析修复后的完整JSON，确保修复后的JSON被完整解析
                    # 首先尝试标准json库
                    try:
                        result = json.loads(fixed_json_str)
                        repair_success = True
                        print(f"JSON修复成功：{repair_reason}")
                    except json.JSONDecodeError:
                        # 尝试使用json5，保留原始内容中的中文符号
                        try:
                            result = json5.loads(fixed_json_str)
                            repair_success = True
                            print(f"JSON修复成功（使用json5）：{repair_reason}")
                        except Exception as e:
                            repair_reason += f"json解析失败，尝试手动构建完整JSON；"
                            print(f"JSON解析失败，尝试手动构建完整JSON：{e}")
                            
                            # 4. 手动构建完整JSON，确保包含所有阶段
                            # 提取层级
                            level_pattern = r'"层级"\s*:\s*"(.*?)"'
                            level_match = re.search(level_pattern, fixed_json_str)
                            level = level_match.group(1) if level_match else ""
                            
                            # 提取第一阶段
                            stage1 = {}
                            stage1_pattern = r'"第一阶段：要素识别结果"\s*:\s*(\{[\s\S]*?\})'
                            stage1_match = re.search(stage1_pattern, fixed_json_str, re.DOTALL)
                            if stage1_match:
                                try:
                                    stage1 = json5.loads(stage1_match.group(1))
                                    repair_reason += "提取了第一阶段内容；"
                                except Exception:
                                    stage1 = {}
                            
                            # 提取第二阶段
                            stage2 = {}
                            stage2_pattern = r'"第二阶段：发现问题结果"\s*:\s*(\{[\s\S]*?\})'
                            stage2_match = re.search(stage2_pattern, fixed_json_str, re.DOTALL)
                            if stage2_match:
                                try:
                                    stage2 = json5.loads(stage2_match.group(1))
                                    repair_reason += "提取了第二阶段内容；"
                                except Exception:
                                    stage2 = {}
                            
                            # 提取问题归因
                            cause_pattern = r'"问题归因"\s*[:：]\s*"(.*?)"'
                            cause_match = re.search(cause_pattern, fixed_json_str)
                            cause = cause_match.group(1) if cause_match else ""
                            
                            # 提取问题归因影响分析
                            impact = ""
                            impact_pattern = r'"问题归因影响分析"\s*[:：]\s*"(.*?)"'
                            impact_match = re.search(impact_pattern, fixed_json_str, re.DOTALL)
                            if impact_match:
                                impact = impact_match.group(1)
                            else:
                                # 尝试另一种模式（没有闭合引号）
                                impact_pattern2 = r'"问题归因影响分析"\s*[:：]\s*"(.*?)问题归因列表'
                                impact_match2 = re.search(impact_pattern2, fixed_json_str, re.DOTALL)
                                if impact_match2:
                                    impact = impact_match2.group(1).strip()
                            
                            # 提取问题归因列表
                            list_pattern = r'问题归因列表\s*[:：]\s*\[(.*?)\]'
                            list_match = re.search(list_pattern, fixed_json_str, re.DOTALL)
                            list_content = list_match.group(1).strip() if list_match else ""
                            
                            # 处理问题归因列表，只修复必要的格式错误
                            problem_list = []
                            if list_content:
                                # 清理字符串，但保留原始内容中的中文符号
                                list_content = re.sub(r'\s+', ' ', list_content)
                                # 只修复明显的引号问题
                                if list_content.count('"') % 2 != 0:
                                    # 奇数个引号，尝试修复
                                    list_content = list_content.replace('""', '"')
                                    repair_reason += "修复了问题归因列表中的引号问题；"
                                
                                # 分割列表项，只在引号外分割
                                items = re.split(r',(?![^\"]*\")', list_content)
                                # 处理每个项，保留原始内容中的中文符号
                                problem_list = [item.strip('" ').strip("' ") for item in items if item.strip()]
                            
                            # 构建完整的修复JSON，确保包含所有阶段
                            result = {
                                "层级": level,
                                "第一阶段：要素识别结果": stage1,
                                "第二阶段：发现问题结果": stage2,
                                "第三阶段：问题归因结果": {
                                    "问题归因": cause,
                                    "问题归因影响分析": impact,
                                    "问题归因列表": problem_list
                                }
                            }
                            repair_success = True
                            print(f"JSON手动构建成功：{repair_reason}")
                    
                    # 确保结果不为空
                    if result is None:
                        repair_reason += "所有修复尝试都失败；"
                        print(f"JSON修复失败：{repair_reason}")
                        return {
                            "第三阶段：问题归因结果": {
                                "问题归因列表": []
                            }
                        }
                    
                    # 5. 确保问题归因列表是列表类型
                    third_stage = result.get("第三阶段：问题归因结果", {})
                    if third_stage and "问题归因列表" in third_stage:
                        list_content = third_stage["问题归因列表"]
                        # 如果是字符串，转换为列表
                        if isinstance(list_content, str):
                            # 清理字符串
                            list_content = list_content.strip()
                            if list_content.startswith('[') and list_content.endswith(']'):
                                # 移除首尾括号
                                list_content = list_content[1:-1]
                                # 分割列表项
                                items = re.split(r',(?![^\"]*\")', list_content)
                                # 处理每个项
                                third_stage["问题归因列表"] = [item.strip('" ').strip("' ") for item in items if item.strip()]
                                repair_reason += "将问题归因列表字符串转换为列表；"
                            else:
                                # 直接作为单个项
                                third_stage["问题归因列表"] = [list_content.strip('" ').strip("' ")]
                                repair_reason += "将问题归因列表字符串转换为列表；"
                        elif not isinstance(list_content, list):
                            # 其他类型转换为列表
                            third_stage["问题归因列表"] = [str(list_content)]
                            repair_reason += "将问题归因列表非列表类型转换为列表；"
                    elif third_stage:
                        # 如果没有问题归因列表，添加空列表
                        third_stage["问题归因列表"] = []
                        repair_reason += "添加了空的问题归因列表；"
                    
                    return result
                except Exception as e:
                    repair_reason += f"修复过程中发生异常：{str(e)}"
                    print(f"JSON修复失败：{repair_reason}")
                    # 最终后备方案：返回包含基本结构的JSON
                    return {
                        "第三阶段：问题归因结果": {
                            "问题归因列表": []
                        }
                    }
                finally:
                    if not repair_success:
                        print(f"JSON修复失败：{repair_reason}")
                    else:
                        print(f"JSON修复成功：{repair_reason}")
            
            # 尝试其他修复方法
            # 修复3：处理没有闭合的字符串
            if json_str.count('"') % 2 != 0:
                # 找到所有引号位置
                quote_positions = [i for i, char in enumerate(json_str) if char == '"']
                if quote_positions:
                    # 找到最后一个引号位置
                    last_quote_pos = quote_positions[-1]
                    # 在字符串末尾添加引号
                    fixed_json = json_str[:last_quote_pos+1] + json_str[last_quote_pos+1:].rstrip() + '"'
                    # 尝试解析
                    try:
                        result = json.loads(fixed_json)
                        return result
                    except json.JSONDecodeError:
                        try:
                            result = json5.loads(fixed_json)
                            return result
                        except Exception:
                            pass
            
            # 修复4：处理没有闭合的JSON对象
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            if open_braces > close_braces:
                fixed_json = json_str + '}' * (open_braces - close_braces)
                try:
                    result = json.loads(fixed_json)
                    return result
                except json.JSONDecodeError:
                    try:
                        result = json5.loads(fixed_json)
                        return result
                    except Exception:
                        pass
            
            # 最后尝试：手动构建JSON对象
            # 提取所有可能的字段，构建一个基本的JSON对象
            fixed_json = {}
            
            # 提取"层级"字段
            level_pattern = r'"层级"\s*:\s*"(.*?)"'
            level_match = re.search(level_pattern, json_str)
            if level_match:
                fixed_json["层级"] = level_match.group(1)
            
            # 提取"问题归因列表"并添加到固定位置
            if '问题归因列表' in json_str:
                list_pattern = r'问题归因列表\s*:\s*\[(.*?)\]'
                list_match = re.search(list_pattern, json_str, re.DOTALL)
                if list_match:
                    list_content = list_match.group(1).strip()
                    list_content = list_content.replace('“', '"').replace('”', '"')
                    fixed_json["第三阶段：问题归因结果"] = {
                        "问题归因列表": [item.strip('"') for item in list_content.split(',') if item.strip()]
                    }
            
            return fixed_json
            
            # 所有修复都失败，返回None
            return None
        except Exception as e:
            # 如果修复过程中出现异常，返回None
            return None
    
    def extract_and_flatten_json(self, json_str: str, image_name: str) -> Dict:
        """
        提取JSON内容并扁平化，支持直接JSON和Markdown包裹的JSON
        :param json_str: JSON字符串
        :param image_name: 图片名称
        :return: 扁平化后的数据
        """
        # 初始化结果字典
        result = {"图片名称": image_name}
        
        # 尝试从字符串中提取JSON
        extracted_json = None
        original_json_str = json_str  # 保存原始字符串，用于后续修复
        
        # 1. 尝试处理Markdown格式的JSON，包括不完整的包裹
        if isinstance(json_str, str):
            # 首先尝试处理完整的Markdown JSON包装
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            matches = re.findall(json_pattern, json_str, re.DOTALL)
            
            # 处理不完整的Markdown JSON包装（只有开头没有结尾）
            if not matches:
                # 查找 ```json 或 ``` 开头的标记
                start_match = re.search(r'```(?:json)?\s*', json_str)
                if start_match:
                    # 从标记后开始提取所有内容作为可能的JSON
                    json_content = json_str[start_match.end():].strip()
                    matches = [json_content] if json_content else []
            
            if matches:
                # 选择最后一个匹配的JSON代码块（结果通常在最后）
                for json_content in reversed(matches):
                    json_content = json_content.strip()
                    if json_content:
                        # 首先尝试使用标准json库解析
                        try:
                            extracted_json = json.loads(json_content)
                            if extracted_json:
                                break
                        except json.JSONDecodeError:
                            # 标准解析失败，才使用json5进行修正
                            try:
                                extracted_json = json5.loads(json_content)
                                if extracted_json:
                                    break
                            except Exception:
                                # 尝试使用修复函数
                                fixed_json = self._fix_json(json_content)
                                if fixed_json:
                                    extracted_json = fixed_json
                                    break
            
        # 2. 尝试直接解析JSON
        if not extracted_json:
            try:
                if isinstance(json_str, str):
                    # 首先尝试使用标准json库解析
                    try:
                        extracted_json = json.loads(json_str)
                    except json.JSONDecodeError:
                        # 标准解析失败，才使用json5进行修正
                        try:
                            extracted_json = json5.loads(json_str)
                        except Exception:
                            # 尝试使用修复函数
                            fixed_json = self._fix_json(json_str)
                            if fixed_json:
                                extracted_json = fixed_json
                elif isinstance(json_str, dict):
                    extracted_json = json_str
            except Exception:
                # 尝试提取JSON对象或数组
                try:
                    # 匹配JSON对象或数组
                    json_pattern = r'(\{[\s\S]*?\}|\[[\s\S]*?\])'
                    match = re.search(json_pattern, json_str, re.DOTALL)
                    if match:
                        json_content = match.group(0)
                        # 首先尝试使用标准json库解析
                        try:
                            extracted_json = json.loads(json_content)
                        except json.JSONDecodeError:
                            # 标准解析失败，才使用json5进行修正
                            try:
                                extracted_json = json5.loads(json_content)
                            except Exception:
                                # 尝试使用修复函数
                                fixed_json = self._fix_json(json_content)
                                if fixed_json:
                                    extracted_json = fixed_json
                except Exception:
                    pass
        
        # 3. 如果仍然没有提取到JSON，尝试更强大的修复
        if not extracted_json and isinstance(original_json_str, str):
            # 尝试使用修复函数修复整个字符串
            fixed_json = self._fix_json(original_json_str)
            if fixed_json:
                extracted_json = fixed_json
        
        # 4. 如果还是无法提取，记录错误
        if not extracted_json:
            # 记录错误信息
            result["_json_parse_error"] = "无法解析JSON内容，可能存在格式错误"
            return result
        
        # 5. 扁平化JSON结构
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    # 检查列表中的元素是否都是简单类型（非字典）
                    if all(not isinstance(item, dict) for item in v):
                        # 如果都是简单类型，将列表转换为逗号分隔的字符串
                        list_str = ', '.join(str(item) for item in v)
                        items.append((new_key, list_str))
                    else:
                        # 如果包含字典，则按原方式处理
                        for i, item in enumerate(v):
                            list_key = f"{new_key}{sep}{i}"
                            if isinstance(item, dict):
                                items.extend(flatten_dict(item, list_key, sep=sep).items())
                            else:
                                items.append((list_key, item))
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flattened = flatten_dict(extracted_json)
        result.update(flattened)
        return result
    
    def extract_structured_data(self, excel_path: str, output_excel_path: str, show_progress: bool = True) -> None:
        """
        从Excel文件中提取结构化数据
        :param excel_path: 输入Excel文件路径
        :param output_excel_path: 输出Excel文件路径
        :param show_progress: 是否显示进度条
        """
        df_input = pd.read_excel(excel_path, sheet_name="Sheet1")
        
        required_cols = ["image_basename", "response"]
        missing_cols = [col for col in required_cols if col not in df_input.columns]
        if missing_cols:
            raise ValueError(f"输入Excel缺少必要列 - {', '.join(missing_cols)}")
        
        # 初始化进度条
        progress_bar = None
        if show_progress:
            progress_bar = st.progress(0.0, text="正在提取结构化数据...")
            total_rows = len(df_input)
        
        if self.IS_GENERAL_MODE:
            # 通用模式：自动提取JSON内容并扁平化
            all_data = []
            all_columns = set()
            
            for idx, row in df_input.iterrows():
                image_name = row["image_basename"] if not pd.isna(row["image_basename"]) else "未知图片名称"
                json_str = row["response"]
                
                # 提取并扁平化JSON
                single_data = self.extract_and_flatten_json(json_str, image_name)
                all_data.append(single_data)
                
                # 收集所有列名
                all_columns.update(single_data.keys())
                
                # 更新进度条
                if show_progress and progress_bar:
                    progress = (idx + 1) / total_rows
                    progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_rows} 行...")
            
            # 按图片名称中的数字进行自然数排序
            def extract_number_sort_key(item):
                img_name = item["图片名称"]
                # 提取所有数字
                numbers = re.findall(r'\d+', img_name)
                # 如果有数字，将第一个数字转换为整数作为排序键
                if numbers:
                    return int(numbers[0])
                # 否则使用字符串本身作为排序键
                return img_name
            
            all_data_sorted = sorted(
                all_data,
                key=extract_number_sort_key
            )
            
            # 生成输出列顺序
            output_cols = ["图片名称"] + sorted(list(all_columns - {"图片名称"}))
            
            # 生成输出数据
            output_data = []
            for data in all_data_sorted:
                row = {}
                for col in output_cols:
                    row[col] = data.get(col, "")
                output_data.append(row)
        else:
            # 原有模式：诊断或优化策略
            if self.PROCESS_MODE == "diagnosis":
                base_cols = {"图片名称", "层级名称", "层级评级结果", "问题归因", "问题归因影响分析", "问题归因列表"}
                base_cols_order = ["图片名称", "层级名称", "层级评级结果", "问题归因", "问题归因影响分析", "问题归因列表"]
            else:
                base_cols = {"图片名称", "层级名称", "宏观外部现实条件", "微观优先改进需求", "优化策略提出", "优化策略列表"}
                base_cols_order = ["图片名称", "层级名称", "宏观外部现实条件", "微观优先改进需求", "优化策略提出", "优化策略列表"]
            
            all_data = []
            all_dimensions: Set[str] = set()
            
            for idx, row in df_input.iterrows():
                image_name = row["image_basename"] if not pd.isna(row["image_basename"]) else "未知图片名称"
                json_str = row["response"]
                
                single_data = self.parse_single_row(json_str, image_name)
                all_data.append(single_data)
                
                for col in single_data.keys():
                    if col not in base_cols:
                        all_dimensions.add(col)
                
                # 更新进度条
                if show_progress and progress_bar:
                    progress = (idx + 1) / total_rows
                    progress_bar.progress(progress, text=f"正在处理第 {idx + 1} / {total_rows} 行...")
            
            # 按图片名称中的数字进行自然数排序
            def extract_number_sort_key(item):
                img_name = item["图片名称"]
                # 提取所有数字
                numbers = re.findall(r'\d+', img_name)
                # 如果有数字，将第一个数字转换为整数作为排序键
                if numbers:
                    return int(numbers[0])
                # 否则使用字符串本身作为排序键
                return img_name
            
            all_data_sorted = sorted(
                all_data,
                key=extract_number_sort_key
            )
            
            dim_cols_order = sorted(list(all_dimensions))
            output_cols = base_cols_order + dim_cols_order
            
            output_data = []
            for data in all_data_sorted:
                row = {}
                for col in base_cols_order:
                    row[col] = data.get(col, "")
                for dim_col in dim_cols_order:
                    row[dim_col] = data.get(dim_col, self.MISSING_DIM_VALUE)
                output_data.append(row)
        
        df_output = pd.DataFrame(output_data, columns=output_cols)
        df_output.to_excel(output_excel_path, index=False, engine="openpyxl")
    
    def process_jsonl_file(self, input_path: str, input_filename: str, show_progress: bool = True, output_steps: Optional[List[Union[int, str]]] = None) -> Dict[str, str]:
        """
        处理JSONL文件，执行完整的处理流程或指定步骤
        :param input_path: 输入JSONL文件路径
        :param input_filename: 输入文件名
        :param show_progress: 是否显示进度条
        :param output_steps: 要执行的处理步骤，可以是数字列表或字符串列表
                             - 1 或 "json": 只生成JSON文件
                             - 2 或 "excel": 生成JSON和Excel文件
                             - 3 或 "structured": 生成所有文件，包括结构化Excel
                             - 列表形式如 ["structured"] 表示只输出结构化结果
        :return: 生成的文件路径字典，只包含用户请求的结果
        """
        input_basename = Path(input_filename).stem
        output_json_path = Path(self.OUTPUT_DIR) / f"{input_basename}.json"
        output_excel_path = Path(self.OUTPUT_DIR) / f"{input_basename}.xlsx"
        output_structured_path = Path(self.OUTPUT_DIR) / f"{input_basename}_structured.xlsx"
        
        # 确定用户实际需要的输出结果
        requested_results = set()
        if output_steps is None:
            # 默认返回所有结果
            requested_results = {"json", "excel", "structured"} if self.PROCESS_STEP == 3 else {"json", "excel"} if self.PROCESS_STEP >= 2 else {"json"}
        else:
            # 根据output_steps确定用户需要的结果
            for step in output_steps:
                if step == 1 or step == "json":
                    requested_results.add("json")
                elif step == 2 or step == "excel":
                    requested_results.update({"json", "excel"})
                elif step == 3 or step == "structured":
                    requested_results.add("structured")
        
        # 确定要执行的步骤
        execute_steps = set()
        if output_steps is None:
            # 默认执行所有配置的步骤
            execute_steps = {1, 2, 3} if self.PROCESS_STEP == 3 else {1, 2} if self.PROCESS_STEP >= 2 else {1}
        else:
            # 根据output_steps确定要执行的步骤
            for step in output_steps:
                if step == 1 or step == "json":
                    execute_steps.add(1)
                elif step == 2 or step == "excel":
                    execute_steps.update({1, 2})
                elif step == 3 or step == "structured":
                    execute_steps.update({1, 2, 3})
            # 确保步骤顺序正确
            execute_steps = sorted(execute_steps)
        
        # 执行处理步骤
        temp_result_files = {}
        
        if 1 in execute_steps:
            self.jsonl_to_json(input_path, str(output_json_path), show_progress=show_progress)
            temp_result_files["json"] = str(output_json_path)
        
        if 2 in execute_steps:
            # 确保步骤1已经执行
            if not os.path.exists(output_json_path):
                self.jsonl_to_json(input_path, str(output_json_path), show_progress=show_progress)
                temp_result_files["json"] = str(output_json_path)
            self.json_to_excel(str(output_json_path), str(output_excel_path), show_progress=show_progress)
            temp_result_files["excel"] = str(output_excel_path)
        
        if 3 in execute_steps:
            # 确保步骤2已经执行
            if not os.path.exists(output_excel_path):
                if not os.path.exists(output_json_path):
                    self.jsonl_to_json(input_path, str(output_json_path), show_progress=show_progress)
                    temp_result_files["json"] = str(output_json_path)
                self.json_to_excel(str(output_json_path), str(output_excel_path), show_progress=show_progress)
                temp_result_files["excel"] = str(output_excel_path)
            self.extract_structured_data(str(output_excel_path), str(output_structured_path), show_progress=show_progress)
            temp_result_files["structured"] = str(output_structured_path)
        
        # 只返回用户请求的结果
        result_files = {}
        for result_type in requested_results:
            if result_type in temp_result_files:
                result_files[result_type] = temp_result_files[result_type]
        
        return result_files

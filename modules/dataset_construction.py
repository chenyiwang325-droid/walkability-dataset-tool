import os
import json
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

class DatasetConstructor:
    """
    大模型数据集构建工具类
    用于构建问题诊断数据集，支持多模态和LLM模型
    """
    
    def __init__(self):
        # 核心配置参数
        self.image_directory = ""
        self.process_multiple_blocks = False
        self.image_path_prefix = ""
        self.data_source = "default"
        self.group_by_subdirectory = False
        self.enable_content_extraction = False
        
        # 内容提取配置
        self.extract_json_only_from_markdown = True
        self.json_extraction_source = "assistant"
        self.excel_extraction_source = "assistant"
        
        # 模型配置
        self.model_type = "multimodal"
        self.max_images = 0
        self.dataset_type = "test"
        
        # Excel读取设置
        self.excel_file_path = ""
        self.excel_image_name_column = "image_basename"
        self.user_excel_column = ""
        self.assistant_excel_column = "response"
        
        # JSON读取设置
        self.json_file_path = ""
        self.json_image_name_field = "images"
        self.json_messages_field = "messages"
        self.json_role_field = "role"
        self.json_content_field = "content"
        
        # 输出配置
        self.output_file_path = "output/dataset_{street_number}_{dataset_type}.json"
        self.json_image_name_source = "path"
        self.json_label_field = "label"
        self.include_label_in_output = False
        
        # 提示词组合配置
        self.user_content_prefix = ""
        self.user_content_suffix = ""
        self.user_content_default = "请你完成街道可步行性分析，根据提供的街景图像进行评估。"
        self.extracted_content_prefix = ""
        self.extracted_content_suffix = "\n"
        self.extracted_content_separator = "\n---\n"
        self.system_content = "请你以城市规划领域可步行性研究专家的身份，完成街道可步行性分析任务。"
    
    def set_config(self, config: Dict[str, Any]):
        """
        设置配置参数
        :param config: 配置字典
        """
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def extract_json_from_markdown(self, text: str) -> str:
        """
        从Markdown中提取JSON
        :param text: 输入文本
        :return: 提取的JSON字符串
        """
        if not text or not isinstance(text, str):
            return text
        
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
    
    def natural_sort_key(self, s: str) -> tuple:
        """
        生成自然排序键
        :param s: 字符串
        :return: 排序键元组
        """
        if not s:
            return ()
        numbers = re.findall(r'\d+', s)
        return tuple(map(int, numbers)) if numbers else (s,)
    
    def process_prompts(
        self,
        data_source: str,
        content_type: str,
        base_prefix: str,
        base_suffix: str,
        default_content: str,
        extracted_content: Any = None,
        is_group: bool = False,
        image_name: Any = None,
        group_key: str = None
    ) -> str:
        """
        处理提示词
        :param data_source: 数据源
        :param content_type: 内容类型
        :param base_prefix: 基础前缀
        :param base_suffix: 基础后缀
        :param default_content: 默认内容
        :param extracted_content: 提取的内容
        :param is_group: 是否为分组模式
        :param image_name: 图片名称
        :param group_key: 分组键
        :return: 处理后的提示词
        """
        if not self.enable_content_extraction:
            return default_content
        
        if not extracted_content:
            return default_content
        
        result = f"{base_prefix}"
        
        if isinstance(extracted_content, list):
            processed_items = []
            for idx, item in enumerate(extracted_content):
                item_image_name_str = str(image_name[idx] if isinstance(image_name, list) and idx < len(image_name) else image_name)
                item_str = f"{self.extracted_content_prefix.replace('{image_name}', item_image_name_str)}{item}{self.extracted_content_suffix}"
                processed_items.append(item_str)
            
            result += self.extracted_content_separator.join(processed_items)
        else:
            image_name_str = str(image_name)
            if image_name:
                result += self.extracted_content_prefix.replace('{image_name}', image_name_str)
            result += extracted_content
            if image_name:
                result += self.extracted_content_suffix
        
        result += base_suffix
        return result
    
    def get_local_image_info(self, root: str, file: str) -> Dict[str, Any]:
        """
        提取本地图片信息
        :param root: 根目录
        :param file: 文件名
        :return: 图片信息字典
        """
        img_filename = file
        final_img_path = f"{self.image_path_prefix}{img_filename}"  # 仅正斜杠
        img_name_no_ext = os.path.splitext(file)[0]
        
        local_full_path = os.path.join(root, file)
        rel_to_image_dir = os.path.relpath(local_full_path, self.image_directory)
        path_parts = rel_to_image_dir.split(os.sep)
        
        if self.process_multiple_blocks and len(path_parts) >= 3:
            group_key = path_parts[-2]
        elif len(path_parts) >= 2:
            group_key = path_parts[-2]
        else:
            group_key = "default_group"
        
        return {
            "internal_group_key": group_key,
            "final_img_path": final_img_path,
            "img_name_no_ext": img_name_no_ext,
            "sort_key": self.natural_sort_key(img_filename)
        }
    
    def extract_content_from_messages(self, messages: List[Dict[str, Any]], role: str) -> str:
        """
        从messages中提取指定角色的内容
        :param messages: 消息列表
        :param role: 角色
        :return: 提取的内容
        """
        if not messages or not isinstance(messages, list):
            return ""
        
        for msg in messages:
            if isinstance(msg, dict) and msg.get(self.json_role_field) == role:
                return msg.get(self.json_content_field, "").strip()
        
        return ""
    
    def read_data_source(self) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]], Dict[str, str]]:
        """
        读取数据源，建立“图片名→内容”映射
        :return: (image_to_content, image_to_prompt, image_to_label_path)
        """
        image_to_content = {}  # 存储提取的内容
        image_to_prompt = {}   # 存储原始提示词
        image_to_label_path = {}  # 存储图片标签路径
        
        if self.data_source == "excel":
            try:
                df = pd.read_excel(self.excel_file_path)
                
                # 根据设置动态确定必需的列
                required_cols = {self.excel_image_name_column}
                if self.excel_extraction_source == "user" and self.user_excel_column:
                    required_cols.add(self.user_excel_column)
                elif self.excel_extraction_source == "assistant" and self.assistant_excel_column:
                    required_cols.add(self.assistant_excel_column)
                elif self.excel_extraction_source == "both":
                    if self.user_excel_column: required_cols.add(self.user_excel_column)
                    if self.assistant_excel_column: required_cols.add(self.assistant_excel_column)
                
                if self.dataset_type == "train" and self.assistant_excel_column:
                    required_cols.add(self.assistant_excel_column)
                
                missing_cols = [col for col in required_cols if col and col not in df.columns]
                if missing_cols:
                    raise ValueError(f"Excel缺少必要列：{missing_cols}")
                
                for _, row in df.iterrows():
                    img_name_with_ext = str(row[self.excel_image_name_column]).strip()
                    img_name_no_ext = os.path.splitext(img_name_with_ext)[0].strip()
                    
                    raw_user_from_excel = str(row.get(self.user_excel_column, "")).strip() if self.user_excel_column else ""
                    raw_assistant_from_excel = str(row.get(self.assistant_excel_column, "")).strip() if self.assistant_excel_column else ""
                    
                    if self.extract_json_only_from_markdown:
                        raw_user_from_excel = self.extract_json_from_markdown(raw_user_from_excel)
                        raw_assistant_from_excel = self.extract_json_from_markdown(raw_assistant_from_excel)
                    
                    # 根据 EXCEL_EXTRACTION_SOURCE 分别准备用户和助手的内容
                    content_for_user_prompt = ""
                    target_assistant_response = ""
                    
                    if self.excel_extraction_source == "user":
                        content_for_user_prompt = raw_user_from_excel
                        if self.dataset_type == "train":
                            target_assistant_response = raw_assistant_from_excel
                    elif self.excel_extraction_source == "assistant":
                        content_for_user_prompt = ""  # 用户提示词使用默认
                        if self.dataset_type == "train":
                            target_assistant_response = raw_assistant_from_excel
                    elif self.excel_extraction_source == "both":
                        content_for_user_prompt = raw_user_from_excel
                        if self.dataset_type == "train":
                            target_assistant_response = raw_assistant_from_excel
                    
                    prompt_data = {
                        "user": content_for_user_prompt,
                        "assistant": target_assistant_response
                    }
                    
                    image_to_content[img_name_no_ext] = content_for_user_prompt
                    image_to_prompt[img_name_no_ext] = prompt_data
                    
                    if img_name_no_ext != img_name_with_ext:
                        image_to_content[img_name_with_ext] = content_for_user_prompt
                        image_to_prompt[img_name_with_ext] = prompt_data
                
            except Exception as e:
                raise Exception(f"读取Excel失败：{str(e)}")
        
        elif self.data_source == "json":
            try:
                with open(self.json_file_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                json_items = json_data if isinstance(json_data, list) else [json_data]
                
                for item_idx, item in enumerate(json_items):
                    messages = item.get(self.json_messages_field, [])
                    user_prompt = self.extract_content_from_messages(messages, "user")
                    assistant_prompt = self.extract_content_from_messages(messages, "assistant")
                    
                    if self.extract_json_only_from_markdown:
                        user_prompt = self.extract_json_from_markdown(user_prompt)
                        assistant_prompt = self.extract_json_from_markdown(assistant_prompt)
                    
                    extracted_content = ""
                    if self.json_extraction_source == "user":
                        extracted_content = user_prompt
                    elif self.json_extraction_source == "assistant":
                        extracted_content = assistant_prompt
                    elif self.json_extraction_source == "both":
                        extracted_content = f"{user_prompt}\n{assistant_prompt}"
                    
                    # 提取label的纯basename → 拼接IMAGE_PATH_PREFIX
                    images_array = item.get(self.json_image_name_field, [])
                    label_value = item.get(self.json_label_field, "").strip()
                    
                    img_names = []
                    label_full_paths = []  # 存储最终的“前缀+basename”完整路径
                    
                    if self.json_image_name_source == "path":
                        # 从images.path提取时：先取basename，再拼前缀
                        for img in images_array:
                            if isinstance(img, dict):
                                img_path = img.get("path", "").replace("\\", "/")
                                if img_path:
                                    img_basename = os.path.basename(img_path)  # 提取纯basename（如"1.jpg"）
                                    img_name_no_ext = os.path.splitext(img_basename)[0].strip()
                                    img_names.append(img_name_no_ext)
                    else:
                        # 从独立label字段提取时：先去源路径前缀→取basename→拼新前缀
                        if not label_value:
                            continue
                        # 关键：无论源label是完整路径还是纯文件名，先提取纯basename
                        label_basename = os.path.basename(label_value)  # 如源label是"abc/2.jpg"→取"2.jpg"
                        # 拼接前缀生成完整路径（IMAGE_PATH_PREFIX + basename）
                        label_full_path = f"{self.image_path_prefix}{label_basename}"
                        label_full_paths = [label_full_path]
                        # 图片名用无扩展名格式（用于关联content）
                        img_name_no_ext = os.path.splitext(label_basename)[0].strip()
                        img_names.append(img_name_no_ext)
                    
                    # 关联图片名与完整label路径（IMAGE_PATH_PREFIX + basename）
                    for idx, img_name in enumerate(img_names):
                        if not img_name:
                            continue
                        # 关联prompt和content
                        if img_name in image_to_prompt:
                            image_to_prompt[img_name]["user"] += "\n" + user_prompt
                            image_to_prompt[img_name]["assistant"] += "\n" + assistant_prompt
                        else:
                            image_to_prompt[img_name] = {
                                "user": user_prompt,
                                "assistant": assistant_prompt
                            }
                        if self.enable_content_extraction:
                            if img_name in image_to_content:
                                image_to_content[img_name] += "\n" + extracted_content
                            else:
                                image_to_content[img_name] = extracted_content
                        # 存储“前缀+basename”的完整路径到映射表
                        if label_full_paths and idx < len(label_full_paths):
                            image_to_label_path[img_name] = label_full_paths[idx]
            except Exception as e:
                raise Exception(f"读取JSON失败：{str(e)}")
        
        return image_to_content, image_to_prompt, image_to_label_path
    
    def build_dataset(self) -> Dict[str, Any]:
        """
        构建数据集
        :return: 构建的数据集结果
        """
        import random
        
        # 从图片目录提取街道编号，如果为空则使用默认值
        street_number = os.path.basename(self.image_directory) if self.image_directory else "default_street"
        
        # 确保图片路径前缀以斜杠结尾
        if not self.image_path_prefix.endswith("/"):
            self.image_path_prefix += "/"
        
        # 设置分组名称
        if self.group_by_subdirectory:
            group_name = "grouped"
        else:
            group_name = "ungrouped"
        
        # 确保输出路径是绝对路径，基于当前文件所在目录
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取项目根目录（当前目录的父目录）
        project_root = os.path.dirname(current_dir)
        
        # 替换输出文件路径中的变量
        formatted_output_path = self.output_file_path.format(street_number=street_number, dataset_type=self.dataset_type)
        
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(formatted_output_path):
            formatted_output_path = os.path.join(project_root, formatted_output_path)
        
        # 读取数据源
        image_to_content, image_to_prompt, image_to_label_path = self.read_data_source()
        
        # 遍历本地目录，获取图片信息并按自然顺序排序
        local_image_info = []
        for root, _, files in os.walk(self.image_directory):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")):
                    img_info = self.get_local_image_info(root, file)
                    local_image_info.append(img_info)
        
        if not local_image_info:
            raise ValueError(f"本地目录「{self.image_directory}」未找到图片")
        
        # 对所有图片先按自然顺序排序（全局排序）
        local_image_info.sort(key=lambda x: x["sort_key"])
        
        # 按内部分组键整理图片（组内仍保持自然顺序）
        all_images = []
        all_labels = []  # 存储“前缀+basename”的完整label路径
        image_groups = {}
        for img_info in local_image_info:
            group_key = img_info["internal_group_key"]
            final_img_path = img_info["final_img_path"]  # images字段的完整路径（原有逻辑）
            img_name = img_info["img_name_no_ext"]       # 图片名（无扩展名）
            img_basename = os.path.basename(final_img_path)  # 本地图片的纯basename（如"1.jpg"）
            
            # 关联label：优先用JSON生成的“前缀+basename”，无则用本地图片的“前缀+basename”
            label_full_path = image_to_label_path.get(img_name, f"{self.image_path_prefix}{img_basename}")
            
            all_images.append((final_img_path, img_name))  # images字段：完整路径
            all_labels.append((label_full_path, img_name))  # label字段：完整路径（前缀+basename）
            
            if self.group_by_subdirectory:
                if group_key not in image_groups:
                    image_groups[group_key] = []
                # 分组存储完整信息：(images路径, 图片名, label完整路径)
                image_groups[group_key].append((final_img_path, img_name, label_full_path))
        
        # 生成JSON结果（确保图片和提示词顺序一致）
        result = []
        if self.group_by_subdirectory:
            for group_key, group_imgs in image_groups.items():
                # 组内图片已按自然顺序排列，如需采样仍保持相对顺序
                if self.model_type == "multimodal" and self.max_images > 0 and len(group_imgs) > self.max_images:
                    # 采样后按原顺序排序
                    selected_indices = sorted(random.sample(range(len(group_imgs)), self.max_images))
                    selected_imgs = [group_imgs[i] for i in selected_indices]
                else:
                    selected_imgs = group_imgs  # 已自然排序
                
                # 提取内容（按排序后的图片顺序）
                extracted_contents = []
                image_names = []
                for _, img_name, _ in selected_imgs:
                    image_names.append(img_name)
                    if self.enable_content_extraction:
                        extracted_contents.append(image_to_content.get(img_name, ""))
                
                # 处理用户提示词（顺序与图片一致）
                if self.enable_content_extraction:
                    final_user = self.process_prompts(
                        data_source=self.data_source,
                        content_type="user",
                        base_prefix=self.user_content_prefix,
                        base_suffix=self.user_content_suffix,
                        default_content=self.user_content_default,
                        extracted_content=extracted_contents if extracted_contents else None,
                        is_group=True,
                        image_name=image_names,
                        group_key=group_key
                    )
                else:
                    group_user_prompts = [image_to_prompt.get(img_name, {}).get("user", "") for _, img_name, _ in selected_imgs]
                    final_user = self.process_prompts(
                        data_source=self.data_source,
                        content_type="user",
                        base_prefix=self.user_content_prefix,
                        base_suffix=self.user_content_suffix,
                        default_content=self.user_content_default,
                        extracted_content=group_user_prompts if group_user_prompts else None,
                        is_group=True,
                        image_name=image_names,
                        group_key=group_key
                    )
                
                # 处理助手提示词
                final_assist = ""
                if self.dataset_type == "train":
                    group_assist_prompts = [image_to_prompt.get(img_name, {}).get("assistant", "") for _, img_name, _ in selected_imgs]
                    final_assist = self.process_prompts(
                        data_source=self.data_source,
                        content_type="assistant",
                        base_prefix="",
                        base_suffix="",
                        default_content="",
                        extracted_content=group_assist_prompts if group_assist_prompts else None,
                        is_group=True,
                        image_name=image_names,
                        group_key=group_key
                    )
                
                # 构建条目（images和提示词顺序一致）
                entry = {
                    "messages": [
                        {"role": "system", "content": self.system_content},
                        {"role": "user", "content": final_user}
                    ] + ([{"role": "assistant", "content": final_assist}] if self.dataset_type == "train" else [])
                }
                if self.model_type == "multimodal":
                    entry["images"] = [path for path, _, _ in selected_imgs]  # images：完整路径
                if self.include_label_in_output:
                    entry["label"] = [label for _, _, label in selected_imgs]  # label：完整路径（IMAGE_PATH_PREFIX+basename）
                result.append(entry)
        
        else:
            # 非分组模式（全局自然排序） - 为每张图片生成一个条目
            # 不采样，直接使用所有图片
            selected_imgs = all_images  # 已自然排序
            selected_labels = all_labels  # 赋值完整label列表
            
            # 循环中使用同步后的selected_imgs和selected_labels，为每张图片生成一个条目
            for (img_path, img_name), (label_path, _) in zip(selected_imgs, selected_labels):
                extracted_content = image_to_content.get(img_name, "") if self.enable_content_extraction else None
                
                # 处理用户提示词（原有逻辑不变）
                if self.enable_content_extraction:
                    final_user = self.process_prompts(
                        data_source=self.data_source,
                        content_type="user",
                        base_prefix=self.user_content_prefix,
                        base_suffix=self.user_content_suffix,
                        default_content=self.user_content_default,
                        extracted_content=extracted_content if extracted_content else None,
                        image_name=img_name
                    )
                else:
                    user_prompt = image_to_prompt.get(img_name, {}).get("user", "")
                    final_user = self.process_prompts(
                        data_source=self.data_source,
                        content_type="user",
                        base_prefix=self.user_content_prefix,
                        base_suffix=self.user_content_suffix,
                        default_content=self.user_content_default,
                        extracted_content=user_prompt if user_prompt else None,
                        image_name=img_name
                    )
                
                # 处理助手提示词（原有逻辑不变）
                final_assist = ""
                if self.dataset_type == "train":
                    assist_prompt = image_to_prompt.get(img_name, {}).get("assistant", "")
                    final_assist = self.process_prompts(
                        data_source=self.data_source,
                        content_type="assistant",
                        base_prefix="",
                        base_suffix="",
                        default_content="",
                        extracted_content=assist_prompt if assist_prompt else None,
                        image_name=img_name
                    )
                
                # 构建条目（原有逻辑不变，含label字段）
                entry = {
                    "messages": [
                        {"role": "system", "content": self.system_content},
                        {"role": "user", "content": final_user}
                    ] + ([{"role": "assistant", "content": final_assist}] if self.dataset_type == "train" else [])
                }
                if self.model_type == "multimodal":
                    entry["images"] = [img_path]  # images：完整路径
                if self.include_label_in_output:
                    entry["label"] = [label_path]  # label：完整路径
                result.append(entry)
        
        return {
            "result": result,
            "output_path": formatted_output_path
        }
    
    def save_dataset(self, dataset_result: Dict[str, Any]):
        """
        保存数据集结果到文件
        :param dataset_result: 数据集结果
        """
        result = dataset_result["result"]
        formatted_output_path = dataset_result["output_path"]
        
        # 确保输出目录存在
        output_dir = os.path.dirname(formatted_output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 添加调试信息，打印实际的输出文件路径
        print(f"DEBUG: 正在保存数据集到: {formatted_output_path}")
        print(f"DEBUG: 输出目录: {output_dir}")
        print(f"DEBUG: 结果数据量: {len(result)}条")
        
        # 保存文件
        with open(formatted_output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 验证文件是否成功保存
        if os.path.exists(formatted_output_path):
            print(f"DEBUG: 数据集保存成功！文件大小: {os.path.getsize(formatted_output_path)}字节")
        else:
            print(f"DEBUG: 数据集保存失败！文件未找到: {formatted_output_path}")
    
    def preview_dataset(self, dataset_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        预览数据集结果
        :param dataset_result: 数据集结果
        :return: 预览数据（前几条）
        """
        result = dataset_result["result"]
        # 返回前3条作为预览
        return result[:3]    
    
    def format_preview_entry(self, entry: Dict[str, Any]) -> str:
        """
        格式化预览条目，用于更直观地展示数据集内容
        :param entry: 数据集条目
        :return: 格式化后的预览字符串
        """
        formatted = """
## 数据集条目预览

### 系统提示词
{system_content}

### 用户提示词
{user_content}
"""
        
        # 提取系统提示词和用户提示词
        system_content = ""
        user_content = ""
        assistant_content = ""
        
        for msg in entry.get("messages", []):
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]
            elif msg["role"] == "assistant":
                assistant_content = msg["content"]
        
        # 格式化系统提示词（只显示前200个字符）
        formatted_system = system_content[:200] + "..." if len(system_content) > 200 else system_content
        
        # 格式化用户提示词
        formatted_user = user_content[:300] + "..." if len(user_content) > 300 else user_content
        
        # 构建基础格式
        preview = formatted.format(
            system_content=formatted_system,
            user_content=formatted_user
        )
        
        # 如果是train模式，添加助手提示词
        if assistant_content:
            formatted_assistant = assistant_content[:300] + "..." if len(assistant_content) > 300 else assistant_content
            preview += f"\n### 助手响应\n{formatted_assistant}\n"
        
        # 添加图片信息
        if "images" in entry and entry["images"]:
            images = entry["images"]
            preview += f"\n### 图片信息\n包含 {len(images)} 张图片:\n"
            for i, img in enumerate(images[:3]):  # 只显示前3张图片
                preview += f"- {img}\n"
            if len(images) > 3:
                preview += f"- ... 还有 {len(images) - 3} 张图片\n"
        
        # 添加标签信息
        if "label" in entry and entry["label"]:
            labels = entry["label"]
            preview += f"\n### 标签信息\n包含 {len(labels)} 个标签:\n"
            for i, label in enumerate(labels[:3]):  # 只显示前3个标签
                preview += f"- {label}\n"
            if len(labels) > 3:
                preview += f"- ... 还有 {len(labels) - 3} 个标签\n"
        
        return preview

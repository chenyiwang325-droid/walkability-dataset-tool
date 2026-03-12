import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class PresetManager:
    """
    预设参数管理工具类
    用于管理各功能的预设参数，支持保存、加载和导出预设
    """
    
    def __init__(self, presets_dir: str = "presets"):
        """
        初始化预设管理器
        :param presets_dir: 预设文件存储目录
        """
        self.presets_dir = Path(presets_dir)
        # 确保预设目录存在
        self.presets_dir.mkdir(parents=True, exist_ok=True)
    
    def save_preset(self, preset_name: str, function_name: str, params: Dict[str, Any]) -> str:
        """
        保存预设参数
        :param preset_name: 预设名称
        :param function_name: 功能名称
        :param params: 预设参数
        :return: 保存的预设文件路径
        """
        preset = {
            "name": preset_name,
            "function": function_name,
            "params": params,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 构建预设文件路径
        preset_filename = f"{function_name}_{preset_name.replace(' ', '_')}.json"
        preset_path = self.presets_dir / preset_filename
        
        # 保存预设
        with open(preset_path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        
        return str(preset_path)
    
    def load_preset(self, preset_path: str) -> Dict[str, Any]:
        """
        加载预设参数
        :param preset_path: 预设文件路径
        :return: 预设参数
        """
        if not os.path.exists(preset_path):
            raise FileNotFoundError(f"预设文件不存在: {preset_path}")
        
        with open(preset_path, "r", encoding="utf-8") as f:
            preset = json.load(f)
        
        return preset
    
    def get_presets(self, function_name: str = None) -> List[Dict[str, Any]]:
        """
        获取预设列表
        :param function_name: 功能名称，可选，用于过滤特定功能的预设
        :return: 预设列表
        """
        presets = []
        
        # 遍历预设目录下的所有JSON文件
        for preset_file in self.presets_dir.glob("*.json"):
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    preset = json.load(f)
                
                # 如果指定了功能名称，则过滤
                if function_name and preset.get("function") != function_name:
                    continue
                
                # 添加预设文件路径
                preset["file_path"] = str(preset_file)
                presets.append(preset)
            except Exception as e:
                print(f"读取预设文件失败 {preset_file}: {str(e)}")
        
        # 按更新时间倒序排序
        presets.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return presets
    
    def delete_preset(self, preset_path: str) -> bool:
        """
        删除预设文件
        :param preset_path: 预设文件路径
        :return: 是否删除成功
        """
        if os.path.exists(preset_path):
            os.remove(preset_path)
            return True
        return False
    
    def export_preset(self, preset_path: str, export_dir: str = None) -> str:
        """
        导出预设文件
        :param preset_path: 预设文件路径
        :param export_dir: 导出目录，可选
        :return: 导出的文件路径
        """
        if not os.path.exists(preset_path):
            raise FileNotFoundError(f"预设文件不存在: {preset_path}")
        
        # 如果未指定导出目录，则使用当前目录
        if not export_dir:
            export_dir = Path(".")
        else:
            export_dir = Path(export_dir)
            export_dir.mkdir(parents=True, exist_ok=True)
        
        # 读取预设内容
        with open(preset_path, "r", encoding="utf-8") as f:
            preset = json.load(f)
        
        # 构建导出文件名
        export_filename = f"preset_{preset['function']}_{preset['name'].replace(' ', '_')}.json"
        export_path = export_dir / export_filename
        
        # 导出预设
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        
        return str(export_path)
    
    def import_preset(self, import_path: str) -> str:
        """
        导入预设文件
        :param import_path: 导入文件路径
        :return: 导入的预设文件路径
        """
        if not os.path.exists(import_path):
            raise FileNotFoundError(f"导入文件不存在: {import_path}")
        
        # 读取导入的预设内容
        with open(import_path, "r", encoding="utf-8") as f:
            preset = json.load(f)
        
        # 验证预设格式
        required_fields = ["name", "function", "params"]
        for field in required_fields:
            if field not in preset:
                raise ValueError(f"导入的预设文件缺少必要字段: {field}")
        
        # 构建导入后的文件路径
        preset_filename = f"{preset['function']}_{preset['name'].replace(' ', '_')}.json"
        preset_path = self.presets_dir / preset_filename
        
        # 更新时间戳
        preset["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        preset["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存导入的预设
        with open(preset_path, "w", encoding="utf-8") as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)
        
        return str(preset_path)

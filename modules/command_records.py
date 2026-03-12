import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Union

class CommandRecordsManager:
    """
    命令行记录管理工具类
    用于记录和管理命令行代码，支持添加、编辑和删除记录
    """
    
    def __init__(self, records_file: str):
        """
        初始化命令行记录管理器
        :param records_file: 记录文件路径
        """
        self.records_file = records_file
        self.records: List[Dict[str, Any]] = []
        self.load_records()
    
    def load_records(self) -> None:
        """
        从文件加载命令行记录
        """
        if os.path.exists(self.records_file):
            with open(self.records_file, "r", encoding="utf-8") as f:
                self.records = json.load(f)
        else:
            self.records = []
    
    def save_records(self) -> None:
        """
        保存命令行记录到文件
        """
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def add_record(self, command: str) -> Dict[str, Any]:
        """
        添加新的命令行记录
        :param command: 命令行代码
        :return: 添加的记录
        """
        record = {
            "id": str(uuid.uuid4()),
            "command": command.strip(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.records.append(record)
        self.save_records()
        return record
    
    def delete_record(self, record_id: str) -> bool:
        """
        删除命令行记录
        :param record_id: 记录ID
        :return: 是否删除成功
        """
        initial_length = len(self.records)
        self.records = [r for r in self.records if r["id"] != record_id]
        if len(self.records) < initial_length:
            self.save_records()
            return True
        return False
    
    def update_record(self, record_id: str, new_command: str) -> bool:
        """
        更新命令行记录
        :param record_id: 记录ID
        :param new_command: 新的命令行代码
        :return: 是否更新成功
        """
        for record in self.records:
            if record["id"] == record_id:
                record["command"] = new_command.strip()
                record["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_records()
                return True
        return False
    
    def get_records(self, sort_by: str = "created_at", reverse: bool = True) -> List[Dict[str, Any]]:
        """
        获取命令行记录列表
        :param sort_by: 排序字段
        :param reverse: 是否倒序
        :return: 排序后的记录列表
        """
        sorted_records = sorted(self.records, key=lambda x: x[sort_by], reverse=reverse)
        return sorted_records
    
    def get_record(self, record_id: str) -> Union[Dict[str, Any], None]:
        """
        获取单个命令行记录
        :param record_id: 记录ID
        :return: 记录或None
        """
        for record in self.records:
            if record["id"] == record_id:
                return record
        return None

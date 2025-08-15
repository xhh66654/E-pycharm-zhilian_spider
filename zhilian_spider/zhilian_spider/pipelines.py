# -*- coding: utf-8 -*-
import json
import os


class SaveToJsonPipeline:
    """
    将所有 item 追加写入 data/data.json（保留你最初逻辑，并确保目录存在）
    """
    def __init__(self):
        self.folder_path = "data"
        os.makedirs(self.folder_path, exist_ok=True)
        self.file_path = os.path.join(self.folder_path, "data.json")
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    def process_item(self, item, spider):
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.append(dict(item))
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return item

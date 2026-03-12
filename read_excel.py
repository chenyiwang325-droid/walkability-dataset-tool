import pandas as pd

# 读取Excel文件
excel_path = r"d:/我的坚果云/硕士论文/1_优化策略/优化策略提取/知识图谱梳理表格 (1).xlsx"
df = pd.read_excel(excel_path)

# 查看前几行数据
print("=== Excel表格前5行数据 ===")
print(df.head())

# 查看"问题归因"列的前10个值
print("\n=== 问题归因列前10个值 ===")
print(df['问题归因'].head(10))

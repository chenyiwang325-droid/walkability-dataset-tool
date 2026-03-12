import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from modules.optimization_strategy import OptimizationStrategyExtractor
from modules.implementation_measures import ImplementationMeasuresExtractor
from modules.jsonl_processing import JSONLProcessor
from modules.dataset_construction import DatasetConstructor
from modules.command_records import CommandRecordsManager
from modules.preset_manager import PresetManager

# 获取项目根目录（当前文件所在目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 设置页面配置
st.set_page_config(
    page_title="可步行性数据集构建工具",
    page_icon="🚶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 创建工具实例
extractor = OptimizationStrategyExtractor()
measures_extractor = ImplementationMeasuresExtractor()
jsonl_processor = JSONLProcessor()
command_records_file = os.path.join(PROJECT_ROOT, "command_records.json")
command_manager = CommandRecordsManager(command_records_file)
preset_manager = PresetManager(os.path.join(PROJECT_ROOT, "presets"))

# 侧边栏导航
with st.sidebar:
    st.title("可步行性数据集构建工具")
    
    st.header("功能选择")
    app_mode = st.radio(
        "选择您需要的功能",
        ["优化策略提取", "实施举措提取", "JSONL处理", "大模型数据集构建", "命令行记录"],
        index=0,
        help="选择不同的功能模块进行操作"
    )
    
    st.header("工具信息")
    
    with st.expander("关于工具", expanded=False):
        st.write("可步行性数据集构建工具用于从大模型输出中提取问题归因结果，并根据Excel表格匹配对应的优化策略，同时支持数据集构建和JSONL处理。")
    
    with st.expander("功能说明", expanded=False):
        st.write("✅ 支持JSON/JSONL文件上传")
        st.write("✅ 自动提取问题归因结果")
        st.write("✅ 匹配优化策略和内涵")
        st.write("✅ 生成JSON和Markdown结果")
        st.write("✅ 构建大模型数据集")
        st.write("✅ 管理命令行记录")
    
    with st.expander("联系我们", expanded=False):
        st.write("如有问题或建议，请联系开发人员。")

# 页面标题 - 简化设计
st.header("可步行性数据集构建工具")

# 优化策略提取功能
if app_mode == "优化策略提取":
    # 定义默认值，确保变量在整个功能中都能访问
    image_basename_col = "image_basename"
    question_causes_col = "问题归因结果"
    
    # 示例展示区 - 点击展开查看示例
    with st.expander("查看示例", expanded=False):
        tab1, tab2 = st.tabs(["输入示例", "输出示例"])
        
        with tab1:
            st.subheader("输入示例")
            st.code('''{
  "问题归因结果": ["人行通道堵塞", "过街设施不足", "照明条件差"]
}''', language="json")
        
        with tab2:
            st.subheader("输出示例")
            st.code('''# 问题归因及优化策略

## 1. 人行通道堵塞

### 1. 保障人行通道完整性与可通行性
保障人行通道的完整性与可通行性，消除路径堵塞、阻断等问题，让行人拥有无阻碍的专属步行空间。''', language="markdown")

    # 核心功能区 - 文件上传（置于主体位置）
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("上传大模型输出文件或Excel表格")
        uploaded_file = st.file_uploader(
            "选择JSON、JSONL或Excel文件",
            type=["json", "jsonl", "xlsx"],
            help="支持上传JSON、JSONL格式的大模型输出文件，或Excel表格作为数据源，建议文件大小不超过10MB",
            label_visibility="collapsed"
        )
        
        # 显示文件信息
        if uploaded_file:
            st.info(f"已上传: {uploaded_file.name}")
        else:
            st.warning("请上传大模型输出文件或Excel表格")

    with col2:
        st.subheader("上传优化策略表格（可选）")
        uploaded_excel = st.file_uploader(
            "选择Excel表格",
            type=["xlsx"],
            help="包含问题归因、优化策略和优化策略内涵的Excel表格",
            label_visibility="collapsed"
        )
        
        # 设置默认Excel路径 - 使用基于项目根目录的绝对路径
        default_excel_path = os.path.join(PROJECT_ROOT, "docs", "知识图谱梳理表格 (1).xlsx")
        
        # 显示当前使用的Excel表格
        if uploaded_excel:
            st.info(f"使用上传的表格: {uploaded_excel.name}")
        elif os.path.exists(default_excel_path):
            st.info(f"使用默认表格: {Path(default_excel_path).name}")
            st.caption(f"默认表格位置: {default_excel_path}")
        else:
            st.warning("未找到默认表格，请上传自定义优化策略表格")
    
    # 高级设置区 - 可调整的输出设置
    with st.expander("高级设置", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 自定义输出目录
            output_dir = st.text_input(
                "输出目录",
                value="output/optimization_strategy",
                help="设置结果文件的保存目录"
            )
            st.caption("提示：您可以直接在输入框中输入目录路径，或在代码中修改默认路径")
        
        with col2:
            # 自定义文件名前缀
            filename_prefix = st.text_input(
                "文件名前缀",
                value="优化策略提取结果",
                help="设置结果文件的文件名前缀"
            )
    
    # Excel数据源配置
    with st.expander("Excel数据源配置", expanded=False):
        st.write("当上传Excel表格作为数据源时，需要配置以下选项：")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            image_basename_col = st.text_input(
                "图片名称列",
                value=image_basename_col,
                help="Excel表格中包含图片名称的列名"
            )
        
        with col2:
            question_causes_col = st.text_input(
                "问题原因列表列",
                value=question_causes_col,
                help="Excel表格中包含问题原因列表的列名"
            )

    # 处理按钮 - 突出显示
    st.empty()  # 添加空行
    if st.button("开始处理", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("❌ 请先上传大模型输出文件")
        else:
            with st.spinner("正在处理文件..."):
                try:
                    # 读取上传的文件信息
                    file_name = uploaded_file.name
                    file_extension = Path(file_name).suffix.lower()
                    
                    # 确定使用的Excel路径
                    excel_path = uploaded_excel if uploaded_excel else default_excel_path
                    
                    # 处理文件
                    if file_extension == ".jsonl":
                        # 处理JSONL文件 - 需要先保存到临时文件
                        file_content = uploaded_file.getvalue().decode("utf-8")
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
                            f.write(file_content)
                            temp_file_path = f.name
                        
                        try:
                            json_result, markdown_result, excel_result_df = extractor.process_jsonl_file(
                                temp_file_path, excel_path
                            )
                        finally:
                            # 删除临时文件
                            import os
                            os.unlink(temp_file_path)
                    elif file_extension == ".xlsx":
                        # 处理Excel文件 - 直接使用字节流
                        json_result, markdown_result, excel_result_df = extractor.process_excel_file(
                            uploaded_file.getvalue(), excel_path, image_basename_col, question_causes_col
                        )
                    else:
                        # 处理JSON文件 - 解码为UTF-8
                        file_content = uploaded_file.getvalue().decode("utf-8")
                        json_result, markdown_result, excel_result_df = extractor.process_file(
                            file_content, excel_path
                        )
                    
                    # 生成文件名（基于当前时间）
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_name = f"{filename_prefix}_{timestamp}"
                    
                    # 保存结果到指定目录，单独建一个文件夹
                    # 确保输出目录基于项目根目录
                    if not os.path.isabs(output_dir):
                        save_folder = os.path.join(PROJECT_ROOT, output_dir, base_name)
                    else:
                        save_folder = os.path.join(output_dir, base_name)
                    os.makedirs(save_folder, exist_ok=True)
                    
                    # 保存结果
                    json_file_path = os.path.join(save_folder, f"{base_name}.json")
                    markdown_file_path = os.path.join(save_folder, f"{base_name}.md")
                    excel_file_path = os.path.join(save_folder, f"{base_name}.xlsx")
                    
                    extractor.save_result(json_result, json_file_path, "json")
                    extractor.save_result(markdown_result, markdown_file_path, "markdown")
                    excel_result_df.to_excel(excel_file_path, index=False, engine="openpyxl")
                    
                    # 结果展示区域 - 简化设计
                    st.success(f"处理完成！结果已保存到: {save_folder}")
                    
                    # 结果展示
                    with st.expander("查看结果", expanded=True):
                        tab1, tab2 = st.tabs(["JSON格式", "Markdown格式"])
                        
                        with tab1:
                            # 使用容器和滚动条展示大量JSON数据
                            json_container = st.container(height=500, border=True)
                            with json_container:
                                st.json(json_result)
                        
                        with tab2:
                            # 使用容器和滚动条展示大量Markdown数据
                            md_container = st.container(height=500, border=True)
                            with md_container:
                                st.markdown(markdown_result)
                    
                    # 下载区域 - 简化设计
                    st.subheader("下载结果")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        with open(json_file_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="下载JSON结果",
                                data=f,
                                file_name=f"{base_name}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                    
                    with col2:
                        with open(markdown_file_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="下载Markdown结果",
                                data=f,
                                file_name=f"{base_name}.md",
                                mime="text/markdown",
                                use_container_width=True
                            )
                    
                    with col3:
                        with open(excel_file_path, "rb") as f:
                            st.download_button(
                                label="下载Excel结果",
                                data=f,
                                file_name=f"{base_name}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.exception(e)

    # 结果文件上传区 - 用于上传和展示其他输出结果文件
    with st.expander("上传结果文件", expanded=False):
        st.write("上传并查看其他输出结果文件：")
        
        # 上传JSON结果文件
        uploaded_json_result = st.file_uploader(
            "上传JSON结果文件",
            type=["json"],
            help="上传JSON格式的结果文件",
            key="json_result_uploader"
        )
        
        # 上传Markdown结果文件
        uploaded_md_result = st.file_uploader(
            "上传Markdown结果文件",
            type=["md"],
            help="上传Markdown格式的结果文件",
            key="md_result_uploader"
        )
        
        # 展示上传的JSON结果
        if uploaded_json_result:
            st.subheader("上传的JSON结果")
            try:
                json_content = json.load(uploaded_json_result)
                # 使用容器和滚动条展示大量JSON数据
                json_container = st.container(height=500, border=True)
                with json_container:
                    st.json(json_content)
            except json.JSONDecodeError:
                st.error("无法解析JSON文件，请检查文件格式")
        
        # 展示上传的Markdown结果
        if uploaded_md_result:
            st.subheader("上传的Markdown结果")
            try:
                md_content = uploaded_md_result.read().decode("utf-8")
                # 使用容器和滚动条展示大量Markdown数据
                md_container = st.container(height=500, border=True)
                with md_container:
                    st.markdown(md_content)
            except UnicodeDecodeError:
                st.error("无法读取Markdown文件，请检查文件编码")

# JSONL处理功能
elif app_mode == "JSONL处理":
    st.subheader("JSONL处理功能")
    st.write("此功能用于将JSONL文件转换为JSON文件，并支持进一步转换为Excel和结构化Excel文件。")
    
    # 添加配置部分
    with st.expander("配置参数", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 处理模式配置
            process_mode = st.selectbox(
                "处理模式",
                ["diagnosis", "optimization", "general"],
                index=1,
                help="diagnosis（问题诊断）、optimization（优化方向）、general（通用提取）"
            )
        
        with col2:
            # 输出目录
            output_dir = st.text_input(
                "输出目录",
                value="output/jsonl_processing",
                help="设置结果文件的保存目录"
            )
            st.caption("提示：您可以直接在输入框中输入目录路径")
        
        # 合并处理步骤和输出结果选项为一个选择框
        output_options = st.selectbox(
            "输出结果选项",
            [
                "全部输出（JSON+Excel+结构化Excel）",
                "只输出JSON",
                "只输出JSON和Excel",
                "只输出结构化Excel"
            ],
            index=0,
            help="选择要生成的结果文件类型，对应不同的处理步骤"
        )
    
    # 文件上传
    uploaded_jsonl = st.file_uploader(
        "选择JSONL文件",
        type=["jsonl"],
        help="支持上传JSONL格式的文件，建议文件大小不超过10MB"
    )
    
    # 处理按钮
    if st.button("开始处理JSONL文件", type="primary", use_container_width=True):
        if not uploaded_jsonl:
            st.error("❌ 请先上传JSONL文件")
        else:
            with st.spinner("正在处理JSONL文件..."):
                try:
                    # 保存上传的文件到临时目录
                    import tempfile
                    import os
                    
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
                        f.write(uploaded_jsonl.getvalue().decode("utf-8"))
                        temp_jsonl_path = f.name
                    
                    try:
                        # 根据输出选项确定process_step和output_steps
                        process_step = 3  # 默认完整流程
                        output_steps = None
                        
                        if output_options == "只输出JSON":
                            process_step = 1
                            output_steps = ["json"]
                        elif output_options == "只输出JSON和Excel":
                            process_step = 2
                            output_steps = ["excel"]
                        elif output_options == "只输出结构化Excel":
                            process_step = 3
                            output_steps = ["structured"]
                        # 全部输出则保持默认值
                        
                        # 设置处理器配置
                        jsonl_processor.set_config(process_step, process_mode, output_dir)
                        
                        # 处理JSONL文件
                        result_files = jsonl_processor.process_jsonl_file(temp_jsonl_path, uploaded_jsonl.name, output_steps=output_steps)
                        
                        # 显示处理结果
                        st.success("JSONL文件处理完成！")
                        
                        # 显示生成的文件
                        st.subheader("生成的文件")
                        for file_type, file_path in result_files.items():
                            st.write(f"{file_type.upper()}文件: {file_path}")
                            
                            # 提供下载链接
                            with open(file_path, "rb") as f:
                                st.download_button(
                                    label=f"下载{file_type.upper()}文件",
                                    data=f,
                                    file_name=os.path.basename(file_path),
                                    mime="application/json" if file_type == "json" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                    finally:
                        # 删除临时文件
                        os.unlink(temp_jsonl_path)
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.exception(e)

# 大模型数据集构建功能
elif app_mode == "大模型数据集构建":
    st.subheader("大模型数据集构建")
    st.write("此功能用于构建大模型数据集，支持多模态和LLM模型。")
    
    # 确保session_state中始终存在dataset_constructor实例
    if "dataset_constructor" not in st.session_state:
        st.session_state.dataset_constructor = DatasetConstructor()
    dataset_constructor = st.session_state.dataset_constructor
    
    # 保存实例到session_state，确保状态持久化
    def save_constructor_state():
        st.session_state.dataset_constructor = dataset_constructor
    
    # 在页面渲染完成后保存状态
    st.empty()  # 占位符，确保该代码在所有组件渲染后执行
    save_constructor_state()
    
    # 预设管理
    with st.expander("预设参数管理", expanded=False):
        # 加载预设
        presets = preset_manager.get_presets("dataset_construction")
        
        # 预设列表显示和操作
        if presets:
            st.subheader("已保存的预设")
            for i, preset in enumerate(presets):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{preset['name']}**")
                        st.caption(f"创建于: {preset['created_at']} | 更新于: {preset['updated_at']}")
                    with col2:
                        if st.button("加载", key=f"load_{i}", use_container_width=True):
                            dataset_constructor.set_config(preset["params"])
                            st.success(f"已加载预设: {preset['name']}")
                    with col3:
                        if st.button("删除", key=f"delete_{i}", use_container_width=True, type="secondary"):
                            if preset_manager.delete_preset(preset["file_path"]):
                                st.success(f"已删除预设: {preset['name']}")
                                st.rerun()
                            else:
                                st.error(f"删除预设失败: {preset['name']}")
        
        # 保存新预设
        st.subheader("保存新预设")
        save_preset_name = st.text_input(
            "保存当前配置为预设",
            placeholder="输入预设名称",
            key="save_preset_name"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("保存预设", type="primary", use_container_width=True, key="save_preset_btn"):
                if save_preset_name.strip():
                    # 确保获取最新的配置参数
                    # 重新保存实例到session_state，确保获取最新参数
                    st.session_state.dataset_constructor = dataset_constructor
                    
                    # 获取当前配置
                    current_config = {
                        "image_directory": dataset_constructor.image_directory,
                        "process_multiple_blocks": dataset_constructor.process_multiple_blocks,
                        "image_path_prefix": dataset_constructor.image_path_prefix,
                        "data_source": dataset_constructor.data_source,
                        "group_by_subdirectory": dataset_constructor.group_by_subdirectory,
                        "enable_content_extraction": dataset_constructor.enable_content_extraction,
                        "extract_json_only_from_markdown": dataset_constructor.extract_json_only_from_markdown,
                        "json_extraction_source": dataset_constructor.json_extraction_source,
                        "excel_extraction_source": dataset_constructor.excel_extraction_source,
                        "model_type": dataset_constructor.model_type,
                        "max_images": dataset_constructor.max_images,
                        "dataset_type": dataset_constructor.dataset_type,
                        "excel_file_path": dataset_constructor.excel_file_path,
                        "excel_image_name_column": dataset_constructor.excel_image_name_column,
                        "user_excel_column": dataset_constructor.user_excel_column,
                        "assistant_excel_column": dataset_constructor.assistant_excel_column,
                        "json_file_path": dataset_constructor.json_file_path,
                        "json_image_name_field": dataset_constructor.json_image_name_field,
                        "json_messages_field": dataset_constructor.json_messages_field,
                        "json_role_field": dataset_constructor.json_role_field,
                        "json_content_field": dataset_constructor.json_content_field,
                        "output_file_path": dataset_constructor.output_file_path,
                        "json_image_name_source": dataset_constructor.json_image_name_source,
                        "json_label_field": dataset_constructor.json_label_field,
                        "include_label_in_output": dataset_constructor.include_label_in_output,
                        "user_content_prefix": dataset_constructor.user_content_prefix,
                        "user_content_suffix": dataset_constructor.user_content_suffix,
                        "user_content_default": dataset_constructor.user_content_default,
                        "extracted_content_prefix": dataset_constructor.extracted_content_prefix,
                        "extracted_content_suffix": dataset_constructor.extracted_content_suffix,
                        "extracted_content_separator": dataset_constructor.extracted_content_separator,
                        "system_content": dataset_constructor.system_content
                    }
                    
                    # 保存预设，使用w模式确保覆盖现有文件
                    preset_path = preset_manager.save_preset(
                        save_preset_name.strip(), 
                        "dataset_construction", 
                        current_config
                    )
                    
                    st.success(f"预设已保存到: {preset_path}")
                    # 显示保存的文件内容，供用户验证
                    with open(preset_path, 'r', encoding='utf-8') as f:
                        saved_preset = json.load(f)
                    st.json(saved_preset, expanded=False)
                else:
                    st.error("请输入预设名称")
        
        with col2:
            # 导入预设
            uploaded_preset = st.file_uploader(
                "导入预设文件",
                type=["json"],
                label_visibility="collapsed"
            )
            
            if uploaded_preset:
                with st.spinner("正在导入预设..."):
                    try:
                        # 保存上传的文件到临时目录
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                            f.write(uploaded_preset.getvalue().decode("utf-8"))
                            temp_preset_path = f.name
                        
                        # 导入预设
                        imported_path = preset_manager.import_preset(temp_preset_path)
                        st.success(f"预设已导入: {imported_path}")
                        
                        # 删除临时文件
                        import os
                        os.unlink(temp_preset_path)
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"导入预设失败: {str(e)}")
    
    # 配置参数部分
    with st.expander("配置参数", expanded=True):
        # 核心配置参数
        st.subheader("核心配置")
        dataset_constructor.image_directory = st.text_input(
            "图片目录",
            value=dataset_constructor.image_directory,
            help="设置图片所在的目录路径"
        )
        
        dataset_constructor.image_path_prefix = st.text_input(
            "图片路径前缀",
            value=dataset_constructor.image_path_prefix,
            help="图片路径的前缀，用于生成最终的图片URL"
        )
        
        # 模型配置
        st.subheader("模型配置")
        col1, col2 = st.columns([1, 1])
        with col1:
            dataset_constructor.model_type = st.selectbox(
                "模型类型",
                ["multimodal", "llm"],
                index=["multimodal", "llm"].index(dataset_constructor.model_type),
                help="选择模型类型：multimodal（多模态）或llm（纯文本）"
            )
            
            dataset_constructor.dataset_type = st.selectbox(
                "数据集类型",
                ["test", "train"],
                index=["test", "train"].index(dataset_constructor.dataset_type),
                help="选择数据集类型：test（测试集）或train（训练集）"
            )
        
        with col2:
            # 添加启用多图片输入选项
            enable_multiple_images = st.checkbox(
                "启用多图片输入",
                value=dataset_constructor.max_images > 1 or dataset_constructor.process_multiple_blocks or dataset_constructor.group_by_subdirectory,
                help="是否需要在单条数据中添加多张图片"
            )
            
            if enable_multiple_images:
                dataset_constructor.max_images = st.number_input(
                    "最大图片数",
                    min_value=1,
                    max_value=100,
                    value=max(1, dataset_constructor.max_images),
                    help="每条数据中最多包含的图片数量，0表示无限制"
                )
            else:
                dataset_constructor.max_images = 1
                st.caption("当前设置为单图片输入模式")
        
        # 多图片处理配置（仅在启用多图片输入时显示）
        if enable_multiple_images:
            st.subheader("多图片处理配置")
            col1, col2 = st.columns([1, 1])
            with col1:
                dataset_constructor.process_multiple_blocks = st.checkbox(
                    "处理多块图片",
                    value=dataset_constructor.process_multiple_blocks,
                    help="是否处理多个街区的图片，每个街区作为一组"
                )
            
            with col2:
                dataset_constructor.group_by_subdirectory = st.checkbox(
                    "按子目录分组",
                    value=dataset_constructor.group_by_subdirectory,
                    help="是否按子目录分组图片，每个子目录作为一组"
                )
        else:
            dataset_constructor.process_multiple_blocks = False
            dataset_constructor.group_by_subdirectory = False
        
        # 内容提取配置
        st.subheader("内容提取配置")
        dataset_constructor.enable_content_extraction = st.checkbox(
            "启用内容提取",
            value=dataset_constructor.enable_content_extraction,
            help="是否从外部数据源中提取内容，用于组合生成用户提示词"
        )
        
        if dataset_constructor.enable_content_extraction:
            # 数据源说明
            st.info("内容提取说明：- JSON提取：从JSON文件的messages字段中提取user或assistant的内容- Excel提取：从Excel文件的指定列中提取内容")
            
            dataset_constructor.data_source = st.selectbox(
                "数据源类型",
                ["excel", "json"],
                index=0 if dataset_constructor.data_source == "excel" else 1,
                help="选择内容提取的数据源类型"
            )
            
            # 根据数据源显示不同的配置
            if dataset_constructor.data_source == "json":
                st.subheader("JSON内容提取设置")
                dataset_constructor.json_extraction_source = st.selectbox(
                    "提取来源",
                    ["assistant", "user", "both"],
                    index=["assistant", "user", "both"].index(dataset_constructor.json_extraction_source),
                    help="从JSON的messages字段中提取哪个角色的内容"
                )
                
                dataset_constructor.extract_json_only_from_markdown = st.checkbox(
                    "仅从Markdown中提取JSON",
                    value=dataset_constructor.extract_json_only_from_markdown,
                    help="是否仅从Markdown格式的代码块中提取JSON内容"
                )
            else:  # excel
                st.subheader("Excel内容提取设置")
                dataset_constructor.excel_extraction_source = st.selectbox(
                    "提取导向",
                    ["assistant", "user", "both"],
                    index=["assistant", "user", "both"].index(dataset_constructor.excel_extraction_source),
                    help="从Excel中提取哪种类型的内容"
                )
        else:
            dataset_constructor.data_source = "default"
            st.caption("当前设置为默认模式，不提取外部内容")
    
    # 高级配置参数（仅在需要时显示）
    show_advanced = dataset_constructor.enable_content_extraction or dataset_constructor.data_source != "default"
    if show_advanced:
        with st.expander("高级配置", expanded=False):
            if dataset_constructor.data_source == "excel":
                # Excel读取设置
                st.subheader("Excel读取设置")
                st.write("根据提取导向，仅显示需要的列设置")
                
                # 基础设置
                dataset_constructor.excel_file_path = st.text_input(
                    "Excel文件路径",
                    value=dataset_constructor.excel_file_path,
                    help="设置Excel文件的路径"
                )
                
                dataset_constructor.excel_image_name_column = st.text_input(
                    "图片名列",
                    value=dataset_constructor.excel_image_name_column,
                    help="Excel中包含图片名称的列名，用于关联图片和内容"
                )
                
                # 根据提取导向显示相应的列设置
                extraction_guide = dataset_constructor.excel_extraction_source
                
                if extraction_guide in ["user", "both"]:
                    dataset_constructor.user_excel_column = st.text_input(
                        "user内容列",
                        value=dataset_constructor.user_excel_column,
                        help="Excel中包含user内容的列名，将被提取用于生成用户提示词"
                    )
                
                if extraction_guide in ["assistant", "both"]:
                    dataset_constructor.assistant_excel_column = st.text_input(
                        "assistant内容列",
                        value=dataset_constructor.assistant_excel_column,
                        help="Excel中包含assistant内容的列名，将被提取用于生成训练数据"
                    )
            elif dataset_constructor.data_source == "json":
                # JSON读取设置
                st.subheader("JSON读取设置")
                st.write("从JSON文件中提取内容的字段配置")
                
                dataset_constructor.json_file_path = st.text_input(
                    "JSON文件路径",
                    value=dataset_constructor.json_file_path,
                    help="设置JSON文件的路径"
                )
                
                # 图片相关配置
                st.write("### 图片相关配置")
                dataset_constructor.json_image_name_field = st.text_input(
                    "图片数组字段",
                    value=dataset_constructor.json_image_name_field,
                    help="JSON中包含图片路径数组的字段名"
                )
                
                # 消息相关配置
                st.write("### 消息相关配置")
                dataset_constructor.json_messages_field = st.text_input(
                    "消息数组字段",
                    value=dataset_constructor.json_messages_field,
                    help="JSON中包含对话消息数组的字段名"
                )
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    dataset_constructor.json_role_field = st.text_input(
                        "角色字段",
                        value=dataset_constructor.json_role_field,
                        help="消息中包含角色（user/assistant）的字段名"
                    )
                
                with col2:
                    dataset_constructor.json_content_field = st.text_input(
                        "内容字段",
                        value=dataset_constructor.json_content_field,
                        help="消息中包含实际内容的字段名"
                    )
    
    # 输出配置
    with st.expander("输出配置", expanded=True):
        st.subheader("输出设置")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            dataset_constructor.output_file_path = st.text_input(
                "输出文件路径",
                value=dataset_constructor.output_file_path,
                help="设置输出文件的路径，支持{street_number}和{dataset_type}变量"
            )
        
        with col2:
            dataset_constructor.include_label_in_output = st.checkbox(
                "在输出中包含标签",
                value=dataset_constructor.include_label_in_output,
                help="是否在输出结果中新增label字段"
            )
            
            if dataset_constructor.include_label_in_output:
                dataset_constructor.json_image_name_source = st.selectbox(
                    "JSON图片名来源",
                    ["path", "label"],
                    index=["path", "label"].index(dataset_constructor.json_image_name_source),
                    help="选择JSON图片名的来源：path（来自images.path）或label（来自独立的label字段）"
                )
                
                dataset_constructor.json_label_field = st.text_input(
                    "JSON标签字段",
                    value=dataset_constructor.json_label_field,
                    help="JSON中独立的label字段名"
                )
    
    # 提示词组合配置
    with st.expander("提示词组合配置", expanded=True):
        st.subheader("系统提示词")
        dataset_constructor.system_content = st.text_area(
            "系统提示词",
            value=dataset_constructor.system_content,
            help="系统提示词，用于指导模型生成内容",
            height=200
        )
        
        # 根据是否启用内容提取，显示不同的用户提示词配置
        if dataset_constructor.enable_content_extraction:
            # 启用内容提取时，显示提示词组合配置，不显示默认提示词
            st.subheader("提示词组合配置")
            st.write("当启用内容提取时，用户提示词将由提取的内容与前后缀组合生成")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                dataset_constructor.user_content_prefix = st.text_area(
                    "提取内容前缀",
                    value=dataset_constructor.user_content_prefix,
                    help="添加在提取内容前面的文本",
                    height=100
                )
                
                dataset_constructor.user_content_suffix = st.text_area(
                    "提取内容后缀",
                    value=dataset_constructor.user_content_suffix,
                    help="添加在提取内容后面的文本",
                    height=100
                )
            
            # 只有启用多图片输入时，才显示提取内容的前缀、后缀和分隔符
            if enable_multiple_images:
                with col2:
                    st.write("多图片内容组合配置")
                    dataset_constructor.extracted_content_prefix = st.text_area(
                        "单张图片内容前缀",
                        value=dataset_constructor.extracted_content_prefix,
                        help="添加在每张图片提取内容前面的文本",
                        height=100
                    )
                    
                    dataset_constructor.extracted_content_suffix = st.text_area(
                        "单张图片内容后缀",
                        value=dataset_constructor.extracted_content_suffix,
                        help="添加在每张图片提取内容后面的文本",
                        height=100
                    )
                    
                    dataset_constructor.extracted_content_separator = st.text_area(
                        "图片内容分隔符",
                        value=dataset_constructor.extracted_content_separator,
                        help="多张图片提取内容之间的分隔符",
                        height=100
                    )
        else:
            # 未启用内容提取时，只显示默认提示词
            st.subheader("用户提示词")
            dataset_constructor.user_content_default = st.text_area(
                "用户提示词默认内容",
                value=dataset_constructor.user_content_default,
                help="用户提示词的默认内容",
                height=200
            )
    
    # 预览和运行按钮
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("预览数据集", type="secondary", use_container_width=True):
            with st.spinner("正在预览数据集..."):
                try:
                    # 构建数据集
                    dataset_result = dataset_constructor.build_dataset()
                    
                    # 预览结果
                    preview_data = dataset_constructor.preview_dataset(dataset_result)
                    
                    st.success("数据集预览成功！")
                    st.subheader(f"预览数据（共 {len(preview_data)} 条示例）")
                    
                    # 使用折叠面板展示每个示例的详细信息
                    for i, entry in enumerate(preview_data):
                        # 使用容器替代expander，避免嵌套expander错误
                        with st.container(border=True):
                            st.subheader(f"示例 {i+1} 详情")
                            # 使用格式化方法展示详细内容
                            formatted_preview = dataset_constructor.format_preview_entry(entry)
                            st.markdown(formatted_preview)
                            

                except Exception as e:
                    st.error(f"预览失败: {str(e)}")
                    st.exception(e)
    
    with col2:
        if st.button("开始构建数据集", type="primary", use_container_width=True, key="build_dataset_btn"):
            with st.spinner("正在构建数据集..."):
                try:
                    # 确保获取最新的配置参数
                    # 重新保存实例到session_state，确保获取最新参数
                    st.session_state.dataset_constructor = dataset_constructor
                    
                    # 构建数据集
                    dataset_result = dataset_constructor.build_dataset()
                    
                    # 保存数据集
                    dataset_constructor.save_dataset(dataset_result)
                    
                    # 验证文件是否存在
                    output_path = dataset_result['output_path']
                    if os.path.exists(output_path):
                        st.success(f"JSON数据集已生成: {output_path}")
                        st.info(f"文件大小: {os.path.getsize(output_path)}字节")
                    else:
                        st.error(f"数据集文件生成失败，文件未找到: {output_path}")
                        
                    st.info(f"内容提取状态: {'启用' if dataset_constructor.enable_content_extraction else '禁用'}")
                    
                    # 验证排序结果
                    if dataset_result["result"] and "images" in dataset_result["result"][0]:
                        st.subheader("图片顺序示例（前3张）:")
                        for img_path in dataset_result["result"][0]["images"][:3]:
                            st.write(f"- {img_path}")
                    
                    # 下载链接
                    if os.path.exists(output_path):
                        with open(output_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="下载生成的JSON文件",
                                data=f,
                                file_name=os.path.basename(output_path),
                                mime="application/json",
                                use_container_width=True
                            )
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.exception(e)

# 实施举措提取功能
elif app_mode == "实施举措提取":
    # 定义默认值，确保变量在整个功能中都能访问
    image_basename_col = "image_basename"
    strategies_col = "优化策略"
    
    # 示例展示区 - 点击展开查看示例
    with st.expander("查看示例", expanded=False):
        tab1, tab2 = st.tabs(["输入示例", "输出示例"])
        
        with tab1:
            st.subheader("输入示例")
            st.code('''{
  "优化策略列表": ["优化步行网络结构", "提升步行环境品质", "完善步行配套设施"]
}''', language="json")
        
        with tab2:
            st.subheader("输出示例")
            st.code('''# 优化策略及实施举措

## 1. 优化步行网络结构

### 1. 构建连续完整的步行网络
构建连续完整的步行网络，确保行人可以便捷地到达目的地，减少步行中断和绕行。''', language="markdown")

    # 核心功能区 - 文件上传（置于主体位置）
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("上传大模型输出文件或Excel表格")
        uploaded_file = st.file_uploader(
            "选择JSON、JSONL或Excel文件",
            type=["json", "jsonl", "xlsx"],
            help="支持上传JSON、JSONL格式的大模型输出文件，或Excel表格作为数据源，建议文件大小不超过10MB",
            label_visibility="collapsed"
        )
        
        # 显示文件信息
        if uploaded_file:
            st.info(f"已上传: {uploaded_file.name}")
        else:
            st.warning("请上传大模型输出文件或Excel表格")

    with col2:
        st.subheader("上传实施举措表格（可选）")
        uploaded_excel = st.file_uploader(
            "选择Excel表格",
            type=["xlsx"],
            help="包含优化策略、实施举措和实施举措内涵的Excel表格",
            label_visibility="collapsed"
        )
        
        # 设置默认Excel路径 - 使用基于项目根目录的绝对路径
        default_excel_path = os.path.join(PROJECT_ROOT, "docs", "知识图谱梳理表格 (1).xlsx")
        
        # 显示当前使用的Excel表格
        if uploaded_excel:
            st.info(f"使用上传的表格: {uploaded_excel.name}")
        elif os.path.exists(default_excel_path):
            st.info(f"使用默认表格: {Path(default_excel_path).name}")
            st.caption(f"默认表格位置: {default_excel_path}")
        else:
            st.warning("未找到默认表格，请上传自定义实施举措表格")
    
    # 高级设置区 - 可调整的输出设置
    with st.expander("高级设置", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 自定义输出目录
            output_dir = st.text_input(
                "输出目录",
                value="output/implementation_measures",
                help="设置结果文件的保存目录"
            )
            st.caption("提示：您可以直接在输入框中输入目录路径，或在代码中修改默认路径")
        
        with col2:
            # 自定义文件名前缀
            filename_prefix = st.text_input(
                "文件名前缀",
                value="实施举措提取结果",
                help="设置结果文件的文件名前缀"
            )
    
    # Excel数据源配置
    with st.expander("Excel数据源配置", expanded=False):
        st.write("当上传Excel表格作为数据源时，需要配置以下选项：")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            image_basename_col = st.text_input(
                "图片名称列",
                value=image_basename_col,
                help="Excel表格中包含图片名称的列名"
            )
        
        with col2:
            strategies_col = st.text_input(
                "优化策略列表列",
                value=strategies_col,
                help="Excel表格中包含优化策略列表的列名"
            )

    # 处理按钮 - 突出显示
    st.empty()  # 添加空行
    if st.button("开始处理", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("❌ 请先上传大模型输出文件")
        else:
            with st.spinner("正在处理文件..."):
                try:
                    # 读取上传的文件信息
                    file_name = uploaded_file.name
                    file_extension = Path(file_name).suffix.lower()
                    
                    # 确定使用的Excel路径
                    excel_path = uploaded_excel if uploaded_excel else default_excel_path
                    
                    # 处理文件
                    if file_extension == ".jsonl":
                        # 处理JSONL文件 - 需要先保存到临时文件
                        file_content = uploaded_file.getvalue().decode("utf-8")
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
                            f.write(file_content)
                            temp_file_path = f.name
                        
                        try:
                            json_result, markdown_result, excel_result_df = measures_extractor.process_jsonl_file(
                                temp_file_path, excel_path
                            )
                        finally:
                            # 删除临时文件
                            import os
                            os.unlink(temp_file_path)
                    elif file_extension == ".xlsx":
                        # 处理Excel文件 - 直接使用字节流
                        json_result, markdown_result, excel_result_df = measures_extractor.process_excel_file(
                            uploaded_file.getvalue(), excel_path, image_basename_col, strategies_col
                        )
                    else:
                        # 处理JSON文件 - 解码为UTF-8
                        file_content = uploaded_file.getvalue().decode("utf-8")
                        json_result, markdown_result, excel_result_df = measures_extractor.process_file(
                            file_content, excel_path
                        )
                    
                    # 生成文件名（基于当前时间）
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    base_name = f"{filename_prefix}_{timestamp}"
                    
                    # 保存结果到指定目录，单独建一个文件夹
                    # 确保输出目录基于项目根目录
                    if not os.path.isabs(output_dir):
                        save_folder = os.path.join(PROJECT_ROOT, output_dir, base_name)
                    else:
                        save_folder = os.path.join(output_dir, base_name)
                    os.makedirs(save_folder, exist_ok=True)
                    
                    # 保存结果
                    json_file_path = os.path.join(save_folder, f"{base_name}.json")
                    markdown_file_path = os.path.join(save_folder, f"{base_name}.md")
                    excel_file_path = os.path.join(save_folder, f"{base_name}.xlsx")
                    
                    measures_extractor.save_result(json_result, json_file_path, "json")
                    measures_extractor.save_result(markdown_result, markdown_file_path, "markdown")
                    excel_result_df.to_excel(excel_file_path, index=False, engine="openpyxl")
                    
                    # 结果展示区域 - 简化设计
                    st.success(f"处理完成！结果已保存到: {save_folder}")
                    
                    # 结果展示
                    with st.expander("查看结果", expanded=True):
                        tab1, tab2 = st.tabs(["JSON格式", "Markdown格式"])
                        
                        with tab1:
                            # 使用容器和滚动条展示大量JSON数据
                            json_container = st.container(height=500, border=True)
                            with json_container:
                                st.json(json_result)
                        
                        with tab2:
                            # 使用容器和滚动条展示大量Markdown数据
                            md_container = st.container(height=500, border=True)
                            with md_container:
                                st.markdown(markdown_result)
                    
                    # 下载区域 - 简化设计
                    st.subheader("下载结果")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        with open(json_file_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="下载JSON结果",
                                data=f,
                                file_name=f"{base_name}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                    
                    with col2:
                        with open(markdown_file_path, "r", encoding="utf-8") as f:
                            st.download_button(
                                label="下载Markdown结果",
                                data=f,
                                file_name=f"{base_name}.md",
                                mime="text/markdown",
                                use_container_width=True
                            )
                    
                    with col3:
                        with open(excel_file_path, "rb") as f:
                            st.download_button(
                                label="下载Excel结果",
                                data=f,
                                file_name=f"{base_name}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.exception(e)

    # 结果文件上传区 - 用于上传和展示其他输出结果文件
    with st.expander("上传结果文件", expanded=False):
        st.write("上传并查看其他输出结果文件：")
        
        # 上传JSON结果文件
        uploaded_json_result = st.file_uploader(
            "上传JSON结果文件",
            type=["json"],
            help="上传JSON格式的结果文件",
            key="json_result_uploader_measures"
        )
        
        # 上传Markdown结果文件
        uploaded_md_result = st.file_uploader(
            "上传Markdown结果文件",
            type=["md"],
            help="上传Markdown格式的结果文件",
            key="md_result_uploader_measures"
        )
        
        # 展示上传的JSON结果
        if uploaded_json_result:
            st.subheader("上传的JSON结果")
            try:
                json_content = json.load(uploaded_json_result)
                # 使用容器和滚动条展示大量JSON数据
                json_container = st.container(height=500, border=True)
                with json_container:
                    st.json(json_content)
            except json.JSONDecodeError:
                st.error("无法解析JSON文件，请检查文件格式")
        
        # 展示上传的Markdown结果
        if uploaded_md_result:
            st.subheader("上传的Markdown结果")
            try:
                md_content = uploaded_md_result.read().decode("utf-8")
                # 使用容器和滚动条展示大量Markdown数据
                md_container = st.container(height=500, border=True)
                with md_container:
                    st.markdown(md_content)
            except UnicodeDecodeError:
                st.error("无法读取Markdown文件，请检查文件编码")

# 命令行记录功能
elif app_mode == "命令行记录":
    st.subheader("命令行记录")
    st.write("此功能用于记录和管理命令行代码，支持添加、编辑、删除、搜索和导出记录。")
    
    # 添加新命令行记录
    with st.expander("添加新命令行记录", expanded=True):
        new_command = st.text_area(
            "输入命令行代码",
            height=100,
            placeholder="请输入命令行代码，例如：\nCUDA_VISIBLE_DEVICES=0,1 swift infer \\\n--model autodl-tmp/qwen3_vl_32b \\\n--model_type qwen3_vl \\\n--val_dataset autodl-tmp/1217_pleasurability_pics200/1217_训练集转换_final_training_dataset_test.json \\\n--infer_backend vllm \\\n--vllm_tensor_parallel_size 2 \\\n--stream False"
        )
        
        if st.button("添加记录", type="primary", use_container_width=True):
            if new_command.strip():
                # 添加记录
                command_manager.add_record(new_command)
                st.success("命令行记录已添加！")
                # 清空输入框
                st.rerun()
            else:
                st.error("请输入命令行代码！")
    
    # 显示命令行记录
    st.subheader("命令行记录列表")
    records = command_manager.get_records()
    
    # 添加搜索功能
    search_query = st.text_input("搜索命令行记录", placeholder="输入关键词进行搜索")
    
    # 过滤记录
    filtered_records = records
    if search_query:
        filtered_records = [record for record in records if search_query.lower() in record["command"].lower()]
    
    # 统计信息
    st.caption(f"共找到 {len(filtered_records)} 条记录")
    
    if not filtered_records:
        st.info("暂无命令行记录")
    else:
        # 添加导出功能
        if st.button("导出所有记录", type="secondary"):
            # 导出为JSON文件
            import json
            export_data = {
                "records": filtered_records,
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.download_button(
                label="下载命令行记录",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"command_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # 显示每条记录
        for record in filtered_records:
            with st.container(border=True):
                # 记录头部
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**创建时间：** {record['created_at']}")
                with col2:
                    if st.button("编辑", key=f"edit_{record['id']}", use_container_width=True):
                        st.session_state[f"editing_{record['id']}"] = True
                with col3:
                    if st.button("删除", key=f"delete_{record['id']}", use_container_width=True, type="secondary"):
                        command_manager.delete_record(record["id"])
                        st.rerun()
                
                # 显示或编辑命令内容
                if st.session_state.get(f"editing_{record['id']}", False):
                    edited_command = st.text_area(
                        "编辑命令行代码",
                        value=record["command"],
                        height=100,
                        key=f"edit_area_{record['id']}"
                    )
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("保存", key=f"save_{record['id']}", type="primary", use_container_width=True):
                            if edited_command.strip():
                                command_manager.update_record(record["id"], edited_command)
                                st.session_state[f"editing_{record['id']}"] = False
                                st.rerun()
                    with col2:
                        if st.button("取消", key=f"cancel_{record['id']}", type="secondary", use_container_width=True):
                            st.session_state[f"editing_{record['id']}"] = False
                            st.rerun()
                else:
                    st.code(record["command"], language="bash")
                    # 添加复制按钮
                    if st.button("复制命令", key=f"copy_{record['id']}", type="secondary"):
                        st.session_state["copied_command"] = record["command"]
                        st.success("命令已复制到剪贴板！")

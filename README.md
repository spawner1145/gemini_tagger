# Gemini 标签生成器

这是一个基于 Google Gemini API 的工具，用于为指定目录中的图片和视频文件生成描述性标签。支持异步处理、多模态输入（图片和视频），并提供 Gradio 前端界面。

## 功能

* **文件支持** ：处理 **.jpg**, **.jpeg**, **.png** 图片和 **.mp4**, **.mov**, **.avi** 视频。
* **标签生成** ：通过 Gemini API 分析文件内容，生成描述和标签。
* **前端界面** ：使用 Gradio 提供交互式UI，支持自定义参数。
* **状态检查** ：自动等待视频文件处理完成（从 **PROCESSING** 到 **ACTIVE**）。

## 安装依赖

```
pip install httpx gradio
```

1. **准备环境** ：

* 确保 Python 版本为 3.7 或更高。
* 获取 Google Gemini API 密钥（在 [Google AI Studio](https://aistudio.google.com/app/apikey?hl=zh-cn) 创建）。

## 使用方法

1. **准备文件** ：

* 创建 **to_be_tagged** 目录，将图片或视频文件放入其中。

**运行程序** ：

```
   python gemini_tagger.py
```

**访问界面** ：

* 打开浏览器，访问 Gradio 提供的本地地址，默认 **http://127.0.0.1:7860**

**配置参数** ：

* **目录路径** ：默认 **./to_be_tagged**
* **系统提示** ：例如“作为图片和视频分析专家”
* **用户提示** ：例如“描述内容并生成适当的标签”
* **API端点** ：你可以填反代，默认 **https://generativelanguage.googleapis.com**
* **API密钥** ：输入你的 Gemini API 密钥
* **代理（可选）** ：例如 **http://127.0.0.1:7890**
* **模型版本** ：选择 Gemini 2.0 系列模型（如 **gemini-2.0-flash-001**）
* **超时时间（可选）** ：输入秒数（如 **60**），留空表示无限等待
* 点击“处理文件”按钮，查看实时结果

## 注意事项

* **API密钥权限** ：确保密钥已启用“Generative Language API”和“Cloud Storage”服务。
* **文件状态** ：视频上传后需等待处理完成（**PROCESSING** -> **ACTIVE**），超时可能导致失败。
* **模型支持** ：选择的多模态模型需支持视频/图片处理。
* **调试** ：检查后端日志以定位问题。

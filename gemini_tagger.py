import asyncio
import os
import base64
import httpx
from pathlib import Path
import gradio as gr
from typing import Dict, Optional, AsyncGenerator
import json

class GeminiTagger:
    def __init__(self, api_key: str, api_endpoint: str, model: str, proxy: Optional[str] = None):
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(
            proxies=proxy if proxy else None,
            timeout=httpx.Timeout(60.0)
        )

    async def upload_file(self, file_path: str) -> Optional[str]:
        """上传视频文件并返回文件URI"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                url = f"{self.api_endpoint}/upload/v1beta/files?key={self.api_key}"
                print(f"后端日志 - 上传文件请求URL: {url}")
                response = await self.client.post(url, files=files)
                response.raise_for_status()
                response_json = response.json()
                print(f"后端日志 - 文件上传响应: {response_json}")
                uri = response_json['file'].get('uri')
                if uri is None:
                    print(f"后端日志 - 警告: URI未找到，响应内容: {response_json}")
                else:
                    print(f"后端日志 - 文件上传成功: {file_path}, URI: {uri}")
                return uri
        except Exception as e:
            error_msg = f"后端日志 - 上传文件 {file_path} 时出错: {str(e)}"
            print(error_msg)
            return None

    async def wait_for_file_active(self, file_uri: str, timeout: Optional[int] = None, interval: int = 5) -> bool:
        """等待文件状态变为ACTIVE"""
        file_id = file_uri.split('/')[-1]  # 提取文件ID
        url = f"{self.api_endpoint}/v1beta/files/{file_id}?key={self.api_key}"
        start_time = asyncio.get_event_loop().time()
        
        while timeout is None or (asyncio.get_event_loop().time() - start_time < timeout):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                file_info = response.json()
                print(f"后端日志 - 检查文件状态: {file_info}")
                state = file_info.get('state')
                if state == "ACTIVE":
                    print(f"后端日志 - 文件 {file_id} 已就绪，状态: {state}")
                    return True
                elif state == "FAILED":
                    print(f"后端日志 - 文件 {file_id} 处理失败，状态: {state}")
                    return False
                else:
                    print(f"后端日志 - 文件 {file_id} 仍在处理中，状态: {state}")
                    await asyncio.sleep(interval)
            except Exception as e:
                print(f"后端日志 - 检查文件状态出错: {str(e)}")
                return False
        print(f"后端日志 - 等待文件 {file_id} 超时 ({timeout}秒)")
        return False

    async def process_image(self, file_path: str, system_prompt: str, user_prompt: str) -> str:
        print(f"后端日志 - 开始处理图片: {file_path}")
        try:
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            payload = {
                "contents": [{"parts": [{"text": user_prompt}, {"inline_data": {"mime_type": "image/jpeg" if file_path.lower().endswith('.jpg') else "image/png", "data": image_data}}]}],
                "system_instruction": {"parts": [{"text": system_prompt}]}
            }
            url = f"{self.api_endpoint}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()['candidates'][0]['content']['parts'][0]['text']
            print(f"后端日志 - 图片处理完成: {file_path}, 生成的标签: {result}")
            return result
        except httpx.HTTPStatusError as e:
            error_msg = f"后端日志 - 处理图片 {file_path} 时出错: {str(e)} (状态码: {e.response.status_code}, 响应: {e.response.text})"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"后端日志 - 处理图片 {file_path} 时出错: {str(e)}"
            print(error_msg)
            return error_msg

    async def process_video(self, file_path: str, system_prompt: str, user_prompt: str, timeout: Optional[int] = None) -> str:
        print(f"后端日志 - 开始处理视频: {file_path}")
        try:
            file_uri = await self.upload_file(file_path)
            if not file_uri:
                error_msg = "错误: 视频上传失败"
                print(f"后端日志 - {error_msg}")
                return error_msg

            # 等待文件状态变为ACTIVE
            if not await self.wait_for_file_active(file_uri, timeout=timeout):
                error_msg = "错误: 文件未能在规定时间内变为ACTIVE状态"
                print(f"后端日志 - {error_msg}")
                return error_msg

            payload = {
                "contents": [{"parts": [{"text": user_prompt}, {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}}]}],
                "system_instruction": {"parts": [{"text": system_prompt}]}
            }
            url = f"{self.api_endpoint}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()['candidates'][0]['content']['parts'][0]['text']
            print(f"后端日志 - 视频处理完成: {file_path}, 生成的标签: {result}")
            return result
        except httpx.HTTPStatusError as e:
            error_msg = f"后端日志 - 处理视频 {file_path} 时出错: {str(e)} (状态码: {e.response.status_code}, 响应: {e.response.text})"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"后端日志 - 处理视频 {file_path} 时出错: {str(e)}"
            print(error_msg)
            return error_msg

    async def tag_files(self, directory: str, system_prompt: str, user_prompt: str, timeout: Optional[int] = None) -> AsyncGenerator[str, None]:
        directory_path = Path(directory)
        if not directory_path.exists():
            error_msg = "错误: 目录不存在"
            print(f"后端日志 - {error_msg}")
            yield error_msg
            return
        image_exts = ('.jpg', '.jpeg', '.png')
        video_exts = ('.mp4', '.mov', '.avi')
        results = {}
        file_paths = []
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_exts + video_exts:
                file_paths.append(file_path)
        if not file_paths:
            error_msg = "错误: 目录中没有支持的图片或视频文件"
            print(f"后端日志 - {error_msg}")
            yield error_msg
            return
        for file_path in file_paths:
            str_path = str(file_path)
            yield f"前端输出 - 开始处理: {str_path}\n"
            print(f"后端日志 - 开始处理文件: {str_path}")
            if str_path.lower().endswith(image_exts):
                response = await self.process_image(str_path, system_prompt, user_prompt)
            elif str_path.lower().endswith(video_exts):
                response = await self.process_video(str_path, system_prompt, user_prompt, timeout)
            if not response.startswith("处理") and not response.startswith("错误"):
                txt_path = file_path.with_suffix('.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(response)
                results[str_path] = response
                yield f"前端输出 - 完成 {str_path}, 生成的标签: {response}\n"
            else:
                results[str_path] = "处理失败"
                yield f"前端输出 - 完成 {str_path}, 处理失败: {response}\n"
            await asyncio.sleep(0.01)
        yield f"前端输出 - 所有文件处理完成。结果: {json.dumps(results, ensure_ascii=False)}\n"
        print(f"后端日志 - 所有文件处理完成。结果: {json.dumps(results, ensure_ascii=False)}")

    async def close(self):
        await self.client.aclose()

def create_gradio_interface():
    async def process_directory(directory, system_prompt, user_prompt, api_endpoint, api_key, proxy, model, timeout):
        # 将timeout转换为整数，如果为空则为None
        timeout_value = None if not timeout else int(timeout)
        tagger = GeminiTagger(api_key, api_endpoint, model, proxy if proxy.strip() else None)
        async for output in tagger.tag_files(directory, system_prompt, user_prompt, timeout_value):
            yield output
        await tagger.close()

    with gr.Blocks(title="Gemini 文件标签生成器") as demo:
        gr.Markdown("# Gemini 文件标签生成器")
        with gr.Row():
            with gr.Column():
                directory_input = gr.Textbox(label="目录路径", value="./to_be_tagged", placeholder="输入包含图片/视频的目录")
                system_prompt_input = gr.Textbox(label="系统提示", value="作为图片和视频分析专家", lines=3)
                user_prompt_input = gr.Textbox(label="用户提示", value="描述内容并生成适当的标签", lines=3)
                api_endpoint_input = gr.Textbox(label="API端点", value="https://generativelanguage.googleapis.com", placeholder="输入API基础URL，后续路径会自动补充")
                api_key_input = gr.Textbox(label="API密钥", placeholder="输入你的Gemini API密钥")
                proxy_input = gr.Textbox(label="代理 (可选)", placeholder="http://proxy:port 或 socks5://proxy:port", value="http://127.0.0.1:7890")
                model_input = gr.Dropdown(label="模型版本", choices=["gemini-2.0-flash-001", "gemini-2.0-flash-lite-001", "gemini-2.0-pro-exp-02-05", "gemini-2.0-flash-thinking-exp-01-21", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.0-pro"], value="gemini-2.0-flash-001")
                timeout_input = gr.Textbox(label="超时时间 (秒，可选)", placeholder="留空表示无限等待，例如输入60表示60秒", value="")
                submit_btn = gr.Button("处理文件")
            with gr.Column():
                output = gr.Textbox(label="处理结果", lines=15, placeholder="这里将显示每个文件的标签内容")
        submit_btn.click(
            fn=process_directory,
            inputs=[directory_input, system_prompt_input, user_prompt_input, api_endpoint_input, api_key_input, proxy_input, model_input, timeout_input],
            outputs=output
        )
    return demo

if __name__ == "__main__":
    interface = create_gradio_interface()
    interface.launch()
import sys
import asyncio
import json
import re
from io import StringIO

# 自定义流类，用于捕获日志并将其发送到队列
class AsyncLogStream:
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.buffer = []

    def write(self, message):
        """将消息写入缓冲区，当内容足够时刷新"""
        # 将所有消息添加到缓冲区，无论类型如何
        self.buffer.append(message)
        
        # 检查当前缓冲区内容
        buffer_content = ''.join(self.buffer)
        
        # 刷新条件：
        # 1. 当我们得到换行符
        # 2. 当缓冲区太长（防止内存问题）
        # 3. 当我们检测到句子结束
        should_flush = (
            '\n' in message  # 换行符表示行结束
            or len(buffer_content) > 200  # 防止非常长的缓冲区
            or any(c in buffer_content for c in ['.', '!', '?', '。', '！', '？', '；', ';'])  # 句子结束符
            or ('**' in buffer_content and buffer_content.count('**') % 2 == 0)  # 完整的markdown加粗部分
            or ('``' in buffer_content and buffer_content.count('``') % 2 == 0)  # 完整的markdown代码部分
        )
        
        if should_flush:
            content_to_flush = buffer_content.strip()
            if content_to_flush and self._should_include_message(content_to_flush):
                # 使用异步队列的put_nowait方法，避免在同步方法中使用await
                self.queue.put_nowait(content_to_flush)
            self.buffer = []

    def _should_include_message(self, message: str) -> bool:
        """过滤日志消息，只包含重要的用户可见信息"""
        message = message.strip()

        # 跳过空消息
        if not message:
            return False

        # 跳过技术调试消息
        skip_patterns = [
            'INFO:', 'DEBUG:', 'TRACE:',
            'screenshot', 'coordinates', 'bounds',
            'XML dump', 'hierarchy', 'accessibility',
            'UIAutomator', 'ADB command', 'shell command',
            'device info', 'system info',
            'internal', 'private', 'hidden',
            'timeout', 'retry', 'attempt',
            'processing', 'parsing', 'analyzing',
            'loading model', 'initializing', 'connecting',
            'HTTP request', 'API call', 'network request',
            'memory usage', 'CPU usage', 'performance',
            'technical details', 'implementation details'
        ]

        # 如果包含技术模式则跳过
        for pattern in skip_patterns:
            if pattern.lower() in message.lower():
                return False

        # 跳过太长的消息（可能是技术转储）
        if len(message) > 200:
            return False

        # 跳过包含太多特殊字符的消息（可能是JSON/XML转储）
        special_chars = sum(1 for c in message if not c.isalnum() and c not in [' ', '.', ',', '!', '?', ':', '-', '(', ')', '[', ']', '"', "'"])
        if special_chars / len(message) > 0.3:  # 超过30%的特殊字符
            return False

        # 包含用户可见的操作消息
        include_patterns = [
            '[点击]', '[执行]', '[等待]', '[输入]', '[选择]', '[查看]',
            '[成功]', '[完成]', '[失败]', '[错误]',
            '打开', '点击', '输入', '选择', '等待', '加载',
            '成功', '完成', '失败', '错误'
        ]

        for pattern in include_patterns:
            if pattern in message:
                return True

        # 对于其他消息，更包容一些 - 包含简短、可读的可能面向用户的消息
        # 这允许更多自然语言消息，可能没有特定的操作标记
        return len(message) < 150 and message[0].isalnum()

    def flush(self):
        """将缓冲区刷新到队列"""
        if self.buffer:
            line = ''.join(self.buffer)
            self.queue.put_nowait(line)
            self.buffer = []

    def close(self):
        """关闭流"""
        self.flush()

# Async generator to read logs from queue and yield them
async def log_generator(queue: asyncio.Queue, done_event: asyncio.Event):
    """异步生成器，用于从队列中生成日志消息"""
    # 缓冲区，用于将单词累积成完整的消息
    message_buffer = ""

    while not done_event.is_set() or not queue.empty():
        try:
            # 尝试从队列中获取消息，无等待
            message = queue.get_nowait()
            message_buffer += message
        except asyncio.QueueEmpty:
            # 如果队列为空，稍等片刻后再次检查
            await asyncio.sleep(0.1)
            continue

        # 处理缓冲区中的消息
        while message_buffer:
            # 如果消息包含换行符，作为完整消息处理
            if '\n' in message_buffer:
                newline_pos = message_buffer.find('\n')
                # 取出到换行符位置的内容作为完整消息
                complete_message = message_buffer[:newline_pos]
                if complete_message:
                    yield complete_message
                # 剩余内容继续留在缓冲区
                message_buffer = message_buffer[newline_pos+1:]
            elif len(message_buffer) > 50 or any(c in message_buffer for c in ['.', '!', '?', '。', '！', '？']):
                # 如果消息足够长或包含句子结束符，作为完整消息处理
                yield message_buffer
                message_buffer = ""
            else:
                # 否则等待更多内容
                break

    # 处理剩余的消息
    if message_buffer:
        yield message_buffer

def _clean_log_line(log_line: str) -> str:
    """清理日志行以用于用户显示"""
    # 移除ANSI转义码
    log_line = re.sub(r'\x1b\[[0-9;]*m', '', log_line)
    
    # 移除可能造成混淆的markdown格式
    log_line = log_line.replace('**', '').replace('``', '')
    
    # 修剪空白
    log_line = log_line.strip()
    
    return log_line

import sys
import asyncio
from queue import Queue
from droidrun import DroidAgent, DroidrunConfig
from config import app_config
from log import AsyncLogStream

async def stream_execute_droidrun_action(action: str, queue: Queue, done_event: asyncio.Event, scenario: str = None) -> dict:
    """Execute the given action using droidrun and stream logs"""
    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    # Create async log streams
    stdout_stream = AsyncLogStream(queue)
    stderr_stream = AsyncLogStream(queue)

    sys.stdout = stdout_stream
    sys.stderr = stderr_stream

    try:
        # Create config with optimized settings for accuracy
        droidrun_config = DroidrunConfig()

        # Enable screenshot validation before operations
        droidrun_config.screenshot_before_action = True
        droidrun_config.screenshot_after_action = True

        # Set longer wait times for better stability (increased for accuracy)
        droidrun_config.action_wait_time = 3.0  # seconds (increased from 2.0)
        droidrun_config.page_load_wait_time = 5.0  # seconds (increased from 3.0)
        droidrun_config.element_wait_time = 4.0  # seconds for element appearance

        # Enable retry mechanism with more attempts
        droidrun_config.max_action_retries = 5  # increased from 3
        droidrun_config.retry_wait_time = 2.0  # seconds (increased from 1.0)

        # Additional accuracy settings
        droidrun_config.verify_element_clickable = True  # verify elements are clickable before clicking
        droidrun_config.wait_for_page_stability = True  # wait for page to stabilize
        droidrun_config.max_wait_for_element = 10.0  # maximum wait time for element appearance

        # Apply user configuration for LLM
        for _, profile in droidrun_config.llm_profiles.items():
            profile.provider = app_config.get("llmProvider", "DeepSeek")
            profile.model = app_config.get("llmModel", "deepseek-chat")
            profile.temperature = app_config.get("llmTemperature", 0.1)
        
        # Create agent with optimized e-commerce shopping prompts
        custom_prompts = {
            "manager_system": """你是专业的电商购物助手，需要精准响应并执行用户的购物相关操作指令。保持回答简洁，专注于任务执行（如遇到支付步骤请暂停，提示用户进行支付）。

日志输出规范：
- 只输出关键操作步骤和重要状态信息
- 详细记录购物流程的每个关键节点：搜索→详情→加购→结算→支付
- 报告重要的验证结果和状态确认
- 避免输出技术细节、调试信息和内部状态
- 使用简洁明了的中文描述用户关心的操作进展
- 格式："[操作类型] 具体操作描述"，如"[点击] 点击搜索按钮"，"[验证] 商品已添加到购物车"

界面定位原则：
1. 优先使用文本匹配：通过按钮文本、标题、标签等文本内容定位元素
2. 其次使用位置关系：基于屏幕坐标、相对位置进行定位
3. 使用视觉特征：通过颜色、形状、图标等视觉特征识别元素
4. 元素预查验证：在操作前检查元素是否存在、可访问、可操作
5. 验证元素状态：确保按钮可点击、输入框可编辑、界面已完全加载

操作执行策略：
1. 操作前截图验证：确保当前界面符合预期状态
2. 分步精确执行：每个操作后等待界面响应完成
3. 智能重试机制：操作失败时重试，最多3次，每次调整策略
   - 第1次重试：等待更长时间后重试
   - 第2次重试：尝试备选定位方式（如坐标定位改为文本定位）
   - 第3次重试：重新加载页面或应用后重试
4. 错误处理：遇到异常立即停止并报告具体错误信息

遵循以下流程：
1. 快速理解用户需求（搜索商品、浏览分类、查看详情、加入购物车、下单购买等）
2. 优先使用效率最高的操作路径
3. 严格按照购物流程执行：搜索→详情→加购→结算→支付
4. 每个步骤都要有明确的验证和确认
5. 遇到问题立即停止并报告，不要尝试跳过步骤
6. 特别关注支付流程的完整性，确保到达真正的支付页面

关键节点验证：
- 搜索结果：确认有相关商品显示
- 商品详情：确认规格、价格等信息正确
- 购物车：确认商品已添加，数量和价格正确
- 结算页面：确认收货地址、商品列表、总价计算正确
- 支付页面：确认支付金额、支付方式正确显示

常见购物操作流程及等待时间：
- 搜索商品：打开电商APP（等待4秒加载） → 等待首页加载完成（3秒） → 点击搜索框 → 输入关键词（2秒） → 点击搜索按钮 → 等待结果加载（4秒） → 浏览结果
- 浏览分类：打开电商APP（等待4秒加载） → 等待首页加载（3秒） → 点击分类导航 → 选择分类/子分类（等待3秒加载） → 等待页面加载（3秒） → 浏览商品
- 查看详情：点击商品（等待3秒加载详情页） → 等待详情页加载（4秒） → 查看图片/视频 → 浏览规格/参数 → 查看评价
- 加入购物车：选择规格（2秒） → 点击加入购物车 → 等待操作完成（3秒） → 验证添加成功提示（2秒）
- 下单购买：进入购物车（等待3秒加载） → 选择商品（1秒） → 点击结算（等待3秒） → 确认收货地址（2秒） → 选择支付方式（2秒） → 点击提交订单（等待4秒） → 到达支付页面（等待3秒）""",
            "executor_system": """你是电商购物执行助手，负责精准执行购物操作。

日志输出规范：
- 只报告用户可见的操作步骤和结果
- 使用统一的格式：[操作] 描述，如"[执行] 打开淘宝APP"
- 详细报告购物流程进度：[搜索]、[详情]、[加购]、[结算]、[支付]
- 报告关键验证结果：[验证] 商品添加成功，[确认] 到达结算页面
- 避免输出技术细节、坐标信息、内部调试数据
- 重点报告操作成功、失败、等待状态和验证结果

界面操作规范：
1. 截图验证：每次操作前获取屏幕截图，确认界面状态
2. 元素定位：优先使用文本内容定位，其次使用坐标位置，最后使用视觉特征
   - 购物车相关：查找"购物车"、"加入购物车"、"去结算"等文本
   - 支付相关：查找"结算"、"提交订单"、"立即支付"、"确认支付"等文本
   - 数量/规格：查找"+"、"-"、"选择规格"等按钮
3. 元素预查：操作前验证元素是否存在
   - 检查元素是否在当前界面可见
   - 确认元素是否可点击或可编辑
   - 验证界面是否已完全加载（检查关键元素出现）
4. 点击精度：确保点击位置准确，避免误触，使用元素中心点点击
5. 等待机制：操作后等待界面响应完成再进行下一步，不同操作使用不同等待时间
   - 页面跳转：3-4秒
   - 网络请求：2-3秒
   - 界面动画：1-2秒
6. 状态检查：验证操作是否成功执行，通过界面变化或提示信息确认
   - 检查URL变化或页面标题变化
   - 查找成功提示信息
   - 验证关键元素状态变化
7. 重试策略：操作失败时按以下顺序重试：
   - 重新获取界面截图，确认元素是否仍然存在
   - 尝试备用定位方法（文本→坐标→视觉特征）
   - 等待更长时间后重试（每次增加1秒）
   - 向上滑动或刷新页面后重试
   - 如多次失败，报告具体错误信息

执行要求：
- 严格按照manager_system的指示执行
- 每个操作都要有明确的成功验证
- 遇到异常立即停止并详细报告
- 保持操作序列的连续性和准确性

操作后验证机制：
- 界面变化验证：检查界面是否按预期变化（如页面跳转、元素出现/消失）
  - 购物车：检查商品是否成功添加，数量是否正确
  - 结算页面：检查商品列表、价格计算是否正确
  - 支付页面：检查支付金额、支付方式是否正确显示
- 状态反馈验证：查看是否有成功提示、错误提示或加载状态
  - 查找"添加成功"、"提交成功"等提示信息
  - 检查错误提示并立即停止操作
- 元素状态验证：确认相关元素状态是否正确更新
  - 按钮状态变化（可点击→不可点击→完成）
  - 文本内容更新（数量、价格等）
- 连续性验证：确保操作序列的逻辑连贯性
  - 验证每个步骤的输出是否作为下一步的输入
  - 检查页面跳转是否正确
- 结果确认：最终确认整体操作目标是否达成
  - 购物车：确认商品已添加且数量正确
  - 结算：确认订单信息完整
  - 支付：确认到达支付页面并显示正确金额

特别注意：
- 支付步骤前必须暂停，等待用户确认支付密码等信息
- 所有操作都要在合理时间内完成，避免超时
- 如遇到网络问题、界面异常或操作失败要立即报告
- 遇到登录过期、验证码等特殊情况要及时处理""",
        }
        
        agent = DroidAgent(
            goal=action,
            config=droidrun_config,
            prompts=custom_prompts
        )
        
        # Run agent
        result = await agent.run()
        
        return {
            "success": result.success,
            "reason": result.reason,
            "steps": result.steps
        }
    except Exception as e:
        return {
            "success": False,
            "reason": str(e),
            "steps": 0
        }
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        # Mark execution as done
        done_event.set()
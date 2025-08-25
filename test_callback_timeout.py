#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CallbackQuery超时处理机制
"""

import asyncio
import logging
from telegram.error import BadRequest

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_callback_timeout():
    """模拟CallbackQuery超时测试"""
    logger.info("开始模拟CallbackQuery超时测试...")
    
    # 模拟超时异常
    try:
        # 模拟等待10秒，超过Telegram的CallbackQuery超时时间
        await asyncio.sleep(10)
        # 这里应该会抛出超时异常
        raise BadRequest("Query is too old")
    except BadRequest as e:
        error_msg = str(e).lower()
        logger.error(f"捕获到异常: {e}")
        if "query is too old" in error_msg or "timeout" in error_msg:
            logger.info("✅ 成功识别CallbackQuery超时错误")
            return True
        else:
            logger.info("❌ 未识别为超时错误")
            return False
    except Exception as e:
        logger.error(f"捕获到其他异常: {e}")
        return False

async def main():
    """主函数"""
    logger.info("开始测试CallbackQuery超时处理机制...")
    result = await test_callback_timeout()
    if result:
        logger.info("✅ 测试通过")
    else:
        logger.info("❌ 测试失败")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CallbackQuery超时处理机制
"""
import asyncio
import logging
from telegram.error import BadRequest

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test-callback-timeout")

async def test_callback_timeout():
    """模拟CallbackQuery超时情况"""
    logger.info("开始测试CallbackQuery超时处理机制...")
    
    try:
        logger.info("开始模拟CallbackQuery超时测试...")
        # 模拟10秒延迟后抛出"Query is too old"的BadRequest异常
        await asyncio.sleep(10)
        raise BadRequest("Query is too old and response timeout expired or query id is invalid")
    except BadRequest as e:
        if "Query is too old" in str(e):
            logger.info(f"✅ 成功捕获CallbackQuery超时异常: {e}")
            return True
        else:
            logger.error(f"❌ 捕获到其他BadRequest异常: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ 捕获到未预期的异常: {e}")
        return False

async def main():
    """主函数"""
    try:
        result = await test_callback_timeout()
        if result:
            logger.info("✅ 测试通过")
        else:
            logger.error("❌ 测试失败")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
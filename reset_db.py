"""
重置数据库 - 删除所有表并重新创建
用途：开发/测试阶段快速清空数据库并重建表结构
警告：会删除所有数据，生产环境请勿使用！
"""
import asyncio
from app.core.database import engine, Base
# 导入所有模型以确保表被正确创建
from app.models import user, question, paper, exam_record


async def reset_db():
    """删除并重新创建所有表"""
    print("⚠️  警告：此操作将删除所有数据！")
    print("正在删除所有表...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("✅ 所有表已删除")
    
    print("正在重新创建表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ 表创建完成")
    print("\n已创建的表：")
    print("  - users (用户表)")
    print("  - questions (题目表)")
    print("  - papers (试卷表)")
    print("  - exam_records (考试记录表)")
    
    await engine.dispose()
    print("\n✅ 数据库连接已关闭")


if __name__ == "__main__":
    print("=" * 60)
    print("数据库重置工具")
    print("=" * 60)
    
    confirm = input("\n确定要重置数据库吗？这将删除所有数据！(yes/no): ")
    
    if confirm.lower() == 'yes':
        try:
            asyncio.run(reset_db())
            print("\n🎉 数据库重置成功！")
        except Exception as e:
            print(f"\n❌ 重置失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ 操作已取消")

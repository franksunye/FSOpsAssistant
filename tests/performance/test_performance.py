"""
性能测试模块

测试系统在各种负载下的性能表现
"""

import pytest
import time
import threading
import statistics
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.agent.orchestrator import AgentOrchestrator
from src.fsoa.agent.decision import DecisionEngine, DecisionMode
from src.fsoa.data.models import TaskInfo, TaskStatus, Priority
from src.fsoa.notification.wechat import WeChatClient


class TestAgentPerformance:
    """Agent性能测试"""
    
    def create_test_tasks(self, count: int):
        """创建测试任务"""
        tasks = []
        for i in range(count):
            task = TaskInfo(
                id=i + 1,
                title=f"性能测试任务{i+1}",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.NORMAL,
                sla_hours=8,
                elapsed_hours=10,  # 超时任务
                group_id=f"group_{i % 5 + 1:03d}",
                assignee=f"测试人员{i % 10 + 1}",
                customer=f"客户{i % 20 + 1}",
                location=f"地点{i % 15 + 1}",
                created_at=datetime.now() - timedelta(hours=10),
                updated_at=datetime.now()
            )
            tasks.append(task)
        return tasks
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_execution_time_small_load(self, mock_db_manager, mock_send_wechat, 
                                           mock_metabase_client):
        """测试小负载下的执行时间"""
        # 创建10个任务
        tasks = self.create_test_tasks(10)
        
        # Mock设置
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = tasks
        mock_metabase_client.return_value = mock_client
        
        mock_send_wechat.return_value = True
        
        mock_db = Mock()
        mock_db.save_agent_execution.return_value = True
        mock_db.save_task.return_value = True
        mock_db.save_notification.return_value = 1
        mock_db_manager.return_value = mock_db
        
        # 执行测试
        orchestrator = AgentOrchestrator()
        
        start_time = time.time()
        result = orchestrator.execute(dry_run=False)
        execution_time = time.time() - start_time
        
        # 性能断言
        assert execution_time < 10  # 10个任务应在10秒内完成
        assert result.tasks_processed == 10
        assert result.notifications_sent >= 0
        
        print(f"小负载执行时间: {execution_time:.2f}秒")
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_execution_time_medium_load(self, mock_db_manager, mock_send_wechat, 
                                            mock_metabase_client):
        """测试中等负载下的执行时间"""
        # 创建50个任务
        tasks = self.create_test_tasks(50)
        
        # Mock设置
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = tasks
        mock_metabase_client.return_value = mock_client
        
        mock_send_wechat.return_value = True
        
        mock_db = Mock()
        mock_db.save_agent_execution.return_value = True
        mock_db.save_task.return_value = True
        mock_db.save_notification.return_value = 1
        mock_db_manager.return_value = mock_db
        
        # 执行测试
        orchestrator = AgentOrchestrator()
        
        start_time = time.time()
        result = orchestrator.execute(dry_run=False)
        execution_time = time.time() - start_time
        
        # 性能断言
        assert execution_time < 30  # 50个任务应在30秒内完成
        assert result.tasks_processed == 50
        
        print(f"中等负载执行时间: {execution_time:.2f}秒")
    
    @patch('src.fsoa.agent.tools.get_metabase_client')
    @patch('src.fsoa.agent.tools.send_wechat_message')
    @patch('src.fsoa.agent.tools.get_db_manager')
    def test_agent_execution_time_large_load(self, mock_db_manager, mock_send_wechat, 
                                           mock_metabase_client):
        """测试大负载下的执行时间"""
        # 创建100个任务
        tasks = self.create_test_tasks(100)
        
        # Mock设置
        mock_client = Mock()
        mock_client.get_overdue_tasks.return_value = tasks
        mock_metabase_client.return_value = mock_client
        
        mock_send_wechat.return_value = True
        
        mock_db = Mock()
        mock_db.save_agent_execution.return_value = True
        mock_db.save_task.return_value = True
        mock_db.save_notification.return_value = 1
        mock_db_manager.return_value = mock_db
        
        # 执行测试
        orchestrator = AgentOrchestrator()
        
        start_time = time.time()
        result = orchestrator.execute(dry_run=False)
        execution_time = time.time() - start_time
        
        # 性能断言
        assert execution_time < 60  # 100个任务应在60秒内完成
        assert result.tasks_processed == 100
        
        print(f"大负载执行时间: {execution_time:.2f}秒")


class TestDecisionEnginePerformance:
    """决策引擎性能测试"""
    
    def test_rule_engine_performance(self):
        """测试规则引擎性能"""
        decision_engine = DecisionEngine(DecisionMode.RULE_ONLY)
        
        # 创建测试任务
        task = TaskInfo(
            id=1,
            title="性能测试任务",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.NORMAL,
            sla_hours=8,
            elapsed_hours=10,
            group_id="test_group",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 测试1000次决策的时间
        start_time = time.time()
        for _ in range(1000):
            result = decision_engine.make_decision(task)
            assert result.action in ["skip", "notify", "escalate"]
        
        execution_time = time.time() - start_time
        
        # 性能断言
        assert execution_time < 1.0  # 1000次决策应在1秒内完成
        avg_time = execution_time / 1000
        
        print(f"规则引擎平均决策时间: {avg_time*1000:.2f}毫秒")
    
    def test_concurrent_decision_making(self):
        """测试并发决策性能"""
        decision_engine = DecisionEngine(DecisionMode.RULE_ONLY)
        
        def make_decision_batch(batch_size=100):
            """批量决策"""
            results = []
            for i in range(batch_size):
                task = TaskInfo(
                    id=i + 1,
                    title=f"并发测试任务{i+1}",
                    status=TaskStatus.IN_PROGRESS,
                    priority=Priority.NORMAL,
                    sla_hours=8,
                    elapsed_hours=10,
                    group_id="test_group",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                result = decision_engine.make_decision(task)
                results.append(result)
            return results
        
        # 并发执行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_decision_batch) for _ in range(10)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        execution_time = time.time() - start_time
        
        # 性能断言
        assert len(all_results) == 1000  # 10个线程 * 100个决策
        assert execution_time < 5.0  # 并发1000次决策应在5秒内完成
        
        print(f"并发决策执行时间: {execution_time:.2f}秒")


class TestNotificationPerformance:
    """通知系统性能测试"""
    
    @patch('src.fsoa.notification.wechat.requests.post')
    def test_notification_throughput(self, mock_post):
        """测试通知吞吐量"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_response
        
        wechat_client = WeChatClient()
        
        # 测试发送100条消息的时间
        start_time = time.time()
        success_count = 0
        
        for i in range(100):
            success = wechat_client.send_text_message("test_group", f"测试消息{i+1}")
            if success:
                success_count += 1
        
        execution_time = time.time() - start_time
        
        # 性能断言
        assert success_count == 100
        assert execution_time < 10.0  # 100条消息应在10秒内发送完成
        
        throughput = success_count / execution_time
        print(f"通知吞吐量: {throughput:.2f}条/秒")
    
    @patch('src.fsoa.notification.wechat.requests.post')
    def test_concurrent_notifications(self, mock_post):
        """测试并发通知性能"""
        # Mock HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_response
        
        def send_notification_batch(batch_size=10):
            """批量发送通知"""
            wechat_client = WeChatClient()
            success_count = 0
            
            for i in range(batch_size):
                success = wechat_client.send_text_message("test_group", f"并发测试消息{i+1}")
                if success:
                    success_count += 1
            
            return success_count
        
        # 并发发送
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_notification_batch) for _ in range(10)]
            total_success = sum(future.result() for future in as_completed(futures))
        
        execution_time = time.time() - start_time
        
        # 性能断言
        assert total_success == 100  # 10个线程 * 10条消息
        assert execution_time < 15.0  # 并发100条消息应在15秒内完成
        
        print(f"并发通知执行时间: {execution_time:.2f}秒")


class TestMemoryUsage:
    """内存使用测试"""
    
    def test_memory_usage_with_large_dataset(self):
        """测试大数据集的内存使用"""
        import psutil
        import os
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建大量任务数据
        large_task_list = []
        for i in range(1000):
            task = TaskInfo(
                id=i + 1,
                title=f"内存测试任务{i+1}" * 10,  # 增加字符串长度
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.NORMAL,
                sla_hours=8,
                elapsed_hours=10,
                group_id=f"group_{i % 100 + 1:03d}",
                assignee=f"测试人员{i % 50 + 1}",
                customer=f"客户{i % 200 + 1}",
                location=f"地点{i % 150 + 1}",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            large_task_list.append(task)
        
        # 检查内存使用
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # 清理数据
        del large_task_list
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"初始内存: {initial_memory:.2f}MB")
        print(f"峰值内存: {peak_memory:.2f}MB")
        print(f"最终内存: {final_memory:.2f}MB")
        print(f"内存增长: {memory_increase:.2f}MB")
        
        # 内存使用断言
        assert memory_increase < 100  # 内存增长应小于100MB


def run_performance_benchmark():
    """运行性能基准测试"""
    print("🚀 开始性能基准测试...")
    
    # 这里可以添加更多的基准测试
    # 例如：数据库查询性能、网络请求性能等
    
    print("✅ 性能基准测试完成")


if __name__ == "__main__":
    run_performance_benchmark()

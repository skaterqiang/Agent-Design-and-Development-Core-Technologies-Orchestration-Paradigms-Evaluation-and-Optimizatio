"""PDF技能渐进式测试驱动"""
import asyncio
import sys
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入优化后的模块
from agent_scope_skills import (
    AgentSkillManager,
    SkillLoader,
    AgentFactory,
    InteractiveSession,
    initialize_agent_with_skills
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFSkillTester:
    """PDF技能测试器"""
    
    def __init__(self):
        self.test_results = []
        self.skill_manager = None
        self.current_stage = 0
        
    async def setup_test_environment(self):
        """设置测试环境"""
        logger.info("[SETUP] 初始化测试环境")
        try:
            self.skill_manager = AgentSkillManager()
            logger.info("[READY] 测试环境准备就绪")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 测试环境设置失败: {e}")
            return False
    
    def get_pdf_test_scenarios(self) -> List[Dict[str, Any]]:
        """获取PDF测试场景"""
        return [
            {
                'stage': 1,
                'name': 'PDF基础创建与操作',
                'skills': ['basic_tools', 'pdf_basic'],
                'test_cases': [
                    {
                        'description': '创建简单的PDF文档',
                        'prompt': 'Create a PDF document named "hello_world.pdf" with the text "Hello World!"',
                        'expected_outcomes': ['PDF creation', 'file handling', 'text insertion'],
                        'validation_keywords': ['created', 'pdf', 'successfully']
                    },
                    {
                        'description': '查询PDF相关技能',
                        'prompt': 'What PDF operations can you perform?',
                        'expected_outcomes': ['list capabilities', 'explain functions'],
                        'validation_keywords': ['pdf', 'create', 'extract', 'merge']
                    }
                ]
            },
            {
                'stage': 2,
                'name': 'PDF文本提取与处理',
                'skills': ['basic_tools', 'pdf_basic'],
                'test_cases': [
                    {
                        'description': '提取PDF文本内容',
                        'prompt': 'Extract text from the existing 测试.pdf file',
                        'expected_outcomes': ['text extraction', 'file reading'],
                        'validation_keywords': ['extract', 'text', 'content']
                    },
                    {
                        'description': '分析PDF文档结构',
                        'prompt': 'Analyze the structure of 测试.pdf and tell me what you find',
                        'expected_outcomes': ['structure analysis', 'metadata reading'],
                        'validation_keywords': ['pages', 'structure', 'analysis']
                    }
                ]
            },
            {
                'stage': 3,
                'name': 'PDF合并与分割',
                'skills': ['basic_tools', 'pdf_basic'],
                'test_cases': [
                    {
                        'description': '合并多个PDF文件',
                        'prompt': 'Merge 测试.pdf with another PDF file if possible',
                        'expected_outcomes': ['merge operation', 'file combination'],
                        'validation_keywords': ['merge', 'combine', 'multiple']
                    },
                    {
                        'description': '分割PDF页面',
                        'prompt': 'Split 测试.pdf into individual pages',
                        'expected_outcomes': ['split operation', 'page extraction'],
                        'validation_keywords': ['split', 'separate', 'pages']
                    }
                ]
            },
            {
                'stage': 4,
                'name': 'PDF表单处理',
                'skills': ['basic_tools', 'pdf_basic'],
                'test_cases': [
                    {
                        'description': '检查PDF表单字段',
                        'prompt': 'Check if 测试.pdf contains any form fields',
                        'expected_outcomes': ['form detection', 'field identification'],
                        'validation_keywords': ['form', 'fields', 'fillable']
                    },
                    {
                        'description': '填写PDF表单',
                        'prompt': 'Fill out form fields in 测试.pdf if it contains forms',
                        'expected_outcomes': ['form filling', 'data insertion'],
                        'validation_keywords': ['fill', 'form', 'data']
                    }
                ]
            }
        ]
    
    async def run_single_test_case(self, agent, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例"""
        logger.info(f"[TEST] 执行测试: {test_case['description']}")
        logger.info(f"[PROMPT] 测试提示: {test_case['prompt']}")
        
        try:
            # 创建交互会话
            session = InteractiveSession(agent)
            
            # 发送测试提示
            result = await session.send_message(test_case['prompt'])
            
            # 分析响应
            response_text = result['response'].lower()
            validation_score = self._calculate_validation_score(
                response_text, 
                test_case['validation_keywords']
            )
            
            # 判断测试结果
            passed = validation_score > 0.6  # 60%关键词匹配率
            
            test_result = {
                'test_case': test_case['description'],
                'prompt': test_case['prompt'],
                'response': result['response'],
                'validation_score': validation_score,
                'passed': passed,
                'expected_outcomes': test_case['expected_outcomes'],
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"[RESULT] 测试{'通过' if passed else '失败'} (得分: {validation_score:.2f})")
            return test_result
            
        except Exception as e:
            logger.error(f"[ERROR] 测试执行失败: {e}")
            return {
                'test_case': test_case['description'],
                'prompt': test_case['prompt'],
                'error': str(e),
                'passed': False,
                'validation_score': 0.0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_validation_score(self, response: str, keywords: List[str]) -> float:
        """计算验证分数"""
        if not keywords:
            return 1.0
            
        matched_keywords = sum(1 for keyword in keywords if keyword.lower() in response)
        return matched_keywords / len(keywords)
    
    async def run_stage_tests(self, stage_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """运行阶段测试"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[STAGE {stage_config['stage']}] {stage_config['name']}")
        logger.info(f"[SKILLS] 加载技能: {', '.join(stage_config['skills'])}")
        logger.info(f"[TESTS] 测试用例数量: {len(stage_config['test_cases'])}")
        logger.info('='*60)
        
        try:
            # 初始化带有指定技能的智能体
            agent, toolkit, memory = await initialize_agent_with_skills(
                self.skill_manager, 
                stage_config['skills']
            )
            
            # 显示当前技能状态
            available_skills = self.skill_manager.get_available_skills()
            logger.info(f"[STATUS] 当前已加载技能: {available_skills}")
            
            # 运行所有测试用例
            stage_results = []
            for i, test_case in enumerate(stage_config['test_cases'], 1):
                logger.info(f"\n--- 测试用例 {i}/{len(stage_config['test_cases'])} ---")
                result = await self.run_single_test_case(agent, test_case)
                stage_results.append(result)
                
                # 记录到总体结果
                self.test_results.append(result)
            
            # 计算阶段统计
            passed_count = sum(1 for r in stage_results if r['passed'])
            total_count = len(stage_results)
            success_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
            
            logger.info(f"\n[STAGE SUMMARY] {stage_config['name']}")
            logger.info(f"  通过: {passed_count}/{total_count} ({success_rate:.1f}%)")
            
            return stage_results
            
        except Exception as e:
            logger.error(f"[ERROR] 阶段测试执行失败: {e}")
            return []
    
    def generate_detailed_report(self) -> Dict[str, Any]:
        """生成详细测试报告"""
        # 按阶段分组结果
        results_by_stage = {}
        for result in self.test_results:
            # 从测试用例描述中提取阶段信息
            stage_key = result.get('test_case', '').split(':')[0] if ':' in result.get('test_case', '') else 'Unknown'
            if stage_key not in results_by_stage:
                results_by_stage[stage_key] = []
            results_by_stage[stage_key].append(result)
        
        # 计算总体统计
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'generated_at': datetime.now().isoformat()
            },
            'stages': {},
            'detailed_results': self.test_results
        }
        
        # 添加各阶段详情
        for stage, results in results_by_stage.items():
            stage_passed = sum(1 for r in results if r.get('passed', False))
            stage_total = len(results)
            report['stages'][stage] = {
                'total_tests': stage_total,
                'passed_tests': stage_passed,
                'failed_tests': stage_total - stage_passed,
                'success_rate': (stage_passed / stage_total * 100) if stage_total > 0 else 0,
                'results': results
            }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """保存测试报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pdf_skills_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"[SAVED] 测试报告已保存到: {filename}")
            return filename
        except Exception as e:
            logger.error(f"[ERROR] 保存报告失败: {e}")
            return None
    
    async def run_comprehensive_pdf_test(self):
        """运行综合PDF技能测试"""
        logger.info("[START] 开始PDF技能综合测试")
        
        # 设置测试环境
        if not await self.setup_test_environment():
            logger.error("[ABORT] 测试环境设置失败，终止测试")
            return False
        
        # 获取测试场景
        test_scenarios = self.get_pdf_test_scenarios()
        
        # 逐阶段运行测试
        for scenario in test_scenarios:
            await self.run_stage_tests(scenario)
            
            # 在阶段间添加延迟
            await asyncio.sleep(2)
        
        # 生成并保存报告
        report = self.generate_detailed_report()
        report_file = self.save_report(report)
        
        # 显示摘要
        summary = report['summary']
        logger.info(f"\n{'='*60}")
        logger.info("PDF技能测试最终摘要")
        logger.info('='*60)
        logger.info(f"总测试数: {summary['total_tests']}")
        logger.info(f"通过测试: {summary['passed_tests']}")
        logger.info(f"失败测试: {summary['failed_tests']}")
        logger.info(f"成功率: {summary['success_rate']:.1f}%")
        logger.info(f"报告文件: {report_file}")
        logger.info('='*60)
        
        return summary['success_rate'] >= 80  # 80%成功率视为通过

class PDFSkillDemonstration:
    """PDF技能演示类"""
    
    @staticmethod
    async def demonstrate_pdf_capabilities():
        """演示PDF核心功能"""
        logger.info("[DEMO] 开始PDF功能演示")
        
        demo_prompts = [
            "Create a professional PDF document with multiple sections",
            "Show me how to extract text from PDF files",
            "Demonstrate PDF merging capabilities",
            "Explain how to work with PDF forms",
            "Show advanced PDF manipulation techniques"
        ]
        
        try:
            # 初始化完整技能集的智能体
            skill_manager = AgentSkillManager()
            agent, toolkit, memory = await initialize_agent_with_skills(
                skill_manager, 
                ['basic_tools', 'pdf_basic', 'agentscope_analysis']
            )
            
            session = InteractiveSession(agent)
            
            for i, prompt in enumerate(demo_prompts, 1):
                logger.info(f"\n[DEMO {i}] {prompt}")
                try:
                    result = await session.send_message(prompt)
                    logger.info(f"[RESPONSE] {result['response'][:300]}...")
                except Exception as e:
                    logger.error(f"[ERROR] 演示失败: {e}")
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"[ERROR] 演示执行失败: {e}")

async def main():
    """主函数"""
    try:
        # 运行PDF技能测试
        tester = PDFSkillTester()
        success = await tester.run_comprehensive_pdf_test()
        
        if success:
            logger.info("[SUCCESS] PDF技能测试通过！")
            
            # 可选：运行演示
            logger.info("[PROMPT] 是否运行PDF功能演示？(y/n): ")
            # 在实际环境中可以添加用户输入
            # user_input = input().lower().strip()
            # if user_input == 'y':
            #     await PDFSkillDemonstration.demonstrate_pdf_capabilities()
        else:
            logger.warning("[WARNING] PDF技能测试未达到预期标准")
            
    except KeyboardInterrupt:
        logger.info("[INTERRUPTED] 用户中断测试")
    except Exception as e:
        logger.error(f"[ERROR] 测试执行异常: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
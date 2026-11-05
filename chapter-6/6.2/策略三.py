# SOP模板引擎
class SOPTemplateEngine:
    """SOP模板引擎"""
    
    def __init__(self):
        self.templates = self.load_sop_templates()
    
    def load_sop_templates(self):
        """加载SOP模板"""
        return {
            "damaged_goods_complaint": {
                "step1": [
                    "非常抱歉给您带来了不愉快的购物体验！",
                    "我完全理解您收到损坏商品时的心情，这确实让人失望。",
                    "请您放心，我会立即为您记录并处理这个问题。"
                ],
                "step2": [
                    "为了准确为您处理，请提供以下信息：",
                    "1. 订单编号",
                    "2. 损坏商品的具体名称和数量",
                    "3. 损坏情况的文字描述",
                    "4. 损坏照片（如有）",
                    "5. 您希望的解决方案（补发、退款、部分补偿）"
                ],
                "step3": [
                    "信息已收到，我已为您创建了正式工单（编号：{ticket_id}），所有信息均已记录。",
                    "接下来，我会将您的工单提交给售后专员审核，预计在2小时内会有结果。",
                    "审核结束后，我们的专员会通过电话主动联系您，告知处理方案。",
                    "请您留意接听。"
                ],
                "step4": [
                    "请问以上信息是否准确，您是否还有其他补充？",
                    "这是本次为您生成的工单号{ticket_id}，您之后可以通过此编号查询进度。"
                ]
            }
        }
    
    def generate_response(self, scenario, step, context=None):
        """生成模板化回复"""
        template = self.templates.get(scenario, {})
        step_templates = template.get(step, [])
        
        # 填充模板变量
        filled_templates = []
        for tpl in step_templates:
            if context:
                for key, value in context.items():
                    tpl = tpl.replace(f"{{{key}}}", str(value))
            filled_templates.append(tpl)
        
        return "\n".join(filled_templates)

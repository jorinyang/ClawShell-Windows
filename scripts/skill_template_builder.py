     1|#!/usr/bin/env python3
     2|"""
     3|Skill Template Builder - 技能模板构建器
     4|功能：
     5|1. 监听hermes_insights/applied中的技能模板
     6|2. 验证模板完整性
     7|3. 生成可执行的技能文件
     8|4. 注册新技能
     9|"""
    10|
    11|import os
    12|import sys
    13|import json
    14|import shutil
    15|from datetime import datetime
    16|from pathlib import Path
    17|from typing import Dict, Any
    18|
    19|# 配置
    20|OPENCLAW_DIR = Path.home() / ".real"
    21|SKILLS_DIR = OPENCLAW_DIR / "workspace" / "skills"
    22|TEMPLATE_DIR = OPENCLAW_DIR / "shared" / "hermes_insights" / "applied"
    23|TEMPLATE_BACKUP = OPENCLAW_DIR / "shared" / "hermes_insights" / "skill_templates"
    24|LOG_FILE = OPENCLAW_DIR / "logs" / "skill_builder.log"
    25|
    26|
    27|class SkillTemplateBuilder:
    28|    """技能模板构建器"""
    29|    
    30|    def __init__(self):
    31|        TEMPLATE_BACKUP.mkdir(parents=True, exist_ok=True)
    32|        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    33|    
    34|    def _log(self, msg: str):
    35|        """写日志"""
    36|        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    37|        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    38|        with open(LOG_FILE, 'a') as f:
    39|            f.write(f"[{timestamp}] {msg}\n")
    40|    
    41|    def poll_templates(self) -> int:
    42|        """轮询并处理技能模板"""
    43|        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    44|        processed = 0
    45|        
    46|        for template_file in TEMPLATE_DIR.glob("skill_template_*.json"):
    47|            try:
    48|                if self._validate_and_build(template_file):
    49|                    processed += 1
    50|            except Exception as e:
    51|                self._log(f"Error: {template_file.name}: {e}")
    52|        
    53|        return processed
    54|    
    55|    def _validate_and_build(self, template_path: Path) -> bool:
    56|        """验证并构建技能"""
    57|        with open(template_path, 'r') as f:
    58|            template = json.load(f)
    59|        
    60|        # 验证必要字段
    61|        if not self._validate_template(template):
    62|            self._log(f"Invalid template: {template_path.name}")
    63|            return False
    64|        
    65|        # 生成技能文件
    66|        skill_name = template.get("template", {}).get("name")
    67|        skill_path = SKILLS_DIR / skill_name
    68|        
    69|        self._create_skill(skill_path, template)
    70|        self._log(f"Created skill: {skill_name}")
    71|        
    72|        # 移动模板到备份
    73|        shutil.move(str(template_path), str(TEMPLATE_BACKUP / template_path.name))
    74|        
    75|        return True
    76|    
    77|    def _validate_template(self, template: Dict) -> bool:
    78|        """验证模板完整性"""
    79|        required_fields = ["stream_type", "template"]
    80|        for field in required_fields:
    81|            if field not in template:
    82|                return False
    83|        
    84|        template_data = template.get("template", {})
    85|        required_template_fields = ["name", "description", "trigger_conditions", "actions"]
    86|        for field in required_template_fields:
    87|            if field not in template_data:
    88|                return False
    89|        
    90|        return True
    91|    
    92|    def _create_skill(self, skill_path: Path, template: Dict):
    93|        """创建技能文件"""
    94|        skill_path.mkdir(parents=True, exist_ok=True)
    95|        template_data = template.get("template", {})
    96|        
    97|        # 创建SKILL.md
    98|        skill_md = self._generate_skill_md(template_data)
    99|        with open(skill_path / "SKILL.md", 'w') as f:
   100|            f.write(skill_md)
   101|        
   102|        # 创建主脚本
   103|        main_script = self._generate_main_script(template_data)
   104|        script_name = template_data.get("name", "skill").replace("-", "_")
   105|        with open(skill_path / f"{script_name}.py", 'w') as f:
   106|            f.write(main_script)
   107|        
   108|        # 设置执行权限
   109|        os.chmod(skill_path / f"{script_name}.py", 0o755)
   110|    
   111|    def _generate_skill_md(self, template: Dict) -> str:
   112|        """生成SKILL.md内容"""
   113|        trigger_lines = []
   114|        for tc in template.get("trigger_conditions", []):
   115|            trigger_lines.append(f"- {tc}")
   116|        
   117|        actions_lines = []
   118|        for action in template.get("actions", []):
   119|            action_str = f"- type: {action.get('type')}"
   120|            if 'target' in action:
   121|                action_str += f", target: {action.get('target')}"
   122|            if 'pattern' in action:
   123|                action_str += f", pattern: {action.get('pattern')}"
   124|            actions_lines.append(action_str)
   125|        
   126|        trigger_text = "\n".join(trigger_lines) if trigger_lines else "- 无"
   127|        actions_text = "\n".join(actions_lines) if actions_lines else "- 无"
   128|        
   129|        md_content = f"""# {template['name']}
   130|
   131|> 自动生成的技能模板
   132|> 创建时间: {datetime.now().isoformat()}
   133|
   134|## 描述
   135|
   136|{template.get('description', '')}
   137|
   138|## 触发条件
   139|
   140|{trigger_text}
   141|
   142|## 执行动作
   143|
   144|{actions_text}
   145|
   146|## 输出格式
   147|
   148|{template.get('output_format', 'text')}
   149|
   150|---
   151|
   152|*此技能由Hermes自动生成*
   153|"""
   154|        return md_content
   155|    
   156|    def _generate_main_script(self, template: Dict) -> str:
   157|        """生成主脚本"""
   158|        skill_name = template.get("name", "skill")
   159|        script_name = skill_name.replace("-", "_")
   160|        
   161|        script_content = f'''#!/usr/bin/env python3
   162|"""
   163|{skill_name} - 自动生成的技能脚本
   164|由Hermes自动生成
   165|创建时间: {datetime.now().isoformat()}
   166|"""
   167|
   168|import sys
   169|import json
   170|from datetime import datetime
   171|from pathlib import Path
   172|
   173|SKILL_NAME = "{skill_name}"
   174|SKILL_VERSION = "1.1.0"
   175|
   176|
   177|def main():
   178|    """主执行函数"""
   179|    print(f"[{{SKILL_NAME}}] v{{SKILL_VERSION}}")
   180|    print(f"执行时间: {{datetime.now().isoformat()}}")
   181|    
   182|    # TODO: 实现技能逻辑
   183|    print("技能执行中...")
   184|    
   185|    return 0
   186|
   187|
   188|if __name__ == "__main__":
   189|    sys.exit(main())
   190|'''
   191|        return script_content
   192|
   193|
   194|def main():
   195|    import argparse
   196|    parser = argparse.ArgumentParser(description="Skill Template Builder")
   197|    parser.add_argument("--dry-run", action="store_true", help="仅显示待处理模板")
   198|    args = parser.parse_args()
   199|    
   200|    builder = SkillTemplateBuilder()
   201|    
   202|    if args.dry_run:
   203|        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
   204|        templates = list(TEMPLATE_DIR.glob("skill_template_*.json"))
   205|        print(f"待处理模板: {len(templates)}")
   206|        for f in templates:
   207|            print(f"  - {f.name}")
   208|    else:
   209|        processed = builder.poll_templates()
   210|        print(f"处理完成: {processed}个模板")
   211|
   212|
   213|if __name__ == "__main__":
   214|    main()
   215|
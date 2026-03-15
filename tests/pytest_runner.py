#!/usr/bin/env python3
"""
DDNS Manager 测试运行脚本

运行方式：
    python tests/pytest_runner.py              # 运行所有测试
    python tests/pytest_runner.py -v           # 详细输出
    python tests/pytest_runner.py --html       # 生成 HTML 报告
    python tests/pytest_runner.py tests/test_auth.py  # 运行指定测试文件
"""

import sys
import os
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
TEST_DIR = PROJECT_ROOT / "tests"
REPORT_FILE = PROJECT_ROOT / "test-report.html"


def run_pytest(args: list[str]) -> int:
    """运行 pytest 并返回退出码"""
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    # 构建命令
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    # 检查是否生成 HTML 报告
    generate_html = "--html" in args or "-h" in args
    if generate_html:
        cmd.extend([
            "--html=test-report.html",
            "--self-contained-html",
        ])
        # 移除 --html 参数，避免重复
        args = [a for a in args if a not in ("--html", "-h")]
    
    # 添加用户参数
    cmd.extend(args)
    
    # 默认添加 -v (详细输出)
    if "-v" not in args and "--verbose" not in args:
        cmd.insert(3, "-v")
    
    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 60)
    
    # 运行 pytest
    result = subprocess.run(cmd)
    
    if generate_html and REPORT_FILE.exists():
        print("=" * 60)
        print(f"✅ 测试报告已生成: {REPORT_FILE}")
        print(f"   浏览器打开: file://{REPORT_FILE}")
    
    return result.returncode


def main():
    """主函数"""
    args = sys.argv[1:]
    
    # 显示帮助
    if "--help" in args or "-h" in args and "--html" not in args:
        print(__doc__)
        print("\n可选参数:")
        print("  -v, --verbose    详细输出")
        print("  --html           生成 HTML 测试报告")
        print("  --tb=short       简短的错误回溯")
        print("  --tb=long        详细的错误回溯")
        print("  -k <pattern>     运行匹配模式的测试")
        print("  --help           显示此帮助信息")
        print("\n示例:")
        print("  python tests/pytest_runner.py --html")
        print("  python tests/pytest_runner.py -k 'test_create'")
        print("  python tests/pytest_runner.py tests/test_machines.py")
        return 0
    
    exit_code = run_pytest(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
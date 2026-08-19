#!/bin/bash
# Agent Team 启动脚本
# 用于在 Claude Code 中启动各个 Agent

set -e

AGENT_TEAM_DIR="/Users/liuyixing/项目/OREP/docs/agent_team"
STARTUP_PROMPTS_DIR="$AGENT_TEAM_DIR/startup_prompts"
WORK_LOG_DIR="/Users/liuyixing/项目/OREP/WORK_LOG"

# Agent 列表
AGENTS=(
    "tech_lead:Tech Lead:01_tech_lead.md"
    "prompt_eng:Prompt Engineer:02_prompt_engineer.md"
    "backend_eng:Backend Engineer:03_backend_engineer.md"
    "frontend_eng:Frontend Engineer:04_frontend_engineer.md"
    "qa:QA Reviewer:05_qa_reviewer.md"
    "standards:Standards Keeper:06_standards_keeper.md"
)

# 创建工作日志目录
mkdir -p "$WORK_LOG_DIR"

echo "========================================"
echo "OREP AI PPT Agent Team 启动器"
echo "========================================"
echo ""

# 显示 Agent 列表
echo "可用 Agent："
for i in "${!AGENTS[@]}"; do
    IFS=':' read -r id name _ <<< "${AGENTS[$i]}"
    echo "  $((i+1)). $name ($id)"
done
echo ""

# 启动指定 Agent
start_agent() {
    local id="$1"
    local name="$2"
    local prompt_file="$3"

    echo "----------------------------------------"
    echo "启动: $name"
    echo "提示词文件: $STARTUP_PROMPTS_DIR/$prompt_file"
    echo "----------------------------------------"

    # 创建该 Agent 的工作日志文件
    touch "$WORK_LOG_DIR/${id}.md"

    # 读取启动提示词
    PROMPT=$(cat "$STARTUP_PROMPTS_DIR/$prompt_file")

    # 启动 Claude Code（需要用户手动在 Claude Code 中粘贴提示词）
    # 注意：Claude Code 不支持直接传入 prompt，需要用户手动复制
    echo ""
    echo "请在 Claude Code 中启动 $name，粘贴以下提示词："
    echo ""
    echo "========================================"
    echo "$PROMPT"
    echo "========================================"
    echo ""
}

# 主菜单
if [ "$1" == "" ]; then
    echo "用法: ./start_team.sh <agent_id>"
    echo ""
    echo "示例: "
    echo "  ./start_team.sh tech_lead     # 启动 Tech Lead"
    echo "  ./start_team.sh prompt_eng     # 启动 Prompt Engineer"
    echo "  ./start_team.sh backend_eng    # 启动 Backend Engineer"
    echo "  ./start_team.sh frontend_eng   # 启动 Frontend Engineer"
    echo "  ./start_team.sh qa             # 启动 QA Reviewer"
    echo "  ./start_team.sh standards      # 启动 Standards Keeper"
    echo "  ./start_team.sh all            # 显示所有 Agent 的启动提示词"
    echo ""
elif [ "$1" == "all" ]; then
    for entry in "${AGENTS[@]}"; do
        IFS=':' read -r id name prompt_file <<< "$entry"
        start_agent "$id" "$name" "$prompt_file"
    done
else
    for entry in "${AGENTS[@]}"; do
        IFS=':' read -r id name prompt_file <<< "$entry"
        if [ "$1" == "$id" ]; then
            start_agent "$id" "$name" "$prompt_file"
            break
        fi
    done
fi
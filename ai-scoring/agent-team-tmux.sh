#!/bin/bash
# OREP Agent Team Monitor
# 用法: ./agent-team-tmux.sh

SESSION="orep-team"

# 创建新的 tmux session，不attach
tmux new-session -d -s "$SESSION" -d

# 分割成4个窗格
tmux split-window -h -t "$SESSION"
tmux split-window -v -t "$SESSION:0.0"
tmux split-window -v -t "$SESSION:0.2"

# 在每个窗格中监控一个 agent 的输出
tmux send-keys -t "$SESSION:0.0" "tail -f /private/tmp/claude/-Users-liuyixing/tasks/ac9e673.output 2>/dev/null || echo 'Agent 1 输出文件不存在'" Enter
tmux send-keys -t "$SESSION:0.1" "tail -f /private/tmp/claude/-Users-liuyixing/tasks/a4d1d81.output 2>/dev/null || echo 'Agent 2 输出文件不存在'" Enter
tmux send-keys -t "$SESSION:0.2" "tail -f /private/tmp/claude/-Users-liuyixing/tasks/a42b544.output 2>/dev/null || echo 'Agent 3 输出文件不存在'" Enter
tmux send-keys -t "$SESSION:0.3" "tail -f /private/tmp/claude/-Users-liuyixing/tasks/a87cc3f.output 2>/dev/null || echo 'Agent 4 输出文件不存在'" Enter

# 设置窗格标题
tmux set-window-option -t "$SESSION:0.0" window-style "bg=#1e1e1e" 2>/dev/null
tmux set-window-option -t "$SESSION" automatic-rename off 2>/dev/null

echo "Agent Team tmux session '$SESSION' 已创建"
echo "连接命令: tmux attach -t $SESSION"
echo "分离快捷键: Ctrl+b d"
echo ""
echo "各窗格监控的文件:"
echo "  Agent 1 (Prompt Engineer):     ac9e673.output"
echo "  Agent 2 (Architecture Auditor): a4d1d81.output"
echo "  Agent 3 (Quality Benchmark):    a42b544.output"
echo "  Agent 4 (Integration Tester):   a87cc3f.output"